"""Browser acceptance checks with isolated temporary storage. Requires Chrome."""
import base64,json,os,pathlib,secrets,socket,struct,subprocess,sys,tempfile,time,urllib.request
ROOT=pathlib.Path(__file__).resolve().parents[1]
N=len(json.loads((ROOT/'catalog.json').read_text())['books'])
CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def free_port():
 with socket.socket() as s:s.bind(('127.0.0.1',0));return s.getsockname()[1]
def wait_url(url):
 for _ in range(100):
  try:return http.open(url,timeout=1)
  except Exception:time.sleep(.1)
 raise RuntimeError('Service did not start: '+url)
class CDP:
 def __init__(self,url):
  from urllib.parse import urlparse
  p=urlparse(url);self.s=socket.create_connection((p.hostname,p.port));self.s.settimeout(15);self.counter=0
  key=base64.b64encode(secrets.token_bytes(16)).decode();self.s.sendall((f'GET {p.path} HTTP/1.1\r\nHost: {p.netloc}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
  h=b''
  while not h.endswith(b'\r\n\r\n'):h+=self.s.recv(1)
  assert b'101' in h,h
 def read(self,n):
  b=b''
  while len(b)<n:
   x=self.s.recv(n-len(b))
   if not x:raise RuntimeError('Websocket closed')
   b+=x
  return b
 def call(self,method,params=None):
  self.counter+=1;i=self.counter;msg=json.dumps({'id':i,'method':method,'params':params or {}}).encode();mask=secrets.token_bytes(4);n=len(msg)
  header=bytes([0x81,0x80|(n if n<126 else (126 if n<65536 else 127))])
  if n>=126:header+=struct.pack('!H' if n<65536 else '!Q',n)
  self.s.sendall(header+mask+bytes(b^mask[j%4] for j,b in enumerate(msg)))
  while True:
   a,b=self.read(2);n=b&127
   if n==126:n=struct.unpack('!H',self.read(2))[0]
   if n==127:n=struct.unpack('!Q',self.read(8))[0]
   m=self.read(4) if b&128 else None;raw=self.read(n)
   if m:raw=bytes(x^m[j%4] for j,x in enumerate(raw))
   if a&15!=1:continue
   value=json.loads(raw)
   if value.get('id')==i:
    if 'error' in value:raise RuntimeError(value['error'])
    return value.get('result',{})
 def evaluate(self,expr):
  r=self.call('Runtime.evaluate',{'expression':expr,'awaitPromise':True,'returnByValue':True})
  if 'exceptionDetails'in r:raise RuntimeError(r['exceptionDetails'])
  return r.get('result',{}).get('value')
 def wait(self,expr):
  for _ in range(100):
   if self.evaluate(expr):return
   time.sleep(.05)
  raise AssertionError(expr)
 def close(self):self.s.close()
with tempfile.TemporaryDirectory(prefix='books-qa-') as t:
 port,debug=free_port(),free_port();url=f'http://127.0.0.1:{port}'
 env={**os.environ,'BOOKS_DATA_DIR':t};env.pop('BOOKS_PASSWORD',None)
 server=subprocess.Popen([sys.executable,str(ROOT/'server.py'),'--port',str(port)],env=env,stdout=subprocess.DEVNULL)
 chrome=None;cdp=None
 try:
  wait_url(url)
  initial={'books':json.loads((ROOT/'catalog.json').read_text())['books'],'deleted':[],'notes':{},'texts':{},'positions':{},'statuses':{},'lastBook':None,'lastSync':'2099-01-01T00:00:00Z'}
  req=urllib.request.Request(url+'/api/state',data=json.dumps({'state':initial,'revision':0}).encode(),method='PUT',headers={'Content-Type':'application/json'});http.open(req).read()
  chrome=subprocess.Popen([CHROME,'--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--user-data-dir='+t+'/chrome','--remote-debugging-port='+str(debug),'about:blank'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  pages=json.load(wait_url(f'http://127.0.0.1:{debug}/json/list'));cdp=CDP(pages[0]['webSocketDebuggerUrl']);cdp.call('Page.enable');cdp.call('Page.navigate',{'url':url});cdp.wait("document.querySelectorAll('.card').length===68")
  assert cdp.evaluate("!document.querySelector('.quickread')&&document.querySelectorAll('.category-heading').length===8")
  assert cdp.evaluate("(()=>{const groups={};for(const card of document.querySelectorAll('.card')){const id=card.querySelector('[data-read]').dataset.read,b=state.books.find(b=>b.id===id);(groups[b.category]??=[]).push(hasText(id));}return Object.values(groups).every(g=>g.every((v,i)=>v||!g.slice(i+1).includes(true)));})()")
  cdp.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
  cdp.evaluate("window.scrollTo(0,0)")
  time.sleep(.15)
  pathlib.Path('/tmp/books-project-desktop.png').write_bytes(base64.b64decode(cdp.call('Page.captureScreenshot',{'format':'png'})['data']))
  cdp.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
  time.sleep(.15)
  assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth")
  pathlib.Path('/tmp/books-project-mobile.png').write_bytes(base64.b64decode(cdp.call('Page.captureScreenshot',{'format':'png'})['data']))
  cdp.call('Emulation.setDeviceMetricsOverride',{'width':1440,'height':1000,'deviceScaleFactor':1,'mobile':False})
  assert cdp.evaluate("!document.querySelector('#notesTab')&&!document.querySelector('#settingsTab')&&!document.querySelector('#importText')")
  assert cdp.evaluate("document.querySelectorAll('[data-delete]').length===68")
  assert cdp.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--green').trim()==='#0875d1'")
  cdp.evaluate("document.querySelector('[data-read=\"b001\"]').click()")
  cdp.wait("document.querySelector('#reader').open&&document.querySelector('#readerText p')&&state.positions.b001")
  assert cdp.evaluate("document.querySelector('#readerText').textContent.length>20")
  cdp.evaluate("document.querySelector('#chapterSelect').value='1';document.querySelector('#chapterSelect').dispatchEvent(new Event('change'))")
  cdp.wait("state.positions.b001.chapter===PUBLIC_READING.b001.chapters[1].id")
  pathlib.Path('/tmp/books-project-reader.png').write_bytes(base64.b64decode(cdp.call('Page.captureScreenshot',{'format':'png'})['data']))
  cdp.evaluate("document.querySelector('#chapterSelect').value='50';document.querySelector('#chapterSelect').dispatchEvent(new Event('change'))")
  cdp.wait("state.positions.b001.chapter===PUBLIC_READING.b001.chapters[50].id")
  cdp.evaluate("document.querySelector('#readerNote').click();document.querySelector('#noteText').value='浏览器验收：读后感自动保存';document.querySelector('#noteText').dispatchEvent(new Event('input'))")
  cdp.wait("document.querySelector('#noteHint').textContent.includes('已保存')")
  cdp.evaluate("document.querySelector('[data-close=detail]').click()")
  cdp.call('Page.reload');cdp.wait("document.querySelectorAll('.card').length===68")
  assert cdp.evaluate("state.notes.b001.text==='浏览器验收：读后感自动保存'")
  cdp.evaluate("document.querySelector('[data-read=\"b001\"]').click()")
  cdp.wait("document.querySelector('#reader').open&&document.querySelector('#chapterSelect').value==='50'")
  assert cdp.evaluate("state.positions.b001.chapter===PUBLIC_READING.b001.chapters[50].id")
  cdp.evaluate("window.qaLong=PUBLIC_READING.b001.chapters.reduce((best,c,i,all)=>c.text.length>all[best].text.length?i:best,0);document.querySelector('#chapterSelect').value=String(window.qaLong);document.querySelector('#chapterSelect').dispatchEvent(new Event('change'))")
  cdp.wait("state.positions.b001.chapter===PUBLIC_READING.b001.chapters[window.qaLong].id")
  cdp.evaluate("document.querySelector('#reader').scrollTop=(document.querySelector('#reader').scrollHeight-document.querySelector('#reader').clientHeight)*0.55")
  cdp.wait("state.positions.b001.percent>20")
  saved_para=cdp.evaluate("state.positions.b001.paragraph")
  cdp.evaluate("document.querySelector('#fontSize').value='25';document.querySelector('#fontSize').dispatchEvent(new Event('change'))")
  time.sleep(.3)
  assert cdp.evaluate("state.positions.b001.paragraph")==saved_para
  cdp.evaluate("document.querySelector('#readerBack').click()")
  cdp.wait("!document.querySelector('#reader').open")
  cdp.evaluate("window.confirm=()=>true;document.querySelector('[data-delete=\"b002\"]').click()")
  cdp.wait("document.querySelectorAll('.card').length===67")
  cdp.call('Page.reload');cdp.wait("document.querySelectorAll('.card').length===67")
  assert cdp.evaluate("state.deleted.includes('b002')&&!state.books.some(b=>b.id==='b002')")
  cdp.evaluate("document.querySelector('#englishShortcut').click()")
  cdp.wait("document.querySelectorAll('.card').length===6")
  assert cdp.evaluate("Object.keys(window.PUBLIC_READING).filter(k=>k.startsWith('en')).length===6")
  cdp.evaluate("document.querySelector('[data-read=\"en001\"]').click()")
  cdp.wait("document.querySelector('#reader').open&&!document.querySelector('#speechControls').hidden")
  assert cdp.evaluate("document.querySelector('#readerText p[lang=en]').textContent.startsWith('Once upon a time')")
  assert cdp.evaluate("!!document.querySelector('.study')&&!!document.querySelector('#speak')")
  # Test speech dispatch without requiring an OS voice or producing audible output.
  assert cdp.evaluate("(()=>{let calls=0;const old=window.speechSynthesis.speak;window.speechSynthesis.speak=()=>calls++;document.querySelector('#speak').click();window.speechSynthesis.speak=old;document.querySelector('#stopSpeech').click();return calls===1;})()")
  cdp.evaluate("document.querySelector('#readerBack').click()")
  cdp.wait("!document.querySelector('#reader').open")
  cdp.evaluate("category='';document.querySelector('#availabilityFilter').value='';render()")
  cdp.wait("document.querySelectorAll('.card').length===67")
  cdp.evaluate("document.querySelector('#availabilityFilter').value='direct';document.querySelector('#availabilityFilter').dispatchEvent(new Event('change'))")
  cdp.wait("document.querySelectorAll('.card').length===12")
  cdp.evaluate("document.querySelector('[data-read=\"alt001\"]').click()")
  cdp.wait("document.querySelector('#reader').open&&document.querySelector('#readerText').textContent.includes('学而时习之')")
  assert cdp.evaluate("document.querySelector('#chapterSelect').options.length===20")
  cdp.evaluate("document.querySelector('#readerBack').click()")
  cdp.wait("!document.querySelector('#reader').open")
  cdp.evaluate("category='';document.querySelector('#availabilityFilter').value='';render()")
  cdp.call('Emulation.setDeviceMetricsOverride',{'width':390,'height':844,'deviceScaleFactor':1,'mobile':True})
  time.sleep(.2)
  assert cdp.evaluate("document.documentElement.scrollWidth<=innerWidth"),cdp.evaluate("[document.documentElement.scrollWidth,innerWidth]")
  shot=cdp.call('Page.captureScreenshot',{'format':'png'})
  pathlib.Path('/tmp/books-bright-mobile.png').write_bytes(base64.b64decode(shot['data']))
  cdp.call('Emulation.setDeviceMetricsOverride',{'width':1366,'height':900,'deviceScaleFactor':1,'mobile':False})
  time.sleep(.2)
  shot=cdp.call('Page.captureScreenshot',{'format':'png'})
  pathlib.Path('/tmp/books-bright-desktop.png').write_bytes(base64.b64decode(shot['data']))
  print('PASS: 68 cards; six English full-text books and speech dispatch; no standalone notes/sync; blue theme; direct public reading; per-book chapter resume after reload; notes persisted; deletion persisted; 390px layout without horizontal overflow.')
 finally:
  if cdp:cdp.close()
  if chrome:chrome.terminate();chrome.wait(timeout=10)
  server.terminate();server.wait(timeout=10)
