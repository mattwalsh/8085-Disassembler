# to allow forward references
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import ClassVar, List
from enum import Enum, auto
import copy

# ROM is from 0x0 to 0x1fff 
# TODO: void SHLD / LHLD that are outside of 0x2000 and 0x23ff

allInstructions = {}

class BranchType(Enum):
   JUMP = auto()
   CALL = auto()
   RETURN = auto()
   RESTART = auto()

class InstrType(Enum):
   CONTROL = auto()
   PORT = auto()
   BRANCH = auto()
   ARITHMETIC = auto()
   MOVE = auto()
   DATA = auto()
   JUNK = auto()

class OperandType(Enum):
   NONE = auto()
   IMMEDIATE = auto()
   ADDRESS = auto()
   IMMEDIATE_HYBRID = auto()
   CHARACTER = auto()

class Address(BaseModel):
   address : int
   
   def __init__(self, addressIn, **kwargs):
      kwargs.update({'address' : addressIn})
      super().__init__(**kwargs)

   def __hash__(self):
      return self.address

   def rawAddr(self):
      return f"{format(self.address, '04x')}"
   
   def __str__(self):
      if self.address in Instruction.syms:
         return Instruction.syms[self.address]
      else:
         return f"${self.rawAddr()}"

class Label(BaseModel):
   labels  : ClassVar[List[Label]] = {}
   address : Address
   jumpers : List[Instruction] = []
   isOrigin : bool = False
   isJump: bool = False
   isCall: bool = False

   @classmethod
   def makeLabel(self, address):
      if address not in Label.labels:
         label = Label(address = address)
         Label.labels[address] = label
      else:
         label = Label.labels[address]
      return label   

   def setOrigin(self):
      self.isOrigin = True

   def addCaller(self, instruction):
      self.jumpers.append(instruction)
      if instruction.branchType == BranchType.JUMP:
         self.isJump = True
      elif instruction.branchType == BranchType.CALL:
         self.isCall = True
      return

   def __str__(self):
      prefix = ""
      if self.isJump:
         prefix = prefix + "j"
      if self.isCall:
         prefix = prefix + "c"
      if self.isOrigin:
         prefix = prefix + "o"

      return f"{prefix}{self.address.rawAddr()}"  ## probably garbage

   def infoString(self):
      out = ""
      for j in self.jumpers:
         if out == "":
            out = j.label.__str__()
         else:
            out = out + "," + j.label.__str__()

      return out

class Instruction(BaseModel):
   opcode : int 
   mnemonic : str
   insType : InstrType
   numOperands : int
   operandType : OperandType
   origInstrStr : str = None
   branchType : BranchType = None

   alli : ClassVar[dict]  = {}
   syms : ClassVar[dict[int, string]]  = {}
   ports : ClassVar[dict[int, string]]  = {}

   label : Label = None

   operand1 : int = None
   operand2 : int = None

   address : Address = None

   targetAddress : Address = None
   targetLabel : Label = None

   def __init__(self, **data):
      super().__init__(**data)
      Instruction.alli[self.opcode] = self

   def instantiate(self, operand1 = None, operand2 = None):
      newInstr = copy.deepcopy(self)
      newInstr.operand1 = operand1  
      newInstr.operand2 = operand2 
    
      if newInstr.operandType == OperandType.ADDRESS:
         newInstr.targetAddress = Address(int(newInstr.operand1 + (newInstr.operand2 << 8)))
   
      return newInstr

   def __str__(self):
      out = ""
      if self.label is not None:
         l = self.label.__str__()
         out = out + f"{l}:" + (" "*(7 - len(l)))
      else:
         out = out + (" "*8)

      if self.insType == InstrType.JUNK:
         out = out + f"DB {hex(self.opcode)}"

         if self.numOperands > 0:
            out = out + f",{hex(self.operand1)}"
         if self.numOperands > 1:
            out = out + f",{hex(self.operand2)}"

         out = out + f"  ; (was: {self.origInstrStr})"

      else:      
         out = out + f"{self.mnemonic}"

         if self.insType == InstrType.PORT:
            if self.operand1 in Instruction.ports:
               out = out + f" {Instruction.ports[self.operand1]}"
            else:
               out = out + f" #{format(self.operand1, '02x')}"
                 
         else:
            if self.operandType == OperandType.ADDRESS:
               if self.targetLabel is not None:
                  out = out + f" {self.targetLabel}"
               else:
                  out = out + f" {self.targetAddress}"

            else:
               if self.numOperands == 1:
                  out = out + f" #{format(self.operand1, '02x')}"
               elif self.numOperands == 2:
                  addr = (self.operand2 << 8) + self.operand1
                  out = out + f" #{format(addr, '04x')}"

      if self.label:
         s = self.label.infoString()
         if s:
            out = out + " ;" + s

      return out

   def junk(self):
      self.origInstrStr = self.__str__()
      self.insType = InstrType.JUNK

# https://pastraiser.com/cpu/i8085/i8085_opcodes.html
Instruction(opcode = 0x0, mnemonic = "NOP", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1, mnemonic = "LXI B,", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.IMMEDIATE_HYBRID)
Instruction(opcode = 0x2, mnemonic = "STAX B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x3, mnemonic = "INX B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4, mnemonic = "INR B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5, mnemonic = "DCR B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6, mnemonic = "MVI B,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x7, mnemonic = "RLC", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8, mnemonic = "(DSUB)", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9, mnemonic = "DAD B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa, mnemonic = "LDAX B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb, mnemonic = "DCX B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xc, mnemonic = "INR C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xd, mnemonic = "DCR C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe, mnemonic = "MVI C,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xf, mnemonic = "RRC", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x10, mnemonic = "(ARHL)", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x11, mnemonic = "LXI D,", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.IMMEDIATE_HYBRID)
Instruction(opcode = 0x12, mnemonic = "STAX D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x13, mnemonic = "INX D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x14, mnemonic = "INR D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x15, mnemonic = "DCR D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x16, mnemonic = "MVI D,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x17, mnemonic = "RAL", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x18, mnemonic = "(RLDE)", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x19, mnemonic = "DAD D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1a, mnemonic = "LDAX D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1b, mnemonic = "DCX D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1c, mnemonic = "INR E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1d, mnemonic = "DCR E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x1e, mnemonic = "MVI E,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x1f, mnemonic = "RAR", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x20, mnemonic = "RIM", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x21, mnemonic = "LXI H,", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.IMMEDIATE_HYBRID)
Instruction(opcode = 0x22, mnemonic = "SHLD", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.ADDRESS)
Instruction(opcode = 0x23, mnemonic = "INX H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x24, mnemonic = "INR H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x25, mnemonic = "DCR H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x26, mnemonic = "MVI H,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x27, mnemonic = "DAA", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x28, mnemonic = "(LDHI)", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x29, mnemonic = "DAD H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x2a, mnemonic = "LHLD", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.ADDRESS)
Instruction(opcode = 0x2b, mnemonic = "DCX H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x2c, mnemonic = "INR L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x2d, mnemonic = "DCR L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x2e, mnemonic = "MVI L,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x2f, mnemonic = "CMA", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x30, mnemonic = "SIM", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x31, mnemonic = "LXI SP,", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.IMMEDIATE_HYBRID)
Instruction(opcode = 0x32, mnemonic = "STA", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.ADDRESS)
Instruction(opcode = 0x33, mnemonic = "INX SP", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x34, mnemonic = "INR M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x35, mnemonic = "DCR M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x36, mnemonic = "MVI M,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x37, mnemonic = "STC", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x38, mnemonic = "(LDSI)", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x39, mnemonic = "DAD SP", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x3a, mnemonic = "LDA", insType=InstrType.MOVE, numOperands=2, operandType = OperandType.ADDRESS)
Instruction(opcode = 0x3b, mnemonic = "DCX SP", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x3c, mnemonic = "INR A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x3d, mnemonic = "DCR A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x3e, mnemonic = "MVI A,", insType=InstrType.MOVE, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0x3f, mnemonic = "CMC", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x40, mnemonic = "MOV B,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x41, mnemonic = "MOV B,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x42, mnemonic = "MOV B,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x43, mnemonic = "MOV B,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x44, mnemonic = "MOV B,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x45, mnemonic = "MOV B,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x46, mnemonic = "MOV B,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x47, mnemonic = "MOV B,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x48, mnemonic = "MOV C,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x49, mnemonic = "MOV C,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4a, mnemonic = "MOV C,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4b, mnemonic = "MOV C,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4c, mnemonic = "MOV C,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4d, mnemonic = "MOV C,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4e, mnemonic = "MOV C,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x4f, mnemonic = "MOV C,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x50, mnemonic = "MOV D,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x51, mnemonic = "MOV D,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x52, mnemonic = "MOV D,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x53, mnemonic = "MOV D,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x54, mnemonic = "MOV D,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x55, mnemonic = "MOV D,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x56, mnemonic = "MOV D,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x57, mnemonic = "MOV D,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x58, mnemonic = "MOV E,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x59, mnemonic = "MOV E,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5a, mnemonic = "MOV E,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5b, mnemonic = "MOV E,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5c, mnemonic = "MOV E,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5d, mnemonic = "MOV E,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5e, mnemonic = "MOV E,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x5f, mnemonic = "MOV E,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x60, mnemonic = "MOV H,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x61, mnemonic = "MOV H,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x62, mnemonic = "MOV H,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x63, mnemonic = "MOV H,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x64, mnemonic = "MOV H,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x65, mnemonic = "MOV H,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x66, mnemonic = "MOV H,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x67, mnemonic = "MOV H,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x68, mnemonic = "MOV L,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x69, mnemonic = "MOV L,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6a, mnemonic = "MOV L,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6b, mnemonic = "MOV L,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6c, mnemonic = "MOV L,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6d, mnemonic = "MOV L,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6e, mnemonic = "MOV L,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x6f, mnemonic = "MOV L,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x70, mnemonic = "MOV M,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x71, mnemonic = "MOV M,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x72, mnemonic = "MOV M,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x73, mnemonic = "MOV M,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x74, mnemonic = "MOV M,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x75, mnemonic = "MOV M,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x76, mnemonic = "HLT", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x77, mnemonic = "MOV M,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x78, mnemonic = "MOV A,B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x79, mnemonic = "MOV A,C", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7a, mnemonic = "MOV A,D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7b, mnemonic = "MOV A,E", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7c, mnemonic = "MOV A,H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7d, mnemonic = "MOV A,L", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7e, mnemonic = "MOV A,M", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x7f, mnemonic = "MOV A,A", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x80, mnemonic = "ADD B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x81, mnemonic = "ADD C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x82, mnemonic = "ADD D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x83, mnemonic = "ADD E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x84, mnemonic = "ADD H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x85, mnemonic = "ADD L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x86, mnemonic = "ADD M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x87, mnemonic = "ADD A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x88, mnemonic = "ADC B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x89, mnemonic = "ADC C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8a, mnemonic = "ADC D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8b, mnemonic = "ADC E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8c, mnemonic = "ADC H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8d, mnemonic = "ADC L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8e, mnemonic = "ADC M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x8f, mnemonic = "ADC A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x90, mnemonic = "SUB B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x91, mnemonic = "SUB C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x92, mnemonic = "SUB D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x93, mnemonic = "SUB E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x94, mnemonic = "SUB H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x95, mnemonic = "SUB L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x96, mnemonic = "SUB M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x97, mnemonic = "SUB A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x98, mnemonic = "SBB B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x99, mnemonic = "SBB C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9a, mnemonic = "SBB D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9b, mnemonic = "SBB E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9c, mnemonic = "SBB H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9d, mnemonic = "SBB L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9e, mnemonic = "SBB M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0x9f, mnemonic = "SBB A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa0, mnemonic = "ANA B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa1, mnemonic = "ANA C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa2, mnemonic = "ANA D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa3, mnemonic = "ANA E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa4, mnemonic = "ANA H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa5, mnemonic = "ANA L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa6, mnemonic = "ANA M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa7, mnemonic = "ANA A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa8, mnemonic = "XRA B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xa9, mnemonic = "XRA C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xaa, mnemonic = "XRA D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xab, mnemonic = "XRA E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xac, mnemonic = "XRA H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xad, mnemonic = "XRA L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xae, mnemonic = "XRA M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xaf, mnemonic = "XRA A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb0, mnemonic = "ORA B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb1, mnemonic = "ORA C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb2, mnemonic = "ORA D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb3, mnemonic = "ORA E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb4, mnemonic = "ORA H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb5, mnemonic = "ORA L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb6, mnemonic = "ORA M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb7, mnemonic = "ORA A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb8, mnemonic = "CMP B", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xb9, mnemonic = "CMP C", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xba, mnemonic = "CMP D", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xbb, mnemonic = "CMP E", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xbc, mnemonic = "CMP H", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xbd, mnemonic = "CMP L", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xbe, mnemonic = "CMP M", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xbf, mnemonic = "CMP A", insType=InstrType.ARITHMETIC, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xc0, mnemonic = "RNZ", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xc1, mnemonic = "POP B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xc2, mnemonic = "JNZ", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xc3, mnemonic = "JMP", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xc4, mnemonic = "CNZ", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xc5, mnemonic = "PUSH B", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xc6, mnemonic = "ADI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xc7, mnemonic = "RST 0", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xc8, mnemonic = "RZ", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xc9, mnemonic = "RET", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xca, mnemonic = "JZ", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)

# restarts on overflow, PC => 0x40
Instruction(opcode = 0xcb, mnemonic = "(RSTV)", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RESTART)
Instruction(opcode = 0xcc, mnemonic = "CZ", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xcd, mnemonic = "CALL", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xce, mnemonic = "ACI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xcf, mnemonic = "RST 1", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xd0, mnemonic = "RNC", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xd1, mnemonic = "POP D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xd2, mnemonic = "JNC", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xd3, mnemonic = "OUT", insType=InstrType.PORT, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xd4, mnemonic = "CNC", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xd5, mnemonic = "PUSH D", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xd6, mnemonic = "SUI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xd7, mnemonic = "RST 2", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xd8, mnemonic = "RC", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xd9, mnemonic = "(SHLX)", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xda, mnemonic = "JC", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xdb, mnemonic = "IN", insType=InstrType.PORT, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xdc, mnemonic = "CC", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xdd, mnemonic = "(JNK)", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xde, mnemonic = "SBI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xdf, mnemonic = "RST 3", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe0, mnemonic = "RPO", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xe1, mnemonic = "POP H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe2, mnemonic = "JPO", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xe3, mnemonic = "XTHL", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe4, mnemonic = "CPO", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xe5, mnemonic = "PUSH H", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe6, mnemonic = "ANI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xe7, mnemonic = "RST 4", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xe8, mnemonic = "RPE", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xe9, mnemonic = "PCHL", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xea, mnemonic = "JPE", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xeb, mnemonic = "XCHG", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xec, mnemonic = "CPE", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xed, mnemonic = "(LHLX)", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xee, mnemonic = "XRI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)
Instruction(opcode = 0xef, mnemonic = "RST 5", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xf0, mnemonic = "RP", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xf1, mnemonic = "POP PSW", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xf2, mnemonic = "JP", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xf3, mnemonic = "DI", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xf4, mnemonic = "CP", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xf5, mnemonic = "PUSH PSW", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xf6, mnemonic = "ORI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)

# jump to 0x0030
Instruction(opcode = 0xf7, mnemonic = "RST 6", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xf8, mnemonic = "RM", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE, branchType = BranchType.RETURN)
Instruction(opcode = 0xf9, mnemonic = "SPHL", insType=InstrType.MOVE, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xfa, mnemonic = "JM", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xfb, mnemonic = "EI", insType=InstrType.CONTROL, numOperands=0, operandType = OperandType.NONE)
Instruction(opcode = 0xfc, mnemonic = "CM", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.CALL)
Instruction(opcode = 0xfd, mnemonic = "(JK)", insType=InstrType.BRANCH, numOperands=2, operandType = OperandType.ADDRESS, branchType = BranchType.JUMP)
Instruction(opcode = 0xfe, mnemonic = "CPI", insType=InstrType.ARITHMETIC, numOperands=1, operandType = OperandType.IMMEDIATE)

# jump to 0x0038
Instruction(opcode = 0xff, mnemonic = "RST 7", insType=InstrType.BRANCH, numOperands=0, operandType = OperandType.NONE)
