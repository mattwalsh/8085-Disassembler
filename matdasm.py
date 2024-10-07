import sys
import yaml
from instructions import *
from collections import OrderedDict
from pathlib import Path
from utils import hexParse

from argparse import ArgumentParser, ArgumentTypeError

alli = Instruction.alli

parser = ArgumentParser()
parser.add_argument('-i','--input', help='Input binary file', required=True, type=str)
parser.add_argument('-a', help='show addresses for each lineInput binary file', action="store_true", default=False)
args = parser.parse_args()

program = OrderedDict()

sym_path = Path(f"{args.input}.yml")
if sym_path.is_file():
   with open(sym_path) as file: 
      inp = yaml.safe_load(file)

   if 'addresses' in inp:
      for i in inp['addresses']:
         addrInt = hexParse(inp['addresses'][i])
         Instruction.syms[addrInt] = i
         print(f"{i} EQU {hex(addrInt)}")

   if 'inPorts' in inp:
      print("\n; INPUT PORTS")
      for i in inp['inPorts']:
         portInt = hexParse(inp['inPorts'][i])
         Instruction.inPorts[portInt] = i
         print(f"{i} EQU {hex(portInt)}")

   if 'outPorts' in inp:
      print("\n; OUTPUT PORTS")
      for i in inp['outPorts']:
         portInt = hexParse(inp['outPorts'][i])
         Instruction.outPorts[portInt] = i
         print(f"{i} EQU {hex(portInt)}")

   if 'notes' in inp:
#      print("\n; OUTPUT PORTS")
      for i in inp['notes']:
         addr = hexParse(i) #inp['outPorts'][i])
         Instruction.notes[addr] = inp['notes'][i]

PC = 0

with open(args.input, mode='rb') as file: # b is important -> binary
    while (byte := file.read(1)):
      instr = alli[int.from_bytes(byte)]

      operand1 = None
      operand2 = None
      nextPC = PC + 1

      if instr.numOperands >= 1:
         operand1 = int.from_bytes(file.read(1))
         nextPC = nextPC + 1
 
      if instr.numOperands == 2:
         operand2 = int.from_bytes(file.read(1))
         nextPC = nextPC + 1

      instance = instr.instantiate(operand1, operand2)

      program[Address(PC)] = instance
      PC = nextPC

# pass to eliminate junk jumps / calls
for addr in program:
   line = program[addr]

   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         if line.targetAddress not in program:
            print(f"; BOGUS address {line.targetAddress} found in {line} at {addr}")
            line.junk()

for addr in program:
   line = program[addr]
   line.address = addr

   # walk through all jumps and calls
   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         #  no label for it? make one, 
         label = Label.makeLabel(line.targetAddress)

         # find the instruction that is called
         target = program[line.targetAddress]

         # label the target
         target.label = label
         line.targetLabel = label

         # label the line
         line.label = Label.makeLabel(line.address)
         line.label.setOrigin()
         label.addCaller(line)

for pc in program:
   if pc.address in Instruction.notes:
      print(f"; {Instruction.notes[pc.address]}")
   if args.a:
      print(f"{pc} {program[pc]}")
   else:
      print(f"{program[pc]}")




