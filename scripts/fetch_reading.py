"""Fetch explicitly identified public-domain/CC0 originals. No code from archives is executed."""
import hashlib,io,json,pathlib,re,tarfile,urllib.request,xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATA=ROOT/'sources';DATA.mkdir(exist_ok=True)
MANIFEST=[]
def download(url):
 req=urllib.request.Request(url,headers={'User-Agent':'Books-Room/1.0 (+personal public-domain library)'})
 with urllib.request.urlopen(req,timeout=60) as r:return r.read()
def get_se(key,repo,title):
 url='https://codeload.github.com/standardebooks/'+repo+'/tar.gz/refs/heads/master'
 cache=pathlib.Path('/tmp/books-source-'+key+'.tar.gz')
 raw=cache.read_bytes() if cache.exists() else download(url)
 cache.write_bytes(raw)
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
  members={m.name.split('/',1)[1]:m for m in tar.getmembers() if '/' in m.name and m.isfile()}
  opf=ET.fromstring(tar.extractfile(members['src/epub/content.opf']).read());ns={'o':'http://www.idpf.org/2007/opf'}
  items={i.attrib['id']:i.attrib['href'] for i in opf.findall('o:manifest/o:item',ns)};chapters=[]
  for item in opf.findall('o:spine/o:itemref',ns):
   href=items[item.attrib['idref']];name=pathlib.PurePosixPath(href).stem
   if name in ['titlepage','imprint','halftitlepage','colophon','uncopyright','dedication','endnotes','loi','introduction']:continue
   path='src/epub/'+href
   if path not in members:continue
   tree=ET.fromstring(tar.extractfile(members[path]).read());x={'x':'http://www.w3.org/1999/xhtml'}
   body=tree.find('x:body',x)
   if body is None:continue
   paras=[''.join(p.itertext()).strip() for p in body.iter() if p.tag.split('}')[-1] in ['p','blockquote'] and p.tag.split('}')[-1]=='p']
   if not paras:continue
   heads=[' '.join(''.join(h.itertext()).split()) for h in body.iter() if h.tag.split('}')[-1] in ['h2','h3']]
   if key=='en003' and name!='preface':
    sections=[n for n in body.iter() if n.tag.split('}')[-1] in ['section','article'] and not any(child.tag.split('}')[-1] in ['section','article'] for child in n)]
    for sec in sections:
     ph=[''.join(p.itertext()).strip() for p in sec.iter() if p.tag.split('}')[-1]=='p']
     sh=[' '.join(''.join(h.itertext()).split()) for h in sec.iter() if h.tag.split('}')[-1] in ['h2','h3']]
     if ph:chapters.append({'id':sec.attrib.get('id','fable-'+str(len(chapters))),'title':sh[0] if sh else 'Fable '+str(len(chapters)+1),'author':'','text':'\n\n'.join(ph)})
   else:chapters.append({'id':name,'title':heads[0] if heads else name.replace('-',' ').title(),'author':'','text':'\n\n'.join(paras)})
  notice=tar.extractfile(members['src/epub/text/uncopyright.xhtml']).read().decode() if 'src/epub/text/uncopyright.xhtml'in members else 'Standard Ebooks contributions: CC0 1.0 Universal.'
  (DATA/(key+'-license.xhtml')).write_text(notice)
 MANIFEST.append({'id':key,'source':'https://github.com/standardebooks/'+repo,'archive':url,'sha256':hashlib.sha256(raw).hexdigest(),'license':'CC0 1.0 / public-domain original','chapters':len(chapters)})
 return {'version':1,'language':'en','label':title+' · 英文原版','source':'https://github.com/standardebooks/'+repo,'license':'CC0 1.0','chapters':chapters}
def get_pg(key,number,title):
 url=f'https://www.gutenberg.org/cache/epub/{number}/pg{number}.txt';raw=(DATA/(key+'-source.txt')).read_bytes() if (DATA/(key+'-source.txt')).exists() else download(url);text=raw.decode('utf-8-sig')
 (DATA/(key+'-source.txt')).write_text(text)
 body=re.split(r'\*\*\* START OF (?:THE|THIS) PROJECT GUTENBERG EBOOK .*?\*\*\*',text,maxsplit=1,flags=re.I)[-1]
 body=re.split(r'\*\*\* END OF (?:THE|THIS) PROJECT GUTENBERG EBOOK',body,maxsplit=1,flags=re.I)[0].strip()
 body=re.sub(r'\[(?:Picture|Illustration)[^\]]*\]','',body,flags=re.I)
 if number==14838:
  m=re.search(r'Once upon a time',body,re.I)
  if not m:raise ValueError('Peter Rabbit opening not found')
  body=body[m.start():];chapters=[{'id':'story','title':title,'author':'','text':body}]
 else:
  titles=['THE HAPPY PRINCE','THE NIGHTINGALE AND THE ROSE','THE SELFISH GIANT','THE DEVOTED FRIEND','THE REMARKABLE ROCKET'];chapters=[]
  # Match the final occurrence of each story heading to exclude the table of contents.
  points=[]
  for h in titles:
   matches=list(re.finditer(r'(?im)^\s*'+re.escape(h)+r'\.?\s*$',body))
   if not matches:raise ValueError('Heading not found: '+h)
   points.append((matches[-1].start(),matches[-1].end(),h))
  points.sort()
  for i,(start,end,h)in enumerate(points):chapters.append({'id':'story'+str(i),'title':h.title(),'author':'','text':body[end:points[i+1][0] if i+1<len(points) else len(body)].strip()})
 MANIFEST.append({'id':key,'source':f'https://www.gutenberg.org/ebooks/{number}','text_url':url,'sha256':hashlib.sha256(raw).hexdigest(),'license':'Project Gutenberg license retained in sources/'+key+'-source.txt','chapters':len(chapters)})
 return {'version':1,'language':'en','label':title+' · 英文原版','source':f'https://www.gutenberg.org/ebooks/{number}','license':'Project Gutenberg / public-domain original','chapters':chapters}
if __name__=='__main__':
 data={}
 for key,repo,title in [('en003','aesop_fables_v-s-vernon-jones',"Aesop’s Fables"),('en004','lewis-carroll_alices-adventures-in-wonderland_john-tenniel',"Alice’s Adventures in Wonderland"),('en005','l-frank-baum_the-wonderful-wizard-of-oz','The Wonderful Wizard of Oz'),('en006','frances-hodgson-burnett_the-secret-garden','The Secret Garden')]:
  data[key]=get_se(key,repo,title);print(key,len(data[key]['chapters']),flush=True)
 for args in [('en001',14838,'The Tale of Peter Rabbit'),('en002',902,'The Happy Prince and Other Tales')]:
  data[args[0]]=get_pg(*args);print(args[0],len(data[args[0]]['chapters']),flush=True)
 (ROOT/'english.js').write_text('Object.assign(window.PUBLIC_READING,'+json.dumps(data,ensure_ascii=False,separators=(',',':'))+');\n')
 (DATA/'manifest.json').write_text(json.dumps(MANIFEST,ensure_ascii=False,indent=2))
