import sys
import yaml
from instructions import *
from collections import OrderedDict
from pathlib import Path
from utils import hexParse

from argparse import ArgumentParser, ArgumentTypeError

alli = Instruction.alli
#for i in alli:
#   print(alli[i].model_dump())

if len(sys.argv) < 2:
   print("missing filename")
   quit()

program = OrderedDict()

sym_path = Path(f"{sys.argv[1]}.yml")
if sym_path.is_file():
   with open(sym_path) as file: 
      inp = yaml.safe_load(file)

   if inp['addresses']:
      for i in inp['addresses']:
         addrInt = hexParse(inp['addresses'][i])
         Instruction.syms[addrInt] = i
         print(f"{i} EQU {hex(addrInt)}")

   if inp['ports']:
      print("\n; PORTS")
      for i in inp['ports']:
         portInt = hexParse(inp['ports'][i])
         Instruction.ports[portInt] = i
         print(f"{i} EQU {hex(portInt)}")

PC = 0

with open(sys.argv[1], mode='rb') as file: # b is important -> binary
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
   #print(f"{pc} {program[pc]}")
   print(f"{program[pc]}")

