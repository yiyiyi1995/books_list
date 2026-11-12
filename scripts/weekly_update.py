"""Append one curated candidate per week. Never modify/remove existing books."""
import json,os,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
p=root/'catalog.json';data=json.loads(p.read_text());candidates=json.loads((root/'candidates.json').read_text())['books']
existing=data['books'];before=json.dumps(existing,ensure_ascii=False,sort_keys=True)
known={(b['title'],b['author']) for b in existing};ids={b['id'] for b in existing};cats={b['category'] for b in existing}
for b in candidates:
 if b['id'] in ids or (b['title'],b['author']) in known:continue
 if b['category'] not in cats:raise ValueError('Candidate category must already exist')
 if not all(isinstance(b.get(k),str) and b[k] for k in ['id','title','author','category','description','recommendation']):raise ValueError('Invalid candidate')
 existing.append(b);print('Added:',b['title']);break
else:print('No unused candidates; existing catalog preserved.')
assert json.dumps(existing[:len(json.loads(before))],ensure_ascii=False,sort_keys=True)==before
p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
(root/'catalog.js').write_text('window.INITIAL_CATALOG='+p.read_text()+';\n')
