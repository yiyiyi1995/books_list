#!/usr/bin/env python3
"""Local personal library. Python 3 standard library only."""
import argparse,base64,getpass,hashlib,hmac,http.cookies,json,os,secrets,sqlite3,time,urllib.request
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs,urlparse
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('BOOKS_DATA_DIR',str(ROOT/'data')))
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'books.sqlite3'
with sqlite3.connect(DB) as conn:
 conn.execute('CREATE TABLE IF NOT EXISTS library (id INTEGER PRIMARY KEY CHECK(id=1), revision INTEGER NOT NULL, state TEXT)')
 conn.execute('INSERT OR IGNORE INTO library VALUES (1,0,NULL)')
secret=secrets.token_bytes(32)
password=''

def valid_state(s):
 return isinstance(s,dict) and isinstance(s.get('books'),list) and all(isinstance(b,dict) and all(isinstance(b.get(k),str) and b[k] for k in ['id','title','author','category','description']) for b in s['books']) and isinstance(s.get('deleted'),list) and all(isinstance(s.get(k),dict) for k in ['notes','texts','positions','statuses']) and all(isinstance(n,dict) and isinstance(n.get('text'),str) and isinstance(n.get('updated'),str) for n in s['notes'].values()) and all(isinstance(t,str) for t in s['texts'].values())

class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kw):super().__init__(*args,directory=str(ROOT),**kw)
 def log_message(self,fmt,*args):pass
 def reply(self,code,data,ctype='application/json; charset=utf-8',extra=None):
  body=json.dumps(data,ensure_ascii=False).encode() if ctype.startswith('application/json') else data.encode()
  self.send_response(code);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin')
  for k,v in (extra or {}).items():self.send_header(k,v)
  self.end_headers();self.wfile.write(body)
 def authorized(self):
  if not password:return True
  try:
   cookies=http.cookies.SimpleCookie(self.headers.get('Cookie',''));value=cookies['books_session'].value;stamp,signature=value.split('.');age=time.time()-int(stamp)
   return 0<=age<30*86400 and hmac.compare_digest(signature,hmac.new(secret,stamp.encode(),hashlib.sha256).hexdigest())
  except Exception:return False
 def origin_ok(self):
  origin=self.headers.get('Origin')
  return self.headers.get('Sec-Fetch-Site') not in ('cross-site',) and (not origin or urlparse(origin).netloc==self.headers.get('Host'))
 def do_GET(self):
  path=urlparse(self.path).path
  if not self.authorized():
   if path.startswith('/api/'):return self.reply(401,{'error':'login required'})
   return self.reply(200,'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>登录书间</title><form method="post" action="/login" style="max-width:360px;margin:15vh auto;font:18px sans-serif"><h1>书间</h1><p>请输入启动服务时设置的访问密码。</p><input name="password" type="password" required autocomplete="current-password"><button>进入书房</button></form>','text/html; charset=utf-8')
  if path=='/api/state':
   with sqlite3.connect(DB) as c:rev,s=c.execute('SELECT revision,state FROM library WHERE id=1').fetchone()
   return self.reply(200,{'revision':rev,'state':json.loads(s) if s else None})
  if path=='/api/catalog':
   try:
    req=urllib.request.Request('https://raw.githubusercontent.com/yiyiyi1995/books_list/HEAD/catalog.json',headers={'User-Agent':'Books-Room/1'})
    with urllib.request.urlopen(req,timeout=15) as r:catalog=json.load(r)
    return self.reply(200,catalog)
   except Exception:return self.reply(502,{'error':'remote catalog unavailable'})
  if path not in ['/', '/index.html','/app.js','/style.css','/catalog.js','/catalog.json']:return self.reply(404,{'error':'not found'})
  return super().do_GET()
 def do_HEAD(self):self.reply(405,{'error':'not supported'})
 def body(self,limit=40*1024*1024):
  size=int(self.headers.get('Content-Length','0'))
  if not 0<size<=limit:raise ValueError('invalid size')
  return self.rfile.read(size)
 def do_POST(self):
  if not self.origin_ok():return self.reply(403,{'error':'origin rejected'})
  if self.path!='/login':return self.reply(404,{'error':'not found'})
  try:provided=parse_qs(self.body(4096).decode()).get('password',[''])[0]
  except Exception:return self.reply(400,{'error':'invalid request'})
  if not hmac.compare_digest(provided.encode(),password.encode()):return self.reply(403,'密码不正确，请返回重试。','text/plain; charset=utf-8')
  stamp=str(int(time.time()));sig=hmac.new(secret,stamp.encode(),hashlib.sha256).hexdigest()
  self.send_response(303);self.send_header('Location','/');self.send_header('Set-Cookie',f'books_session={stamp}.{sig}; Path=/; HttpOnly; SameSite=Strict; Max-Age=2592000');self.end_headers()
 def do_PUT(self):
  if not self.authorized() or not self.origin_ok():return self.reply(403,{'error':'not authorized'})
  if self.path!='/api/state':return self.reply(404,{'error':'not found'})
  try:
   data=json.loads(self.body());s=data['state'];rev=data['revision']
   if not valid_state(s) or not isinstance(rev,int):raise ValueError('invalid state')
   with sqlite3.connect(DB) as c:
    result=c.execute('UPDATE library SET revision=revision+1,state=? WHERE id=1 AND revision=?',(json.dumps(s,ensure_ascii=False),rev))
    if result.rowcount==0:return self.reply(409,{'error':'another device updated the library'})
   return self.reply(200,{'revision':rev+1})
  except (ValueError,KeyError,TypeError):return self.reply(400,{'error':'invalid state'})

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--host',default='127.0.0.1');parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
 password=os.environ.get('BOOKS_PASSWORD','')
 if args.host not in ['127.0.0.1','localhost','::1'] and not password:
  password=getpass.getpass('设置手机访问密码（至少 8 位，不会存入文件）：')
  if len(password)<8:raise SystemExit('密码至少 8 位')
 print(f'书间已启动：http://{args.host}:{args.port}，Ctrl+C 停止。数据保存在 {DB}',flush=True)
 ThreadingHTTPServer((args.host,args.port),Handler).serve_forever()
