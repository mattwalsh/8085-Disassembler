import sys
import yaml
from instructions import *
from collections import OrderedDict
from pathlib import Path
from utils import hexParse

from argparse import ArgumentParser, ArgumentTypeError

alli = Instruction.alli

parser = ArgumentParser()
parser.add_argument('-i', '--input', help='Input binary file', required=True, type=str)
parser.add_argument('-a', '--addresses', help='show addresses for each line', action="store_true", default=False)
parser.add_argument('-w', '--binaryops', help='Show opcodes w/ binary', action="store_true", default=False)
args = parser.parse_args()

program = OrderedDict()

sym_path = Path(f"{args.input}.yml")
if sym_path.is_file():
   with open(sym_path) as file: 
      yml = yaml.safe_load(file)

   if 'addresses' in yml:
      for i in yml['addresses']:
         addrInt = hexParse(yml['addresses'][i])
         Instruction.syms[addrInt] = i
         print(f"{i} EQU {hex(addrInt)}")

   if 'labels' in yml:
      for i in yml['labels']:
         addrInt = hexParse(yml['labels'][i])
         Instruction.labels[addrInt] = i

   if 'inPorts' in yml:
      print("\n; INPUT PORTS")
      for i in yml['inPorts']:
         portInt = hexParse(yml['inPorts'][i])
         Instruction.inPorts[portInt] = i
         print(f"{i} EQU {hex(portInt)}")

   if 'outPorts' in yml:
      print("\n; OUTPUT PORTS")
      for i in yml['outPorts']:
         portInt = hexParse(yml['outPorts'][i])
         Instruction.outPorts[portInt] = i
         print(f"{i} EQU {hex(portInt)}")

   if 'notes' in yml:
      for i in yml['notes']:
         addr = hexParse(i)
         Instruction.notes[addr] = yml['notes'][i]

   if 'not_code' in yml:
      for i in yml['not_code']:
         label = i
         start = hexParse(yml['not_code'][i][0])
         end = hexParse(yml['not_code'][i][1])
         Instruction.addDataRange((start, end))

PC = 0
Instruction.opcodeBinary = args.binaryops

with open(args.input, mode='rb') as file: # b is important -> binary
    while (byte := file.read(1)):

      instr = alli[int.from_bytes(byte)]
      nextPC = PC + 1

      if not Instruction.checkIfData(PC):
         operand1 = None
         operand2 = None

         if instr.numOperands >= 1:
            operand1 = int.from_bytes(file.read(1))
            nextPC = nextPC + 1
    
         if instr.numOperands == 2:
            operand2 = int.from_bytes(file.read(1))
            nextPC = nextPC + 1

         instance = instr.instantiate(operand1, operand2)
         program[Address(PC)] = instance
      else:
         instance = instr.instantiateDB()
         program[Address(PC)] = instance
      PC = nextPC

# pass to eliminate junk jumps / calls
for addr in program:
   line = program[addr]

# see $0445 why
#   if line.insType == InstrType.BRANCH:
#      if line.operandType == OperandType.ADDRESS:
#         if line.targetAddress not in program:
#            if not Instruction.checkIfData(addr.address):
#            #print(f"; BOGUS address {line.targetAddress} found in {line} at {addr}")
#               line.junk()

for addr in program:
   line = program[addr]
   line.address = addr

   # walk through all jumps and calls
   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         #  no label for it? make one, 
         label = Label.makeLabel(line.targetAddress)

         # find the instruction that is called
         if line.targetAddress in program:
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
   if args.addresses:
      l = program[pc]
      if l.label and l.label.isCall:
         print(" ")
      print(f"{pc} {l}")
   else:
      print(f"{program[pc]}")




