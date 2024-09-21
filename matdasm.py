import sys
from instructions import *
from collections import OrderedDict

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

      program[PC] = instance
      PC = nextPC

# pass to eliminate junk jumps / calls
for addr in program:
   line = program[addr]

   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         if line.address not in program:
            print(f"BOGUS address {format(line.address, '04x')} found in {line.dump()} at {hex(addr)}")
            line.junk()

labels = {}
for addr in program:
   line = program[addr]

   if line.insType == InstrType.BRANCH:
      if line.operandType == OperandType.ADDRESS:
         target = program[line.address]
         if line.address not in labels:
            l = Label(address = line.address)
            labels[line.address] = l

         line.labelAddr = l
         target.label = l
         l.callers.append(line)      

for pc in program:
   print(f"{format(pc, '04x')} {program[pc].dump()}")

