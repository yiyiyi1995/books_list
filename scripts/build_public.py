"""Build the public, browser-local edition from an explicit asset allowlist."""
import json,pathlib,re,shutil,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'dist'
if OUT.exists():shutil.rmtree(OUT)
OUT.mkdir()
files=['index.html','style.css','app.js','catalog.js','catalog.json','reading.js','poetry-guides.js','THIRD_PARTY_LICENSES.txt','READING_SOURCES.md']
files.extend(str(p.relative_to(ROOT))for p in (ROOT/'readings').glob('*.js'))
files.extend(['sources/en001-source.txt','sources/en002-source.txt','sources/OpenCC-LICENSE.txt','sources/manifest.json'])
files.extend(str(p.relative_to(ROOT))for p in (ROOT/'sources').glob('en*-license.xhtml'))
for name in files:
 source=ROOT/name
 assert source.is_file() and not source.is_symlink(),name
 dest=OUT/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,dest)
html=(OUT/'index.html').read_text().replace('<script src="catalog.js','<script>window.BOOKS_STATIC=true;</script><script src="catalog.js',1)
(OUT/'index.html').write_text(html)
for name in re.findall(r'(?:src|href)="([^"#]+)"',html):
 if name.startswith(('https://','http://')):continue
 assert (OUT/name.split('?')[0]).is_file(),name
assert not (OUT/'data').exists() and not list(OUT.rglob('*.sqlite3')) and not (OUT/'server.py').exists()
(OUT/'.nojekyll').write_text('')
sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
(OUT/'deployment.json').write_text(json.dumps({'source_commit':sha,'storage':'visitor-browser','public':True}))
print('Public build:',len(files),'allowlisted assets; private database excluded.')
