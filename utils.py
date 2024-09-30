import re

def hexParse(word):
   # tolerate hex format 0x12 or 0X34
   if re.match(r'^(0X|0x)[0-9a-fA-F]+$', word):
      return int(word, 16)
   # tolerate hex format #12
   elif re.match(r'^(#)[0-9a-fA-F]+$', word):
      word = re.sub(r'(#)', '', word)
      return int(f"0x{word}", 16)
   # tolerate hex format $12
   elif re.match(r'^(\$)[0-9a-fA-F]+$', word):
      word = re.sub(r'(\$)', '', word)
      return int(f"0x{word}", 16)
   # tolerate hex format 12h
   elif(re.match(r'^([0-9a-fA-F]+(H|h))$', word)):
      word = re.sub(r'(H|h)', '', word)
      return int(f"0x{word}", 16)

   return None
