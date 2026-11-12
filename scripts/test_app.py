import copy,http.cookiejar,json,os,pathlib,shutil,socket,subprocess,sys,tempfile,time,unittest,urllib.request,urllib.error
ROOT=pathlib.Path(__file__).resolve().parents[1]
class AppTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.tmp=tempfile.TemporaryDirectory();s=socket.socket();s.bind(('127.0.0.1',0));cls.port=s.getsockname()[1];s.close()
  cls.url='http://127.0.0.1:'+str(cls.port)
  cls.proc=subprocess.Popen([sys.executable,str(ROOT/'server.py'),'--port',str(cls.port)],env={**os.environ,'BOOKS_DATA_DIR':cls.tmp.name,'BOOKS_PASSWORD':'test-password'},stdout=subprocess.DEVNULL)
  cls.client=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
  for _ in range(50):
   try:urllib.request.urlopen(cls.url);break
   except Exception:time.sleep(.1)
 @classmethod
 def tearDownClass(cls):cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
 def test_full_roundtrip(self):
  with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(self.url+'/api/state')
  self.assertEqual(e.exception.code,401)
  self.client.open(urllib.request.Request(self.url+'/login',data=b'password=test-password')).read()
  d=json.load(self.client.open(self.url+'/api/state'));self.assertIsNone(d['state'])
  state={'books':json.loads((ROOT/'catalog.json').read_text())['books'],'deleted':[],'notes':{'b001':{'text':'我的读后感','updated':'2026-11-12T00:00:00Z'}},'texts':{'b001':'正文\n第二段'},'positions':{'b001':{'offset':520}},'statuses':{'b001':'reading'},'lastBook':'b001','lastSync':None}
  def put(rev,origin=None):
   req=urllib.request.Request(self.url+'/api/state',data=json.dumps({'state':state,'revision':rev}).encode(),method='PUT',headers={'Content-Type':'application/json',**({'Origin':origin} if origin else {})});return self.client.open(req)
  self.assertEqual(json.load(put(0))['revision'],1)
  saved=json.load(self.client.open(self.url+'/api/state'));self.assertEqual(saved['state'],state)
  with self.assertRaises(urllib.error.HTTPError) as e:put(0)
  self.assertEqual(e.exception.code,409)
  with self.assertRaises(urllib.error.HTTPError) as e:put(1,'https://untrusted.example')
  self.assertEqual(e.exception.code,403)
  for path in ['/data/books.sqlite3','/server.py','/../server.py']:
   with self.assertRaises(urllib.error.HTTPError):self.client.open(self.url+path)
  self.assertIn('书间',self.client.open(self.url).read().decode())
  import sqlite3
  with sqlite3.connect(pathlib.Path(self.tmp.name)/'books.sqlite3') as c:self.assertEqual(json.loads(c.execute('select state from library').fetchone()[0]),state)
 def test_weekly_append_only(self):
  with tempfile.TemporaryDirectory() as t:
   p=pathlib.Path(t);(p/'scripts').mkdir()
   for name in ['catalog.json','catalog.js','candidates.json','scripts/weekly_update.py']:shutil.copy(ROOT/name,p/name)
   original=json.loads((p/'catalog.json').read_text())['books']
   for _ in range(15):
    subprocess.run([sys.executable,str(p/'scripts/weekly_update.py')],check=True,stdout=subprocess.DEVNULL)
    books=json.loads((p/'catalog.json').read_text())['books'];self.assertEqual(books[:len(original)],original);self.assertEqual(len(books),len({b['id'] for b in books}));self.assertEqual(len(books),len({(b['title'],b['author']) for b in books}))
   self.assertEqual(len(books),len(original)+12)
if __name__=='__main__':unittest.main()
