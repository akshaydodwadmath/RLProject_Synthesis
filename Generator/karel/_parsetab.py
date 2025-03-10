
# _parsetab.py
# This file is automatically generated. Do not edit.
# pylint: disable=W,C,R
_tabversion = '3.10'

_lr_method = 'LALR'

_lr_signature = 'C_LBRACE C_RBRACE DEF ELSE E_LBRACE E_RBRACE FRONT_IS_CLEAR IF IFELSE INT I_LBRACE I_RBRACE LEFT_IS_CLEAR MARKERS_PRESENT MOVE M_LBRACE M_RBRACE NOT NO_MARKERS_PRESENT PICK_MARKER PUT_MARKER REPEAT RIGHT_IS_CLEAR RUN R_LBRACE R_RBRACE TURN_LEFT TURN_RIGHT WHILE W_LBRACE W_RBRACEprog : DEF RUN M_LBRACE action3 action3 stmt_fixed  M_RBRACEstmt_fixed : stmt\n        stmt : while\n                | repeat\n                | stmt_stmt\n                | action\n                | if\n                | ifelse\n        stmt_stmt : stmt stmt\n        if : IF C_LBRACE cond C_RBRACE I_LBRACE stmt I_RBRACE\n        ifelse : IFELSE C_LBRACE cond C_RBRACE I_LBRACE stmt I_RBRACE ELSE E_LBRACE stmt E_RBRACE\n        while : WHILE C_LBRACE cond C_RBRACE W_LBRACE stmt W_RBRACE\n        repeat : REPEAT cste R_LBRACE stmt R_RBRACE\n        cond : cond_without_not\n                | NOT C_LBRACE cond_without_not C_RBRACE\n        cond_without_not : FRONT_IS_CLEAR\n                            | LEFT_IS_CLEAR\n                            | RIGHT_IS_CLEAR\n                            | MARKERS_PRESENT\n                            | NO_MARKERS_PRESENT\n        action3 :  action action  action \n        action : MOVE\n                  | TURN_RIGHT\n                  | TURN_LEFT\n                  | PICK_MARKER\n                  | PUT_MARKER\n        cste : INT\n        '
    
_lr_action_items = {'DEF':([0,],[2,]),'$end':([1,27,],[0,-1,]),'RUN':([2,],[3,]),'M_LBRACE':([3,],[4,]),'MOVE':([4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[7,7,7,-22,-23,-24,-25,-26,7,7,7,-3,-4,-5,-6,-7,-8,-21,7,7,7,7,-13,7,7,7,7,7,-12,-10,7,7,-11,]),'TURN_RIGHT':([4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[8,8,8,-22,-23,-24,-25,-26,8,8,8,-3,-4,-5,-6,-7,-8,-21,8,8,8,8,-13,8,8,8,8,8,-12,-10,8,8,-11,]),'TURN_LEFT':([4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[9,9,9,-22,-23,-24,-25,-26,9,9,9,-3,-4,-5,-6,-7,-8,-21,9,9,9,9,-13,9,9,9,9,9,-12,-10,9,9,-11,]),'PICK_MARKER':([4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[10,10,10,-22,-23,-24,-25,-26,10,10,10,-3,-4,-5,-6,-7,-8,-21,10,10,10,10,-13,10,10,10,10,10,-12,-10,10,10,-11,]),'PUT_MARKER':([4,5,6,7,8,9,10,11,12,13,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[11,11,11,-22,-23,-24,-25,-26,11,11,11,-3,-4,-5,-6,-7,-8,-21,11,11,11,11,-13,11,11,11,11,11,-12,-10,11,11,-11,]),'WHILE':([7,8,9,10,11,12,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[-22,-23,-24,-25,-26,22,22,-3,-4,-5,-6,-7,-8,-21,22,22,22,22,-13,22,22,22,22,22,-12,-10,22,22,-11,]),'REPEAT':([7,8,9,10,11,12,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[-22,-23,-24,-25,-26,23,23,-3,-4,-5,-6,-7,-8,-21,23,23,23,23,-13,23,23,23,23,23,-12,-10,23,23,-11,]),'IF':([7,8,9,10,11,12,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[-22,-23,-24,-25,-26,24,24,-3,-4,-5,-6,-7,-8,-21,24,24,24,24,-13,24,24,24,24,24,-12,-10,24,24,-11,]),'IFELSE':([7,8,9,10,11,12,15,16,17,18,19,20,21,26,28,42,47,50,52,53,54,55,57,58,59,60,63,64,65,],[-22,-23,-24,-25,-26,25,25,-3,-4,-5,-6,-7,-8,-21,25,25,25,25,-13,25,25,25,25,25,-12,-10,25,25,-11,]),'M_RBRACE':([7,8,9,10,11,14,15,16,17,18,19,20,21,28,52,59,60,65,],[-22,-23,-24,-25,-26,27,-2,-3,-4,-5,-6,-7,-8,-9,-13,-12,-10,-11,]),'R_RBRACE':([7,8,9,10,11,16,17,18,19,20,21,28,47,52,59,60,65,],[-22,-23,-24,-25,-26,-3,-4,-5,-6,-7,-8,-9,52,-13,-12,-10,-11,]),'W_RBRACE':([7,8,9,10,11,16,17,18,19,20,21,28,52,55,59,60,65,],[-22,-23,-24,-25,-26,-3,-4,-5,-6,-7,-8,-9,-13,59,-12,-10,-11,]),'I_RBRACE':([7,8,9,10,11,16,17,18,19,20,21,28,52,57,58,59,60,65,],[-22,-23,-24,-25,-26,-3,-4,-5,-6,-7,-8,-9,-13,60,61,-12,-10,-11,]),'E_RBRACE':([7,8,9,10,11,16,17,18,19,20,21,28,52,59,60,64,65,],[-22,-23,-24,-25,-26,-3,-4,-5,-6,-7,-8,-9,-13,-12,-10,65,-11,]),'C_LBRACE':([22,24,25,36,],[29,32,33,46,]),'INT':([23,],[31,]),'NOT':([29,32,33,],[36,36,36,]),'FRONT_IS_CLEAR':([29,32,33,46,],[37,37,37,37,]),'LEFT_IS_CLEAR':([29,32,33,46,],[38,38,38,38,]),'RIGHT_IS_CLEAR':([29,32,33,46,],[39,39,39,39,]),'MARKERS_PRESENT':([29,32,33,46,],[40,40,40,40,]),'NO_MARKERS_PRESENT':([29,32,33,46,],[41,41,41,41,]),'R_LBRACE':([30,31,],[42,-27,]),'C_RBRACE':([34,35,37,38,39,40,41,43,44,51,56,],[45,-14,-16,-17,-18,-19,-20,48,49,56,-15,]),'W_LBRACE':([45,],[50,]),'I_LBRACE':([48,49,],[53,54,]),'ELSE':([61,],[62,]),'E_LBRACE':([62,],[63,]),}

_lr_action = {}
for _k, _v in _lr_action_items.items():
   for _x,_y in zip(_v[0],_v[1]):
      if not _x in _lr_action:  _lr_action[_x] = {}
      _lr_action[_x][_k] = _y
del _lr_action_items

_lr_goto_items = {'prog':([0,],[1,]),'action3':([4,5,],[5,12,]),'action':([4,5,6,12,13,15,28,42,47,50,53,54,55,57,58,63,64,],[6,6,13,19,26,19,19,19,19,19,19,19,19,19,19,19,19,]),'stmt_fixed':([12,],[14,]),'stmt':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[15,28,28,47,28,55,57,58,28,28,28,64,28,]),'while':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[16,16,16,16,16,16,16,16,16,16,16,16,16,]),'repeat':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[17,17,17,17,17,17,17,17,17,17,17,17,17,]),'stmt_stmt':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[18,18,18,18,18,18,18,18,18,18,18,18,18,]),'if':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[20,20,20,20,20,20,20,20,20,20,20,20,20,]),'ifelse':([12,15,28,42,47,50,53,54,55,57,58,63,64,],[21,21,21,21,21,21,21,21,21,21,21,21,21,]),'cste':([23,],[30,]),'cond':([29,32,33,],[34,43,44,]),'cond_without_not':([29,32,33,46,],[35,35,35,51,]),}

_lr_goto = {}
for _k, _v in _lr_goto_items.items():
   for _x, _y in zip(_v[0], _v[1]):
       if not _x in _lr_goto: _lr_goto[_x] = {}
       _lr_goto[_x][_k] = _y
del _lr_goto_items
_lr_productions = [
  ("S' -> prog","S'",1,None,None,None),
  ('prog -> DEF RUN M_LBRACE action3 action3 stmt_fixed M_RBRACE','prog',7,'p_prog','parser_for_synthesis.py',103),
  ('stmt_fixed -> stmt','stmt_fixed',1,'p_stmt_fixed','parser_for_synthesis.py',114),
  ('stmt -> while','stmt',1,'p_stmt','parser_for_synthesis.py',120),
  ('stmt -> repeat','stmt',1,'p_stmt','parser_for_synthesis.py',121),
  ('stmt -> stmt_stmt','stmt',1,'p_stmt','parser_for_synthesis.py',122),
  ('stmt -> action','stmt',1,'p_stmt','parser_for_synthesis.py',123),
  ('stmt -> if','stmt',1,'p_stmt','parser_for_synthesis.py',124),
  ('stmt -> ifelse','stmt',1,'p_stmt','parser_for_synthesis.py',125),
  ('stmt_stmt -> stmt stmt','stmt_stmt',2,'p_stmt_stmt','parser_for_synthesis.py',135),
  ('if -> IF C_LBRACE cond C_RBRACE I_LBRACE stmt I_RBRACE','if',7,'p_if','parser_for_synthesis.py',145),
  ('ifelse -> IFELSE C_LBRACE cond C_RBRACE I_LBRACE stmt I_RBRACE ELSE E_LBRACE stmt E_RBRACE','ifelse',11,'p_ifelse','parser_for_synthesis.py',174),
  ('while -> WHILE C_LBRACE cond C_RBRACE W_LBRACE stmt W_RBRACE','while',7,'p_while','parser_for_synthesis.py',205),
  ('repeat -> REPEAT cste R_LBRACE stmt R_RBRACE','repeat',5,'p_repeat','parser_for_synthesis.py',227),
  ('cond -> cond_without_not','cond',1,'p_cond','parser_for_synthesis.py',249),
  ('cond -> NOT C_LBRACE cond_without_not C_RBRACE','cond',4,'p_cond','parser_for_synthesis.py',250),
  ('cond_without_not -> FRONT_IS_CLEAR','cond_without_not',1,'p_cond_without_not','parser_for_synthesis.py',262),
  ('cond_without_not -> LEFT_IS_CLEAR','cond_without_not',1,'p_cond_without_not','parser_for_synthesis.py',263),
  ('cond_without_not -> RIGHT_IS_CLEAR','cond_without_not',1,'p_cond_without_not','parser_for_synthesis.py',264),
  ('cond_without_not -> MARKERS_PRESENT','cond_without_not',1,'p_cond_without_not','parser_for_synthesis.py',265),
  ('cond_without_not -> NO_MARKERS_PRESENT','cond_without_not',1,'p_cond_without_not','parser_for_synthesis.py',266),
  ('action3 -> action action action','action3',3,'p_action3','parser_for_synthesis.py',276),
  ('action -> MOVE','action',1,'p_action','parser_for_synthesis.py',286),
  ('action -> TURN_RIGHT','action',1,'p_action','parser_for_synthesis.py',287),
  ('action -> TURN_LEFT','action',1,'p_action','parser_for_synthesis.py',288),
  ('action -> PICK_MARKER','action',1,'p_action','parser_for_synthesis.py',289),
  ('action -> PUT_MARKER','action',1,'p_action','parser_for_synthesis.py',290),
  ('cste -> INT','cste',1,'p_cste','parser_for_synthesis.py',299),
]
