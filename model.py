
# External imports
import copy
import time
import torch
import torch.nn as nn
import torch.nn.functional as F

from torch.autograd import Variable
from dataloader import IMG_SIZE
from misc.beam import Beam
from reinforce import Rolls

### A module to ensure convolution happens in the correct manner and the required dimensions are obtained 
### after convolution. Example:
# inp_grids torch.Size([16, 5, 16, 18, 18])
# x_feat_shape torch.Size([16, 18, 18])
# flat_x_shape (-1, 16, 18, 18)
# flat_x torch.Size([80, 16, 18, 18]) : x is input
# flat_y torch.Size([80, 32, 18, 18]) : y is output
# y_feat_shape torch.Size([32, 18, 18])
# y_shape torch.Size([16, 5, 32, 18, 18])
class MapModule(nn.Module):
    '''
    Takes as argument a module `elt_module` that as a signature:
    B1 x I1 x I2 x I3 x ... -> B x O1 x O2 x O3 x ...
    This becomes a module with signature:
    B1 x B2 x B3 ... X I1 x I2 x I3 -> B1 x B2 x B3 x ... X O1 x O2 x O3
    '''
    def __init__(self, elt_module, nb_mod_dim):
        super(MapModule, self).__init__()
        self.elt_module = elt_module
        self.nb_mod_dim = nb_mod_dim

    def forward(self, x):
        x_batch_shape = x.size()[:-self.nb_mod_dim]
        x_feat_shape = x.size()[-self.nb_mod_dim:]

        flat_x_shape = (-1, ) + x_feat_shape
        flat_x = x.contiguous().view(flat_x_shape)
        flat_y = self.elt_module(flat_x)

        y_feat_shape = flat_y.size()[1:]
        y_shape = x_batch_shape + y_feat_shape
        y = flat_y.view(y_shape)

        return y
        
        
class MultiIOProgramDecoder(nn.Module):
    '''
    This LSTM based decoder offers two methods to obtain programs,
    based on a batch of embeddings of the IO grids.

    - `beam_sample` will return the `top_k` best programs, according to
      a beam search using `beam_size` rays.
      Outputs are under the form of tuples
      (Variable with the log proba of the sequence, sequence (as a list) )
    - `sample_model` will sample directly from the probability distribution
      defined by the model.
      Outputs are under the forms of `Rolls` objects. The expected use is to
      assign rewards to the trajectory (using the `Rolls.assign_rewards` function)MultiIOProgramDecoder
      and then use the `yield_*` functions to get them.
    '''
    def __init__(self, vocab_size, embedding_dim,
                 io_emb_size, lstm_hidden_size, nb_layers,
                 learn_syntax):
        super(MultiIOProgramDecoder, self).__init__()

        self.vocab_size = vocab_size
        self.embedding_dim = embedding_dim

        self.io_emb_size = io_emb_size
        self.lstm_input_size = io_emb_size + embedding_dim
        self.lstm_hidden_size = lstm_hidden_size
        self.nb_layers = nb_layers
        self.syntax_checker = None
        self.learned_syntax_checker = None

        self.embedding = nn.Embedding(
            self.vocab_size,
            self.embedding_dim
        )
        self.rnn = nn.LSTM(
            self.lstm_input_size,
            self.lstm_hidden_size,
            self.nb_layers,
        )

        self.initial_h = nn.Parameter(torch.Tensor(self.nb_layers, 1, 1, self.lstm_hidden_size))
        self.initial_c = nn.Parameter(torch.Tensor(self.nb_layers, 1, 1, self.lstm_hidden_size))

        self.out2token = MapModule(nn.Linear(self.lstm_hidden_size, self.vocab_size), 1)
        #TODO
        if learn_syntax:
            self.learned_syntax_checker = SyntaxLSTM(self.vocab_size, self.embedding_dim,
                                                     self.lstm_hidden_size, self.nb_layers)

        self.init_weights()
        
    def init_weights(self):
        initrange = 0.1
        self.embedding.weight.data.uniform_(-initrange, initrange)
        self.out2token.elt_module.bias.data.fill_(0)
        self.initial_h.data.uniform_(-initrange, initrange)
        self.initial_c.data.uniform_(-initrange, initrange)
        
    
    def forward(self, tgt_inp_sequences, io_embeddings,
                list_inp_sequences, no_grad,
                initial_state=None,
                grammar_state=None):
        '''
        tgt_inp_sequences: batch_size x seq_len(tensor length=64)
        io_embeddings: batch_size x nb_ios x io_emb_size
        '''
        # unsqueeze:  dimension of size one inserted at the specified position.
        # squeeze: dimensions of input of size 1 removed.
        # expand: singleton dimensions expanded to a larger size.
        # permute:  dimensions permuted.
        # torch.cat dim: dimensions along which the tensors are concatenated
        # TODO: understand seq_len again
        batch_size, seq_len = tgt_inp_sequences.size()
        _, nb_ios, _ = io_embeddings.size()
     #  print('tgt_inp_sequences',tgt_inp_sequences)
     #   print('tgt_inp_sequences.long()', tgt_inp_sequences.long())
        seq_emb = self.embedding(tgt_inp_sequences).permute(1, 0, 2).contiguous()
        # seq_emb: seq_len x batch_size x embedding_dim
        per_io_seq_emb = seq_emb.unsqueeze(2).expand(seq_len, batch_size, nb_ios, self.embedding_dim)
        # per_io_seq_emb: seq_len x batch_size x nb_ios x embedding_dim

        lstm_cell_size = torch.Size((self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size))
        if initial_state is None:
            initial_state = (
                self.initial_h.expand(lstm_cell_size).contiguous(),
                self.initial_c.expand(lstm_cell_size).contiguous()
            )
        

        # Add the IO embedding to each of the input
        io_embeddings = io_embeddings.unsqueeze(0)
        io_embeddings = io_embeddings.expand(seq_len, batch_size, nb_ios, self.io_emb_size)


        # Forms the input correctly
        dec_input = torch.cat([per_io_seq_emb, io_embeddings], 3)
        # dec_input: seq_len x batch_size x nb_ios x lstm_input_size

        # Flatten across batch x nb_ios
        dec_input = dec_input.view(seq_len, batch_size*nb_ios, self.lstm_input_size)
        # dec_input: seq_len x batch_size*nb_ios x lstm_input_size
        initial_state = (
            initial_state[0].view(self.nb_layers, batch_size*nb_ios, self.lstm_hidden_size),
            initial_state[1].view(self.nb_layers, batch_size*nb_ios, self.lstm_hidden_size)
        )
        if(no_grad):
            initial_state[0].detach()
            initial_state[1].detach()

        # initial_state: 2-Tuple of (nb_layers x batch_size*nb_ios x embedding_dim)

        # Pass through the LSTM
        dec_out, dec_lstm_state = self.rnn(dec_input.contiguous(), initial_state)
        # dec_out: seq_len x batch_size*nb_ios x lstm_hidden_size
        # dec_lstm_state: 2-Tuple of (nb_layers x batch_size*nb_ios x embedding_dim)

        # Reshape the output:
        dec_out = dec_out.view(1, seq_len, batch_size, nb_ios, self.lstm_hidden_size)
        # XXX there is an extremely weird bug in pytorch when doing the max
        # over dim = 2 so we introduce a dummy dimension to avoid it, so
        # that we can operate on the third dimension
        pool_out, _ = dec_out.max(3)
        pool_out = pool_out.squeeze(3).squeeze(0)
        # pool_out: seq_len x batch_size x lstm_hidden_size

        # Flatten for decoding
        decoder_logit = self.out2token(pool_out)
        # decoder_logit: seq_len x batch_size x out_voc_size
        decoder_logit = decoder_logit.permute(1, 0, 2)
        # decoder_logit: batch_size x seq_len x out_voc_size

        # Also reorganise the state
        dec_lstm_state = (
            dec_lstm_state[0].view(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size),
            dec_lstm_state[1].view(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size)
        )
        syntax_mask = None
        
        #TODO if self.syntax_checker is not None:
        
        return decoder_logit, dec_lstm_state, grammar_state, syntax_mask
    
    #TODO understand beam search, currently only used for model evaluation
    def beam_sample(self, io_embeddings,
                    batch_list_inputs_passed, tgt_end, max_len,
                    beam_size, top_k, vol):
        '''
        io_embeddings: batch_size x nb_ios x io_emb_size
        All the rest are ints
        vol is a boolean indicating whether created Variables should be volatile
        '''
        batch_size, nb_ios, io_emb_size = io_embeddings.size()
        use_cuda = io_embeddings.is_cuda
        tt = torch.cuda if use_cuda else torch
        force_beamcpu = True
        
        temp_h = (tt.FloatTensor(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size).fill_(0))
        temp_c = (tt.FloatTensor(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size).fill_(0))

        beams = [Beam(beam_size, top_k, 1, tgt_end, use_cuda and not force_beamcpu)
                 for _ in range(batch_size)]

        lsm = nn.LogSoftmax(dim=1)

        # We will make it a batch size of beam_size
        batch_state = None  # First one is the learned default state
        final_batch_state = None
        batch_grammar_state = None
        batch_inputs = Variable(tt.LongTensor(batch_size, 1).fill_(1))
        batch_list_inputs = [[1]]*batch_size
        batch_io_embeddings = io_embeddings
        batch_idx = Variable(torch.arange(0, batch_size, 1).long())
        if use_cuda:
            batch_idx = batch_idx.cuda()
        beams_per_sp = [1 for _ in range(batch_size)]
        
        curr_batch_size = batch_size  # Will vary as we go along in the decoder
        parent =  [idx for idx in range(curr_batch_size)]
        prev_parent = [idx for idx in range(curr_batch_size)]
        prev_parent = Variable(tt.LongTensor(prev_parent), requires_grad=False)
        
        for i in range(1, (max(map(len,batch_list_inputs_passed)))):
            
            # Do the forward of one time step, for all our traces to expand
            dec_outs, dec_state, \
            _, _ = self.forward(batch_inputs,
                                                batch_io_embeddings,
                                                batch_list_inputs,
                                                batch_state,
                                                batch_grammar_state)
            
            
            
            to_continue_mask = [i < (len(j)-1) for j in batch_list_inputs_passed]
            
            curr_batch_size = sum(to_continue_mask)
            
            next_batch_inputs = [inp[i] for inp in batch_list_inputs_passed if i < (len(inp)-1)]
            
            sp_from_idx = 0
            for i, (beamState, cont , cur_input) in enumerate(zip(beams, to_continue_mask, next_batch_inputs )):
                if(cont):
                    is_done = beamState.advance_initial_beam(cur_input)
            
            
            
            batch_inputs = Variable(tt.LongTensor(next_batch_inputs).view(-1, 1),
                                    requires_grad=False)
            
            batch_list_inputs = [[inp] for inp in next_batch_inputs]

            ## Which are the parents that we need to get the state for
            ## (potentially multiple times the same parent)
            parents_to_continue = [parent_idx for (parent_idx, to_cont)
                                   in zip(parent, to_continue_mask) if to_cont]
            parent = Variable(tt.LongTensor(parents_to_continue), requires_grad=False)
            
            ## Gather the output for the next step of the decoder
            
            batch_state = (
                dec_state[0].index_select(1, parent),
                dec_state[1].index_select(1, parent)
            )
    
            final_batch_state = (
                temp_h.index_copy_(1, prev_parent, dec_state[0]),
                temp_c.index_copy_(1, prev_parent, dec_state[1])   
            )
                
            prev_parent = parent
            batch_io_embeddings = batch_io_embeddings.index_select(0, parent)
            
        #Prepare for model learning
        batch_io_embeddings = io_embeddings     
        batch_list_inputs = [inp[-1] for inp in batch_list_inputs_passed]
        for i, (beamState , cur_input) in enumerate(zip(beams, batch_list_inputs )):
            is_done = beamState.advance_initial_beam(cur_input)
        
        batch_inputs = Variable(tt.LongTensor(batch_list_inputs).view(-1, 1),
                            requires_grad=False)
        curr_batch_size = batch_size
        batch_state = final_batch_state

        for stp in range(max_len):
            # We will just do the forward of one timestep Each of the inputs
            # for a beam appears as a different sample in the batch

            dec_outs, dec_state, \
            batch_grammar_state, _ = self.forward(batch_inputs,
                                                  batch_io_embeddings,
                                                  False,
                                                  batch_list_inputs,
                                                  batch_state,
                                                  batch_grammar_state)


            # Get the actual word probability for each beam
            dec_outs = dec_outs.squeeze(1)  # (batch_size*beam_size x nb_out_word)
            lpb_out = lsm(dec_outs)  # (batch_size*beam_size x nb_out_word)

            # Update all the beams, put out of the circulations the ones that
            # have completed
            new_inputs = []
            new_parent_idxs = []
            new_batch_idx = []
            new_beams_per_sp = []
            new_batch_checker = []
            new_batch_list_inputs = []

            sp_from_idx = 0
            lpb_to_use = lpb_out.data
            if force_beamcpu:
                lpb_to_use = lpb_to_use.cpu()
            for i, (beamState, sp_beam_size) in enumerate(zip(beams, beams_per_sp)):
                if beamState.done:
                    new_beams_per_sp.append(0)
                    continue
                sp_lpb = lpb_to_use.narrow(0, sp_from_idx, sp_beam_size)
                is_done = beamState.advance(sp_lpb)
                if is_done:
                    new_beams_per_sp.append(0)
                    sp_from_idx += sp_beam_size
                    continue

                # Get the input for the decoder at the next step
                sp_next_inputs, sp_next_input_list = beamState.get_next_input()
                sp_curr_beam_size = sp_next_inputs.size(0)
                sp_batch_inputs = sp_next_inputs.view(sp_curr_beam_size, 1)
                # Prepare so that for each beam, it's parent state is correct
                sp_parent_idx_among_beam = beamState.get_parent_beams()
                sp_parent_idxs = sp_parent_idx_among_beam + sp_from_idx
                if self.syntax_checker is not None:
                    for idx in sp_parent_idxs.data:
                        new_batch_checker.append(copy.copy(batch_grammar_state[idx]))
                sp_next_batch_idxs = Variable(tt.LongTensor(sp_curr_beam_size).fill_(i))
                # Get the idxs of the batches
                if use_cuda:
                    sp_batch_inputs = sp_batch_inputs.cuda()
                    sp_parent_idxs = sp_parent_idxs.cuda()
                new_inputs.append(sp_batch_inputs)
                new_beams_per_sp.append(sp_curr_beam_size)
                new_batch_idx.append(sp_next_batch_idxs)
                new_parent_idxs.append(sp_parent_idxs)
                new_batch_list_inputs.extend([[inp] for inp in sp_next_input_list])
                sp_from_idx += sp_beam_size

            assert(sp_from_idx == lpb_to_use.size(0))  # have we gone over all the things?
            if len(new_inputs)==0:
                # All of our beams are done
                break
            batch_inputs = torch.cat(new_inputs, 0)
            batch_idx = torch.cat(new_batch_idx, 0)
            parent_idxs = torch.cat(new_parent_idxs, 0)
            batch_list_inputs = new_batch_list_inputs

            batch_state = (
                dec_state[0].index_select(1, parent_idxs.type(torch.int64)),
                dec_state[1].index_select(1, parent_idxs.type(torch.int64))
                )
            if self.syntax_checker is not None:
                batch_grammar_state = new_batch_checker
            elif self.learned_syntax_checker is not None:
                batch_grammar_state = (
                    batch_grammar_state[0].index_select(1, parent_idxs),
                    batch_grammar_state[1].index_select(1, parent_idxs)
                )
            batch_io_embeddings = io_embeddings.index_select(0, batch_idx)
            beams_per_sp = new_beams_per_sp
            assert(len(beams_per_sp)==len(beams))
        sampled = []
        for i, beamState in enumerate(beams):
            sampled.append(beamState.get_sampled())
        return sampled
    
    def sample_model(self, io_embeddings,
                     batch_list_inputs_passed, tgt_end, max_len,
                     nb_rollouts):
        '''
        io_embeddings: batch_size x nb_ios x io_emb_size
        tgt_start: int -> Character indicating the start of the decoding
        tgt_end: int -> Character indicating the end of the decoding
        max_len: int -> How many tokens to sample from this rollout of the batch
        nb_rollouts: int -> How many rollouts to collect for each of the samples
                           of the batch
        '''
        # I will attempt to `detach` or create with `requires_grad=False` all
        # of the variables that won't need backpropagating through to ensure
        # that no spurious computation is done.
        if io_embeddings.is_cuda:
            use_cuda = True
            tt = torch.cuda
        else:
            use_cuda = False
            tt = torch
       
        # batch_size is going to be a changing thing, it correspond to how many
        # inputs we are passing through the decoder at once. Here, at
        # initialization, it is just the actual batch_size.
        batch_size, nb_ios, io_emb_size = io_embeddings.size()
        
        temp_h = (tt.FloatTensor(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size).fill_(0))
        temp_c = (tt.FloatTensor(self.nb_layers, batch_size, nb_ios, self.lstm_hidden_size).fill_(0))
       
        # rolls holds the sample output that we are going to collect for each
        # of the outputs

        # Initial proba for what is certainly sampled
        full_proba = Variable(tt.FloatTensor([1]), requires_grad=False)
        rolls = [Rolls(-1, full_proba, nb_rollouts, -1) for _ in range(batch_size)]
        
        sm = nn.Softmax(dim=1)

        ## Initialising the elements for the decoder
        curr_batch_size = batch_size  # Will vary as we go along in the decoder
    
        # batch_inputs: (curr_batch, ) -> inputs for the decoder step
        batch_state = None  # First one is the learned default state
        final_batch_state = None
        batch_grammar_state = None
        
        batch_inputs = Variable(tt.LongTensor(batch_size, 1).fill_(1))
        batch_list_inputs = [[1]]*batch_size

        batch_io_embeddings = io_embeddings
        # batch_io_embeddings: curr_batch x nb_ios x io_emb_size

        # Info that we will maintain at each timestep, for all of the traces
        # that we are currently expanding. All these list/tensors should have
        # same sizes.
        trajectories = [[] for _ in range(curr_batch_size)]
        # trajectories: List[ List[idx] ] -> trajectory for each trace that we
        #                                    are currently expanding
        multiplicity = [nb_rollouts for _ in range(curr_batch_size)]
        # multiplicity: List[ int ] -> How many of this trace have we sampled
        roll_idx_for_batchInput = [roll_idx for roll_idx in range(curr_batch_size)]
        # roll_idx_for_batchInput: List[ idx ] -> Which roll/sample is it a trace for
        parent =  [idx for idx in range(curr_batch_size)]
        prev_parent = [idx for idx in range(curr_batch_size)]
        prev_parent = Variable(tt.LongTensor(prev_parent), requires_grad=False)

        for i in range(1, (max(map(len,batch_list_inputs_passed)))):
            
            # Do the forward of one time step, for all our traces to expand
            dec_outs, dec_state, \
            _, _ = self.forward(batch_inputs,
                                                batch_io_embeddings,
                                                batch_list_inputs,
                                                batch_state,
                                                batch_grammar_state)
            
       
            
            to_continue_mask = [i < (len(j)-1) for j in batch_list_inputs_passed]
            
            curr_batch_size = sum(to_continue_mask)
            
            next_batch_inputs = [inp[i] for inp in batch_list_inputs_passed if i < (len(inp)-1)]
            
            
            
            batch_inputs = Variable(tt.LongTensor(next_batch_inputs).view(-1, 1),
                                    requires_grad=False)
            
            batch_list_inputs = [[inp] for inp in next_batch_inputs]

            ## Which are the parents that we need to get the state for
            ## (potentially multiple times the same parent)
            parents_to_continue = [parent_idx for (parent_idx, to_cont)
                                   in zip(parent, to_continue_mask) if to_cont]
            parent = Variable(tt.LongTensor(parents_to_continue), requires_grad=False)
            
            ## Gather the output for the next step of the decoder
            
            batch_state = (
                dec_state[0].index_select(1, parent),
                dec_state[1].index_select(1, parent)
            )
    
            final_batch_state = (
                temp_h.index_copy_(1, prev_parent, dec_state[0]),
                temp_c.index_copy_(1, prev_parent, dec_state[1])   
            )
                
            prev_parent = parent
            batch_io_embeddings = batch_io_embeddings.index_select(0, parent)
            
        #Prepare for model learning
        batch_io_embeddings = io_embeddings     
        batch_list_inputs = [inp[-1] for inp in batch_list_inputs_passed]
        batch_inputs = Variable(tt.LongTensor(batch_list_inputs).view(-1, 1),
                            requires_grad=False)
        curr_batch_size = batch_size
        batch_state = final_batch_state
        
        stp_no_grad =  { 5 : 0, 12 : 5, 15 : 12 }
           
        #for stp in range(max_len):
        for stp in range(max_len):
            no_grad = False
            if (stp < stp_no_grad[max_len]):
                no_grad = True
            # Do the forward of one time step, for all our traces to expand
            dec_outs, dec_state, \
            _, _ = self.forward(batch_inputs,
                                                  batch_io_embeddings,
                                                  batch_list_inputs,
                                                  no_grad,
                                                  batch_state,
                                                  batch_grammar_state)
            # dec_outs: curr_batch x 1 x nb_out_word
            # -> the unnormalized/pre-softmax proba for each word
            # dec_state: 2-tuple of nb_layers x curr_batch x nb_ios x dim

            dec_outs = dec_outs.squeeze(1)  # curr_batch x nb_out_word
            dec_out_probs = sm(dec_outs)           # curr_batch x nb_out_word
        
            
            ##TODEBUG
        #    print("dec_out_probs", dec_out_probs.data[0])

            # Prepare the container for what will need to be given to the next
            # steps
            new_trajectories = []
            new_multiplicity = []
            new_roll_idx_for_batchInput = []
            new_batch_list_inputs = []
            new_batch_checker = []

            # This needs to be collected for each of the samples we do
            parent = []      # -> idx of the trace of this sampled output
            next_input = []  # -> sampled output
            sp_proba = []    # -> proba of the sampled output
            
            for trace_idx in range(curr_batch_size):
                new_batch_list_inputs.append([])
                # Iterate over the current trace prefixes that we have
                idx_per_sample = {}  # -> to group the samples that are same

                # We have sampled `multiplicity[trace_idx]` this prefix trace,
                # we try to continue it `multiplicity[trace_idx]` times.
                # This sample is done with replacement.
                choices = torch.multinomial(dec_out_probs.data[trace_idx],
                                            multiplicity[trace_idx],
                                            True)
        
                ##TODEBUG
                #print("choices", choices)
                # choices: (multiplicity, ) -> sampled output

                # We will now join the samples that are identical, to not
                # duplicate their computation
                for sampled in choices:
                    if sampled in idx_per_sample:
                        # We already have this one, just increase its
                        # multiplicity
                        
                        new_multiplicity[idx_per_sample[sampled]] += 1
                    else:
                        # Bookkeeping so that the future ones similar can be
                        # grouped to this one.
                        idx_per_sample[sampled] = len(new_trajectories)
                        
                        # The trajectory that this now creates:prefix + new elt
                        new_traj = trajectories[trace_idx] + [sampled] ###########
                        new_trajectories.append(new_traj)

                        sp_proba.append(dec_out_probs[trace_idx, sampled])

                        # It belongs to the same samples that his prefix
                        # belonged to
                        new_roll_idx_for_batchInput.append(roll_idx_for_batchInput[trace_idx])

                        # The prefix for this one was trace_idx in the previous
                        # batch
                        parent.append(trace_idx)

                        # What will need to be fed in the decoder to continue
                        # this new trace created
                        next_input.append(sampled)

                        # This is the first one that we see so it will have a
                        # multiplicity of 1 for now
                        new_multiplicity.append(1)
                        
                        
            # Add these new samples to our book-keeping of all samples
            for traj, multiplicity, cur_roll_idx, sp_pb in zip(new_trajectories,
                                                     new_multiplicity,
                                                     new_roll_idx_for_batchInput,
                                                     sp_proba):
               
                rolls[cur_roll_idx].expand_samples(traj, multiplicity, sp_pb)
                
            
            to_continue_mask = [((inp != tgt_end) or (inp == tgt_end)) for inp in next_input]
           
            # For the next step, drop everything that we don't need to pursue
            # because they reached the end symbol
            curr_batch_size = sum(to_continue_mask)
            if curr_batch_size == 0:
                # There is nothing left to sample from
                break
            # Extract the ones we need to continue
            next_batch_inputs = [inp for inp in next_input ]
            batch_inputs = Variable(tt.LongTensor(next_batch_inputs).view(-1, 1),
                                    requires_grad=False)
            batch_list_inputs = [[inp] for inp in next_batch_inputs]
            
            # Which are the parents that we need to get the state for
            # (potentially multiple times the same parent)
            parents_to_continue = [parent_idx for (parent_idx, to_cont)
                                   in zip(parent, to_continue_mask) if to_cont]
            parent = Variable(tt.LongTensor(parents_to_continue), requires_grad=False)
            
            ## Gather the output for the next step of the decoder
            # parent: curr_batch_size
            batch_state = (
                dec_state[0].index_select(1, parent),
                dec_state[1].index_select(1, parent)
            )
            batch_io_embeddings = batch_io_embeddings.index_select(0, parent)
            
            # For all the maintained list, keep only the elt to expand
            joint = [(mul, traj, cr) for mul, traj, cr, to_cont
                     in zip(new_multiplicity,
                            new_trajectories,
                            new_roll_idx_for_batchInput,
                            to_continue_mask)
                     if to_cont]
            ##TODEBUG
            #print('joint', joint)
            multiplicity, trajectories, roll_idx_for_batchInput = zip(*joint)

            
        return rolls

class GridEncoder(nn.Module):
    def __init__(self, kernel_size, conv_stack, fc_stack):
        '''
        kernel_size: width of the kernels
        conv_stack: Number of channels at each point of the convolutional part of
                    the network (includes the input)
        fc_stack: number of channels in the fully connected part of the network
        '''
        super(GridEncoder, self).__init__()
        self.conv_layers = []
        for i in range(1, len(conv_stack)):
            if conv_stack[i-1] != conv_stack[i]:
                block = nn.Sequential(
                    ResBlock(kernel_size, conv_stack[i-1]),
                    nn.Conv2d(conv_stack[i-1], conv_stack[i],
                              kernel_size=kernel_size, padding=(kernel_size-1)//2 ),
                    nn.ReLU(inplace=True)
                )
            else:
                block = ResBlock(kernel_size, conv_stack[i-1])
            self.conv_layers.append(block)
            self.add_module("ConvBlock-" + str(i-1), self.conv_layers[-1])

        # We have operated so far to preserve all of the spatial dimensions so
        # we can estimate the flattened dimension.
        first_fc_dim = conv_stack[-1] * IMG_SIZE[-1]* IMG_SIZE[-2]
        adjusted_fc_stack = [first_fc_dim] + fc_stack
        self.fc_layers = []
       
        for i in range(1, len(adjusted_fc_stack)):
            self.fc_layers.append(nn.Linear(adjusted_fc_stack[i-1],
                                            adjusted_fc_stack[i]))
            self.add_module("FC-" + str(i-1), self.fc_layers[-1])
        # TODO: init?

    def forward(self, x):
        '''
        x: batch_size x channels x Height x Width
        '''
        batch_size = x.size(0)

        # Convolutional part
        for conv_layer in self.conv_layers:
            x = conv_layer(x)

        # Flatten for the fully connected part
        x = x.view(batch_size, -1)
        # Fully connected part
        for i in range(len(self.fc_layers) - 1):
            x = F.relu(self.fc_layers[i](x))
        x = self.fc_layers[-1](x)

        return x

class ResBlock(nn.Module):
    def __init__(self, kernel_size, in_feats):
        '''
        kernel_size: width of the kernels
        in_feats: number of channels in inputs
        '''
        super(ResBlock, self).__init__()
        self.feat_size = in_feats
        self.kernel_size = kernel_size
        self.padding = (kernel_size - 1) // 2

        self.conv1 = nn.Conv2d(self.feat_size, self.feat_size,
                               kernel_size=self.kernel_size,
                               padding=self.padding)
        self.conv2 = nn.Conv2d(self.feat_size, self.feat_size,
                               kernel_size=self.kernel_size,
                               padding=self.padding)
        self.conv3 = nn.Conv2d(self.feat_size, self.feat_size,
                               kernel_size=self.kernel_size,
                               padding=self.padding)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x):
        residual = x

        out = self.conv1(x)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.relu(out)

        out = self.conv3(out)

        out += residual
        out = self.relu(out)

        return out
        
class IOsEncoder(nn.Module):
    def __init__(self, kernel_size, conv_stack, fc_stack):
        super(IOsEncoder, self).__init__()

        ## Do one layer of convolution before stacking

        # Deduce the size of the embedding for each grid
        initial_dim = conv_stack[0] // 2  # Because we are going to get dim from I and dim from O

        # TODO: we know that our grids are mostly sparse, and only positive.
        # That means that a different initialisation might be more appropriate.
        self.in_grid_enc = MapModule(nn.Sequential(
            nn.Conv2d(IMG_SIZE[0], initial_dim, kernel_size=kernel_size, padding=(kernel_size -1)//2),
            nn.ReLU(inplace=True)
        ), 3)
        self.out_grid_enc = MapModule(nn.Sequential(
            nn.Conv2d(IMG_SIZE[0], initial_dim,kernel_size=kernel_size, padding=(kernel_size -1)//2),
            nn.ReLU(inplace=True)
        ), 3)

        # Define the model that works on the stacking
        self.joint_enc = MapModule(nn.Sequential(
            GridEncoder(kernel_size, conv_stack, fc_stack)
        ), 3)

    def forward(self, input_grids, output_grids):
        '''
        {input, output}_grids: batch_size x nb_ios x channels x height x width
        '''
        inp_emb = self.in_grid_enc(input_grids)
        out_emb = self.out_grid_enc(output_grids)
        # {inp, out}_emb: batch_size x nb_ios x feats x height x width

        io_emb = torch.cat([inp_emb, out_emb], 2)
        # io_emb: batch_size x nb_ios x 2 * feats x height x width
        joint_emb = self.joint_enc(io_emb)
        # return joint_emb
        return joint_emb
        
class IOs2Seq(nn.Module):

    def __init__(self,
                 # IO encoder
                 kernel_size, conv_stack, fc_stack,
                 # Program Decoder
                 tgt_vocabulary_size,
                 tgt_embedding_dim,
                 decoder_lstm_hidden_size,
                 decoder_nb_lstm_layers,
                 learn_syntax):
        super(IOs2Seq, self).__init__()
        self.encoder = IOsEncoder(kernel_size, conv_stack, fc_stack)
        io_emb_size = fc_stack[-1]
        self.decoder = MultiIOProgramDecoder(tgt_vocabulary_size,
                                             tgt_embedding_dim,
                                             io_emb_size,
                                             decoder_lstm_hidden_size,
                                             decoder_nb_lstm_layers,
                                             learn_syntax)
                                             
                                             
    def forward(self, input_grids, output_grids, tgt_inp_sequences, list_inp_sequences):

        io_embedding = self.encoder(input_grids, output_grids)
        dec_outs, _, _, syntax_mask = self.decoder(tgt_inp_sequences,
                                                   io_embedding,
                                                   list_inp_sequences)
        return dec_outs, syntax_mask
    
    def score_multiple_decs(self, input_grids, output_grids,
                            tgt_inp_sequences, list_inp_sequences,
                            tgt_out_sequences, nb_cand_per_sp):
        '''
        {input,output}_grids: input_batch_size x nb_ios x channels x height x width
        tgt_{inp,out}_sequences: nb_seq_to_score x max_seq_len
        list_inp_sequences: same as tgt_inp_sequences but under list form
        nb_cand_per_sp: Indicate how many sequences each of the row of {input,output}_grids represent
        '''
        assert sum(nb_cand_per_sp) == tgt_inp_sequences.size(0)
        assert len(nb_cand_per_sp) == input_grids.size(0)
        batch_size, seq_len = tgt_inp_sequences.size()
        io_embedding = self.encoder(input_grids, output_grids)

        io_emb_dims = io_embedding.size()[1:]
        expands = [(nb_cands, ) + io_emb_dims for nb_cands in nb_cand_per_sp]
        # Reshape the io_embedding to have one per input samples
        all_io_embs = torch.cat([io_embedding.narrow(0, pos, 1).expand(*exp_dim)
                                 for pos, exp_dim in enumerate(expands)], 0)

        dec_outs, _, _, _ = self.decoder(tgt_inp_sequences,
                                         all_io_embs,
                                         list_inp_sequences)

        # We need to get a logsoftmax at each timestep
        dec_outs = dec_outs.contiguous().view(batch_size*seq_len, -1)
        lpb = F.log_softmax(dec_outs, dim=1)
        lpb = lpb.view(batch_size, seq_len, -1)

        out_lpb = torch.gather(lpb, 2, tgt_out_sequences.unsqueeze(2)).squeeze(2)
        
        return out_lpb
        
    def beam_sample(self, input_grids, output_grids,
                    tgt_start, tgt_end, max_len,
                    beam_size, top_k, vol=True):
        io_embedding = self.encoder(input_grids, output_grids)

        sampled = self.decoder.beam_sample(io_embedding,
                                           tgt_start, tgt_end, max_len,
                                           beam_size, top_k, vol)
        return sampled
    
    def sample_model(self, input_grids, output_grids,
                     tgt_start, tgt_end, max_len,
                     nb_rollouts, vol=True):
        # Do the encoding of the source_sequence.
        io_embedding = self.encoder(input_grids, output_grids)

        rolls = self.decoder.sample_model(io_embedding,
                                          tgt_start, tgt_end, max_len,
                                          nb_rollouts)
        return rolls
