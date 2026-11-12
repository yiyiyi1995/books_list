# -*- coding: utf-8 -*-
"""Add four verified public-domain classics without replacing the owner's selections."""
import json,pathlib
from simplify_chinese import convert
ROOT=pathlib.Path(__file__).resolve().parents[1]
raw=json.loads((ROOT/'sources/alternatives-original.json').read_text())
rows=[('alt001','论语（简体原文）','孔子弟子及再传弟子 编','社会 · 思想 · 自我','以问答与语录讨论学习、交往、伦理和政治，适合按章短读。','思想与自我板块的公版拓展，不替代现代哲学或心理学书。先读“学而”，每次一两则，记录认同与疑问；古代语境须与今天区分。'),('alt002','诗经（简体原文）','佚名','诗词 · 唐诗宋词','古代诗歌总集，保留原文中的重复、节奏与日常生活场景。','唐宋诗词之外的源头拓展。可从《关雎》《蒹葭》开始朗读；古词难字较多，本版本不含现代译注。'),('alt003','大学（简体原文）','传统归于曾子及其传承，作者存在争议','社会 · 思想 · 自我','围绕修身、齐家与政治秩序展开的古代儒家文本。','适合作为自我与思想板块的短篇原典。先梳理概念关系，再思考哪些观点依赖古代社会条件；不是现代成长方法书。'),('alt004','孟子（简体原文）','孟子及其弟子 编','社会 · 思想 · 自我','以对话、论辩和故事讨论仁义、政治、教育与人格。','思想板块的公版拓展，可从“梁惠王上”读起。观察比喻与追问如何推进论证；不将古代政治主张直接当作现代结论。')]
public={}
for id,title,author,category,description,recommendation in rows:
 source=raw[id];data=source['data']
 for _ in range(3):data=convert(data)
 if isinstance(data,dict):data=[data]
 chapters=[]
 for i,c in enumerate(data):
  content=c.get('paragraphs',c.get('content',[]))
  if not content:continue
  heading=c.get('title') or c.get('chapter') or str(i+1)
  if c.get('section')and c.get('title'):heading=c['section']+' · '+c['title']
  chapters.append({'id':'part'+str(i),'title':heading,'author':'','text':'\n\n'.join(content)})
 assert chapters and all(c['text'].strip()for c in chapters)
 public[id]={'version':1,'language':'zh-Hans','label':title+' · 公版原典拓展','source':'https://github.com/chinese-poetry/chinese-poetry/blob/master/'+source['path'],'license':'MIT / public-domain original','chapters':chapters}
 print(title,len(chapters),'chapters')
folder=ROOT/'readings';files=[]
for id,b in public.items():
 meta={**b,'chapters':[]};groups=[];group=[];size=0
 for c in b['chapters']:
  n=len(json.dumps(c,ensure_ascii=False))
  if group and size+n>35000:groups.append(group);group=[];size=0
  group.append(c);size+=n
 if group:groups.append(group)
 for i,group in enumerate(groups):
  name=f'readings/{id}-{i}.js';s=('window.PUBLIC_READING['+json.dumps(id)+']='+json.dumps(meta,ensure_ascii=False,separators=(',',':'))+';\n'if i==0 else '')
  s+='window.PUBLIC_READING['+json.dumps(id)+'].chapters.push(...'+json.dumps(group,ensure_ascii=False,separators=(',',':'))+');\n';(ROOT/name).write_text(s);files.append(name)
p=ROOT/'index.html';html=p.read_text();import re
html=re.sub(r'<script src="readings/alt[^\"]+"></script>\s*','',html)
html=html.replace('<script src="poetry-guides.js', ''.join('<script src="'+f+'?v=4"></script>\n'for f in files)+'<script src="poetry-guides.js');p.write_text(html)
p=ROOT/'catalog.json';catalog=json.loads(p.read_text())
for id,title,author,category,description,recommendation in rows:
 if not any(b['id']==id for b in catalog['books']):catalog['books'].append(dict(id=id,title=title,author=author,category=category,description=description,recommendation=recommendation))
p.write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n');(ROOT/'catalog.js').write_text('window.INITIAL_CATALOG='+p.read_text()+';\n')
