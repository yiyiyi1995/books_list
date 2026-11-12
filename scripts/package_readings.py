"""Split large language assets into bounded buildless script files."""
import json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
folder=ROOT/'readings';folder.mkdir(exist_ok=True)
text=(ROOT/'english.js').read_text();english=json.loads(text[len('Object.assign(window.PUBLIC_READING,'):-3].strip())
files=[]
for key,b in english.items():
 meta={k:v for k,v in b.items() if k!='chapters'};meta['chapters']=[];chunks=[];group=[];size=0
 for c in b['chapters']:
  length=len(json.dumps(c,ensure_ascii=False))
  if group and size+length>45000:chunks.append(group);group=[];size=0
  group.append(c);size+=length
 if group:chunks.append(group)
 for n,group in enumerate(chunks):
  name=f'readings/{key}-{n}.js';content=('window.PUBLIC_READING['+json.dumps(key)+']='+json.dumps(meta,ensure_ascii=False,separators=(',',':'))+';\n'if n==0 else '')
  content+='window.PUBLIC_READING['+json.dumps(key)+'].chapters.push(...'+json.dumps(group,ensure_ascii=False,separators=(',',':'))+');\n';(ROOT/name).write_text(content);files.append(name)
# A single large source asset is not needed at runtime.
(ROOT/'english.js').unlink()
p=ROOT/'index.html';html=p.read_text();import re
html=re.sub(r'<script src="readings/[^"]+"></script>\s*','',html)
html=re.sub(r'<script src="poetry-guides.js[^"]*"></script>','',html)
html=html.replace('reading.js?v=3','reading.js?v=2');html=html.replace('<script src="reading.js?v=2"></script>','<script src="reading.js?v=3"></script>\n'+''.join('<script src="'+f+'?v=3"></script>\n'for f in files)+'<script src="poetry-guides.js?v=3"></script>');html=html.replace('app.js?v=2','app.js?v=3').replace('style.css?v=2','style.css?v=3');p.write_text(html)
print('Packaged',len(files),'English reading assets')
