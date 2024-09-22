import sys
from instructions import *
from collections import OrderedDict

from argparse import ArgumentParser, ArgumentTypeError

alli = Instruction.alli
#for i in alli:
#   print(alli[i].model_dump())

if len(sys.argv) < 2:
   print("missing filename")
   quit()

program = OrderedDict()

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
            #print(f"BOGUS address {line.targetAddress} found in {line} at {addr}")
            line.junk()

labels = {}
for addr in program:
   line = program[addr]

   # walk through all jumps and calls
   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         #  no label for it? make one, 
         if line.targetAddress not in labels:
            l = Label(address = line.targetAddress)
            labels[line.targetAddress] = l
         else:
            l = labels[line.targetAddress]

         # find the instruction that is called
         target = program[line.targetAddress]

         # label the line.  Really should be part of label creation but to be safe...
         target.label = l
         line.targetLabel = l

         target.callers.append(line)

for pc in program:
   #print(f"{pc} {program[pc]}")
   print(f"{program[pc]}")

