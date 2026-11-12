"""Longest-match traditional-to-simplified conversion using OpenCC data (Apache-2.0)."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
END='\0';TRIE={}
for filename in ['opencc-TSCharacters.txt','opencc-TSPhrases.txt']:
 for line in (ROOT/'sources'/filename).read_text().splitlines():
  if not line.strip() or line.startswith('#') or '\t' not in line:continue
  source,target=line.split('\t',1);node=TRIE
  for char in source:node=node.setdefault(char,{})
  node[END]=target.split()[0]
def simplify(text):
 result=[];start=0
 while start<len(text):
  node=TRIE;end=start;match=None
  while end<len(text) and text[end] in node:
   node=node[text[end]];end+=1
   if END in node:match=(end,node[END])
  if match:start,value=match;result.append(value)
  else:result.append(text[start]);start+=1
 return ''.join(result)
def convert(value):
 if isinstance(value,str):return simplify(value)
 if isinstance(value,list):return [convert(x) for x in value]
 if isinstance(value,dict):return {k:convert(v) for k,v in value.items()}
 return value
if __name__=='__main__':
 data=json.loads((ROOT/'sources/poetry-original.json').read_text())
 for _ in range(3):data=convert(data)
 for b in data.values():b['language']='zh-Hans';b['edition']='原文已统一简体；保留原篇目 ID 以延续阅读位置。'
 (ROOT/'reading.js').write_text('window.PUBLIC_READING='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n')
 assert simplify('憶故鄉，嶽陽樓，乾坤，乾燥')=='忆故乡，岳阳楼，乾坤，干燥'
 print('Converted',sum(len(b['chapters']) for b in data.values()),'chapters')
