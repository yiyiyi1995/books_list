'use strict';
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const PUBLIC = window.PUBLIC_READING || {};
let state = {books:[],deleted:[],notes:{},texts:{},positions:{},statuses:{},externalBookmarks:{},lastBook:null,lastSync:null};
let revision = 0, server = false, category = '', current = null, readingId = null, chapterIndex = 0;
let saveQueue = Promise.resolve(), restoring = false, scrollTimer, noteTimer;
const categories = [...new Set(INITIAL_CATALOG.books.map(b => b.category))];
const colors = ['#83cbff','#a5ddff','#9bcbff','#8dd6ff','#b0dcff','#9ed7ff','#a6d0ff','#7bcdff'];

function toast(t) {
  $('#toast').textContent=t; $('#toast').style.display='block';
  clearTimeout(toast.timer); toast.timer=setTimeout(()=>$('#toast').style.display='none',4500);
}
function validBook(b) {
  return b && ['id','title','author','category','description'].every(k=>typeof b[k]==='string'&&b[k].length>0) && (!b.recommendation||typeof b.recommendation==='string');
}
function mergeCatalog(list) {
  let n=0;
  for(const b of list) if(validBook(b) && !state.deleted.includes(b.id) && !state.books.some(x=>x.id===b.id||(x.title===b.title&&x.author===b.author))) {state.books.push({...b}); n++;}
  return n;
}
async function persist() {
  const snapshot=JSON.parse(JSON.stringify(state));
  saveQueue=saveQueue.catch(()=>{}).then(async()=>{
    if(server) {
      const r=await fetch('/api/state',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({state:snapshot,revision})});
      if(!r.ok) throw new Error(r.status===409?'另一设备已更新数据。请先从页脚导出备份，再刷新后合并修改。':'保存失败，请从页脚导出备份');
      revision=(await r.json()).revision;
    } else await localWrite(snapshot);
  });
  try {await saveQueue; return true;} catch(e) {toast(e.message); return false;}
}
function localDB() {
  return new Promise((res,rej)=>{
    const r=indexedDB.open('books-room',1);
    r.onupgradeneeded=()=>r.result.createObjectStore('state');
    r.onsuccess=()=>res(r.result); r.onerror=()=>rej(new Error('无法访问浏览器存储，请使用本地服务'));
  });
}
async function localRead() {
  const db=await localDB();
  return new Promise((res,rej)=>{const t=db.transaction('state'),r=t.objectStore('state').get('main'); r.onsuccess=()=>{res(r.result);db.close();};r.onerror=()=>{db.close();rej(r.error);};});
}
async function localWrite(s) {
  const db=await localDB();
  return new Promise((res,rej)=>{const t=db.transaction('state','readwrite');t.objectStore('state').put(s,'main');t.oncomplete=()=>{db.close();res();};t.onerror=()=>{db.close();rej(new Error('保存失败，存储空间可能不足，请从页脚导出备份'));};});
}
function hasText(id) {return !!(state.texts[id] || PUBLIC[id]);}
function bookChapters(id) {
  if(state.texts[id]) return [{id:'personal',title:'已保存正文',author:'',text:state.texts[id]}];
  return PUBLIC[id]?.chapters || [];
}
function sourceKey(id) {return state.texts[id]?'personal':'public-v1';}
function progressLabel(id) {
  const p=state.positions[id];
  if(!p) return '';
  const c=bookChapters(id).find(c=>c.id===p.chapter);
  return c ? `上次读到：${c.title}${p.percent!==undefined?' · 本篇 '+p.percent+'%':''}` : '已保存上次阅读位置';
}
function statusLabel(id) {return ({unread:'○ 未开始',reading:'◐ 阅读中',done:'● 已读完'})[state.statuses[id]||'unread'];}
function render() {
  $('#count').textContent=state.books.length;
  const readableCount=state.books.filter(b=>hasText(b.id)).length;
  $('#readableSummary').textContent=readableCount+' 本可立即阅读 · 已置顶';
  $('#topRead').textContent='立即查看这 '+readableCount+' 本 →';
  $('#filters').innerHTML=['全部',...categories].map(c=>`<button data-cat="${esc(c==='全部'?'':c)}" class="${category===(c==='全部'?'':c)?'active':''}">${esc(c)}</button>`).join('');
  const q=$('#search').value.trim().toLowerCase(),status=$('#statusFilter').value,availability=$('#availabilityFilter').value;
  const books=state.books.filter(b=>(!category||b.category===category)&&(!availability||(availability==='direct'?hasText(b.id):!hasText(b.id)))&&(!status||(state.statuses[b.id]||'unread')===status)&&[b.title,b.author,b.description].join(' ').toLowerCase().includes(q)).sort((a,b)=>Number(hasText(b.id))-Number(hasText(a.id)));
  $('#resultCount').textContent=`共 ${books.length} 本 · ${category||'全部板块'}`;
  $('#grid').innerHTML=books.map(b=>`<article class="card"><div class="cardtop"><div class="cover" aria-hidden="true" style="--cover:${colors[Math.max(0,categories.indexOf(b.category))%colors.length]}">${esc(b.title)}</div><div><span class="tag">${esc(b.category)}</span><h3>${esc(b.title)}</h3><div class="author">${esc(b.author)}</div><span class="readbadge">${hasText(b.id)?'站内原文阅读':'尚未接入全文'}</span></div></div><p class="desc">${esc(b.description)}</p><div class="rec">推荐读法 · ${esc(b.recommendation||'从你感兴趣的章节开始。')}</div>${state.positions[b.id]?`<p class="progressline">${esc(progressLabel(b.id))}</p>`:''}<div class="cardfoot"><span>${statusLabel(b.id)}${state.notes[b.id]?.text?' · 已有读后感':''}</span><div class="cardbuttons"><button data-book="${esc(b.id)}">详情 / 读后感</button><button class="primary" data-read="${esc(b.id)}">${hasText(b.id)?(state.positions[b.id]?'继续阅读':'直接阅读'):'查找正版 ↗'}</button><button class="danger" data-delete="${esc(b.id)}" aria-label="删除《${esc(b.title)}》">删除</button></div></div></article>`).join('')||'<div class="empty">这里还没有符合条件的书。</div>';
  const last=state.books.find(b=>b.id===state.lastBook);
  $('#resume').textContent=last?'继续阅读《'+last.title+'》 ↗':'开始一段阅读 ↗';
}
function platformUrl(b) {
  const title=b.title.replace(/（[^）]*）/g,'').replace(/\([^)]*\)/g,'').trim();
  return 'https://weread.qq.com/web/search/books?keyword='+encodeURIComponent(title);
}
async function openExternal(id) {
  const b=state.books.find(b=>b.id===id); if(!b) return;
  // A normal top-level navigation lets the platform handle its own sign-in and reading progress.
  window.open(platformUrl(b),'_blank','noopener,noreferrer');
  state.lastBook=id; if(!state.statuses[id]||state.statuses[id]==='unread')state.statuses[id]='reading';
  await persist();render();
}
async function removeBook(id) {
  const b=state.books.find(b=>b.id===id); if(!b)return;
  if(!confirm('删除《'+b.title+'》？读后感和阅读位置会保留；每周更新不会把它重新加回。'))return;
  state.books=state.books.filter(b=>b.id!==id);
  if(!state.deleted.includes(id))state.deleted.push(id);
  if($('#detail').open&&current?.id===id)$('#detail').close();
  if(await persist()){render();toast('已删除《'+b.title+'》');}
}
function detail(id,focusNote=false) {
  current=state.books.find(b=>b.id===id); if(!current)return;
  const b=current,n=state.notes[id],available=hasText(id),bookmark=state.externalBookmarks[id]||'';
  clearTimeout(noteTimer);
  $('#detailBody').innerHTML=`<span class="tag">${esc(b.category)}</span><h2>${esc(b.title)}</h2><p>${esc(b.author)}</p><h3>关于这本书</h3><p>${esc(b.description)}</p><h3>推荐读法</h3><p>${esc(b.recommendation||'按自己的节奏阅读。')}</p><div class="sourcebox"><strong>${available?'可以直接阅读':'前往正版平台查找'}</strong><p class="sourcehint">${state.texts[id]?'你之前保存的正文仍可继续阅读。':PUBLIC[id]?(PUBLIC[id].language==='en'?'已内置英文原版全文，可直接阅读，并使用浏览器英语合成语音分段听读。语言难度是编辑建议，不是官方分级。':'已内置简体古典原文，无需导入。'+esc(PUBLIC[id].label)+'。'+(window.POETRY_GUIDES?.[id]?'逐篇提供关键词释义和导读，其中部分篇目有原创释义赏析；辅助导读不等同于逐句白话译文。':'本版提供公版原典正文，不含现代译文。')+'原文库不包含出版社现代注释。'):'本书尚无站内授权全文。点击下方按钮在微信读书按书名查找；是否上架及可读范围由平台决定，可能需要登录或购买。外部阅读进度由该平台保存，本应用无法读取。'}</p><div class="actions"><button id="read" class="primary">${available?(state.positions[id]?'继续上次位置':'直接阅读原文'):'去微信读书查找 ↗'}</button><button id="deleteBook" class="danger">删除此书</button></div>${available?`<p class="progressline">${esc(progressLabel(id)||'开始阅读后会自动记住章节与段落位置。')}</p>`:`<label class="sourcehint">我的阅读书签（可选）<input id="externalBookmark" placeholder="例如：第三章，第 42 页" value="${esc(bookmark)}" maxlength="300"></label>`}</div><label>阅读状态 <select id="bookStatus">${[['unread','未开始'],['reading','阅读中'],['done','已读完']].map(([v,t])=>`<option value="${v}" ${(state.statuses[id]||'unread')===v?'selected':''}>${t}</option>`).join('')}</select></label><h3 id="noteHeading">这本书的读后感</h3><textarea id="noteText" placeholder="记下触动你的句子、想法，以及它与你的联系…">${esc(n?.text||'')}</textarea><div class="actions"><button id="saveNote" class="primary">保存读后感</button><span id="noteHint" class="author">${n?'上次保存：'+new Date(n.updated).toLocaleString():'写在这里，会自动保存'}</span></div>`;
  $('#bookStatus').onchange=async e=>{state.statuses[id]=e.target.value;await persist();render();};
  const captureNote=()=>{state.notes[id]={text:$('#noteText').value,updated:new Date().toISOString()};};
  const saved=async()=>{if(await persist()){if(current?.id===id&&$('#noteHint'))$('#noteHint').textContent='已保存 · '+new Date().toLocaleTimeString();render();}};
  $('#noteText').oninput=()=>{captureNote();$('#noteHint').textContent='正在保存…';clearTimeout(noteTimer);noteTimer=setTimeout(saved,350);};
  $('#noteText').onblur=()=>{clearTimeout(noteTimer);saved();};
  $('#saveNote').onclick=()=>{captureNote();clearTimeout(noteTimer);saved();};
  if($('#externalBookmark'))$('#externalBookmark').oninput=e=>{state.externalBookmarks[id]=e.target.value;clearTimeout(noteTimer);noteTimer=setTimeout(persist,350);};
  $('#read').onclick=()=>available?openReader(id):openExternal(id);
  $('#deleteBook').onclick=()=>removeBook(id);
  if(!$('#detail').open)$('#detail').showModal();
  if(focusNote){$('#noteText').focus();$('#noteHeading').scrollIntoView({block:'start'});}
}
$('#detail').addEventListener('close',()=>{clearTimeout(noteTimer);persist();render();});

function readerPosition() {
  if(!readingId)return null;
  const r=$('#reader'),top=readingTop();
  const paragraphs=[...$('#readerText').querySelectorAll('[data-para]')];
  const p=paragraphs.find(p=>p.getBoundingClientRect().bottom>top)||paragraphs[paragraphs.length-1];
  const rect=p?.getBoundingClientRect();
  return {source:sourceKey(readingId),chapter:bookChapters(readingId)[chapterIndex]?.id,paragraph:Number(p?.dataset.para||0),fraction:rect?Math.max(0,Math.min(1,(top-rect.top)/Math.max(1,rect.height))):0,offset:r.scrollTop,percent:Math.round(r.scrollTop/Math.max(1,r.scrollHeight-r.clientHeight)*100),updated:new Date().toISOString()};
}
function capturePosition() {if(readingId&&!restoring&&$('#reader').open)state.positions[readingId]=readerPosition();}
function restorePosition(p) {
  const r=$('#reader');restoring=true;
  requestAnimationFrame(()=>{
    const para=p&&$('#readerText').querySelector(`[data-para="${Number(p.paragraph)||0}"]`);
    if(para&&p.chapter){const top=readingTop(),rect=para.getBoundingClientRect();r.scrollTop+=rect.top-top+(p.fraction||0)*rect.height;}
    else r.scrollTop=p?.offset||0;
    requestAnimationFrame(()=>{restoring=false;updateProgress();capturePosition();persist();render();});
  });
}
function paintChapter(index,p=null) {
  stopReadingSpeech();
  const chapters=bookChapters(readingId);chapterIndex=Math.max(0,Math.min(index,chapters.length-1));
  const c=chapters[chapterIndex],body=$('#readerText');body.replaceChildren();
  const heading=document.createElement('h2');heading.textContent=c.title;body.append(heading);
  if(c.author){const author=document.createElement('p');author.className='chapter-author';author.textContent=c.author;body.append(author);}
  const english=PUBLIC[readingId]?.language==='en';
  $('#speechControls').hidden=!english;
  const paragraphs=chunkParagraphs(c.text,english);
  paragraphs.forEach((t,i)=>{const el=document.createElement('p');el.dataset.para=i;el.textContent=t;if(english){el.lang='en';el.title='点击从这一段开始朗读';el.onclick=()=>startReadingSpeech(i);}body.append(el);});
  const study=makeStudyPanel(readingId,c,paragraphs.length);if(study)body.append(study);
  const source=document.createElement('div');source.id='readerSource';
  if(PUBLIC[readingId]&&!state.texts[readingId]) {const book=PUBLIC[readingId];source.innerHTML=`${esc(book.label)}<br>文本来源：<a class="textlink" href="${esc(book.source)}" target="_blank" rel="noopener noreferrer">${book.language==='en'?(book.source.includes('github.com')?'GitHub · Standard Ebooks':'Project Gutenberg'):'chinese-poetry'}</a> · ${esc(book.license)}。<br>第 ${chapterIndex+1} / ${chapters.length} 篇${book.language==='en'?' · 英语原版，合成语音并非真人录音':' · 简体原典，不含出版社现代译注'}`;}
  else source.textContent='之前保存的私人正文';
  body.append(source);
  const controls=document.createElement('div');controls.className='actions';
  for(const [delta,label]of [[-1,'← 上一篇'],[1,'下一篇 →']]){const b=document.createElement('button');b.textContent=label;b.disabled=chapterIndex+delta<0||chapterIndex+delta>=chapters.length;b.onclick=()=>changeChapter(chapterIndex+delta);controls.append(b);}body.append(controls);
  $('#chapterSelect').value=String(chapterIndex);restorePosition(p);
}
function changeChapter(index) {capturePosition();paintChapter(index);requestAnimationFrame(()=>requestAnimationFrame(()=>{capturePosition();persist();render();}));}
function openReader(id) {
  const b=state.books.find(x=>x.id===id);if(!b)return;
  if(!hasText(id))return openExternal(id);
  if($('#detail').open)$('#detail').close();
  current=b;readingId=id;state.lastBook=id;
  if(!state.statuses[id]||state.statuses[id]==='unread')state.statuses[id]='reading';
  $('#readerTitle').textContent=b.title;
  const chapters=bookChapters(id);
  $('#chapterSelect').innerHTML=chapters.map((c,i)=>`<option value="${i}">${i+1}. ${esc(c.title)}${c.author?' · '+esc(c.author):''}</option>`).join('');
  const p=state.positions[id],compatible=p&&(!p.source||p.source===sourceKey(id));
  const index=compatible?Math.max(0,chapters.findIndex(c=>c.id===p.chapter)):0;
  restoring=true;if(!$('#reader').open)$('#reader').showModal();paintChapter(index,compatible?p:null);
  persist();render();
}
function updateProgress() {const p=readerPosition();$('#progress').textContent=`${chapterIndex+1}/${bookChapters(readingId).length}篇 · 本篇 ${p?.percent||0}%`;}
$('#reader').onscroll=()=>{if(restoring||!readingId)return;updateProgress();capturePosition();clearTimeout(scrollTimer);scrollTimer=setTimeout(persist,300);};
$('#chapterSelect').onchange=e=>changeChapter(Number(e.target.value));
$('#fontSize').onchange=e=>{const p=readerPosition();$('#readerText').style.fontSize=e.target.value+'px';restorePosition(p);};
$('#readerBack').onclick=async()=>{capturePosition();clearTimeout(scrollTimer);await persist();$('#reader').close();render();};
$('#reader').addEventListener('cancel',capturePosition);
$('#reader').addEventListener('close',()=>{clearTimeout(scrollTimer);persist();render();});
$('#readerNote').onclick=()=>{const id=readingId;capturePosition();persist();$('#reader').close();detail(id,true);};
window.addEventListener('resize',()=>{if($('#reader').open)restorePosition(state.positions[readingId]);});
document.addEventListener('visibilitychange',()=>{if(document.hidden){capturePosition();persist();}});

async function sync() {
  try {
    const url=server?'/api/catalog':'https://raw.githubusercontent.com/yiyiyi1995/books_list/HEAD/catalog.json';
    const r=await fetch(url,{cache:'no-store'});if(!r.ok)return;
    const data=await r.json();if(!Array.isArray(data.books)||!data.books.every(validBook))return;
    const n=mergeCatalog(data.books);state.lastSync=new Date().toISOString();
    if(await persist()){render();if(n)toast('书架新增 '+n+' 本书');}
  }catch{ /* Keep the shelf available when a remote update is unavailable. */ }
}
$('#publicShortcut').onclick=$('#topRead').onclick=()=>{category='';$('#search').value='';$('#statusFilter').value='';$('#availabilityFilter').value='direct';render();$('#shelf').scrollIntoView({behavior:'smooth'});};
$('#search').oninput=render;$('#statusFilter').onchange=render;$('#availabilityFilter').onchange=render;
$('#englishShortcut').onclick=()=>{category='英语 · 口语听力阅读';$('#search').value='';$('#statusFilter').value='';$('#availabilityFilter').value='direct';render();$('#shelf').scrollIntoView({behavior:'smooth'});};
$('#filters').onclick=e=>{if(e.target.dataset.cat!==undefined){category=e.target.dataset.cat;render();}};
document.addEventListener('click',e=>{
  const del=e.target.closest('[data-delete]');if(del)return removeBook(del.dataset.delete);
  const read=e.target.closest('[data-read]');if(read)return openReader(read.dataset.read);
  const b=e.target.closest('[data-book]');if(b)return detail(b.dataset.book);
  const c=e.target.closest('[data-close]');if(c)$('#'+c.dataset.close).close();
});
$('#categorySelect').innerHTML=categories.map(c=>`<option>${esc(c)}</option>`).join('');
$('#add').onclick=()=>$('#addDialog').showModal();
$('#addForm').onsubmit=async e=>{
  e.preventDefault();const b=Object.fromEntries(new FormData(e.target));for(const k in b)b[k]=b[k].trim();
  b.id='custom-'+(crypto.randomUUID?crypto.randomUUID():Date.now());if(!validBook(b))return toast('请填写书名、作者和简介');
  state.books.push(b);if(await persist()){e.target.reset();$('#addDialog').close();category='';$('#search').value='';$('#statusFilter').value='';$('#availabilityFilter').value='';render();toast('已加入书架');}
};
$('#resume').onclick=()=>{const b=state.books.find(x=>x.id===state.lastBook)||state.books.find(x=>hasText(x.id))||state.books[0];if(b)openReader(b.id);else toast('请先添加一本书');};
$('#export').onclick=()=>{
  const blob=new Blob([JSON.stringify({format:'books-room-backup',version:1,exported:new Date().toISOString(),state},null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='书间备份-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
};
$('#restore').onchange=async e=>{
  try{
    const f=e.target.files[0];if(!f)return;const data=JSON.parse(await f.text()),s=data.state;
    if(data.format!=='books-room-backup'||data.version!==1||!s||!Array.isArray(s.books)||!s.books.every(validBook)||!Array.isArray(s.deleted)||!['notes','texts','positions','statuses'].every(k=>s[k]&&typeof s[k]==='object'&&!Array.isArray(s[k]))||!Object.values(s.notes).every(n=>n&&typeof n.text==='string'&&typeof n.updated==='string')||!Object.values(s.texts).every(t=>typeof t==='string'))throw Error('备份格式无效');
    if(!confirm('用备份替换当前数据？建议先导出当前数据。'))return;
    state={...s,externalBookmarks:s.externalBookmarks||{}};
    if(await persist()){render();toast('备份已恢复');}
  }catch(err){toast('恢复失败：'+err.message);}finally{e.target.value='';}
};
async function init() {
  try{
    let saved;
    if(location.protocol!=='file:')try{const r=await fetch('/api/state');if(r.ok&&r.headers.get('content-type')?.includes('application/json')){const d=await r.json();server=true;revision=d.revision;saved=d.state;}}catch{}
    if(!server)saved=await localRead();if(saved)state={...state,...saved};
    mergeCatalog(INITIAL_CATALOG.books);await persist();render();
    if(!state.lastSync||Date.now()-Date.parse(state.lastSync)>7*86400000)sync();
  }catch(e){toast(e.message);render();}
}
init();

function chunkParagraphs(text,english) {
  const out=[];
  for(let paragraph of text.split(/\n\s*\n/)) {
    if(english)paragraph=paragraph.replace(/\s+/g,' ').trim();
    while(paragraph.length>400) {
      let end=400;
      if(english){const candidate=paragraph.lastIndexOf(' ',400);if(candidate>200)end=candidate;}
      out.push(paragraph.slice(0,end));paragraph=paragraph.slice(end);
    }
    if(paragraph)out.push(paragraph);
  }
  return out;
}
function readingTop() {
  const top=$('.readerhead').getBoundingClientRect().bottom,controls=$('#speechControls');
  return !controls.hidden&&getComputedStyle(controls).position==='sticky'?Math.max(top,controls.getBoundingClientRect().bottom):top;
}
function makeStudyPanel(id,chapter,index) {
  const english=PUBLIC[id]?.language==='en',guide=window.POETRY_GUIDES?.[id]?.[chapter.id];
  if(!english&&!guide)return null;
  const section=document.createElement('section');section.className='study';section.dataset.para=index;
  if(english) {
    section.innerHTML=`<h3>听 · 读 · 说：把这一章变成口语练习</h3><p>先用 0.7× 或 0.85× 听一小段，试着抓住人物、动作和结果；再对照原文跟读。可以点击任意正文段落，从那里听起。</p><h4>口语复述</h4><p>What happened in this chapter? What did the character want? What would you do differently?</p><h4>练习方法</h4><p>选出 3 个你想复用的词组，逐个换一个情境造句。然后合上原文，用 First… / Then… / In the end… 作 30–60 秒复述。</p><p class="guide-notice">这里使用设备 / 浏览器的英语合成语音，不是真人有声书，也不提供发音评分。古典原著可能包含旧词、方言和双关；现代口语练习优先选清楚自然的对话，不必照搬全部句式。</p>`;
  } else {
    section.innerHTML=`<h3>${esc(guide.heading)}</h3>${guide.notice?`<p class="guide-notice">${esc(guide.notice)}</p>`:''}<h4>${guide.kind==='editorial'?'这首诗词的含义':'含义与理解线索'}</h4><p>${esc(guide.meaning)}</p><h4>关键词与古今词义</h4><dl>${guide.glosses.map(g=>`<dt>${esc(g.word)}</dt><dd>${esc(g.meaning)}</dd>`).join('')}</dl><h4>${guide.kind==='editorial'?'表达与赏析':'赏析读法'}</h4><p>${esc(guide.appreciation)}</p><h4>怎样理解和运用</h4><p>${esc(guide.usage)}</p><p class="guide-notice">书间原创学习辅助内容，不是金性尧等注家的注释；不同解读应回到原文检验。</p>`;
  }
  return section;
}
let speechRun=0,speakingParagraph=0,speechActive=false;
function stopReadingSpeech() {
  speechRun++;speechActive=false;
  if('speechSynthesis'in window)window.speechSynthesis.cancel();
  document.querySelectorAll('.speaking').forEach(p=>p.classList.remove('speaking'));
  if($('#speechHint'))$('#speechHint').textContent='浏览器合成语音 · 可点击正文段落从此处听起';
}
function startReadingSpeech(start=0) {
  if(!('speechSynthesis'in window)||typeof SpeechSynthesisUtterance==='undefined'){toast('当前浏览器不支持朗读，请使用支持语音合成的浏览器');return;}
  if(!$('#reader').open||PUBLIC[readingId]?.language!=='en')return;
  stopReadingSpeech();const run=speechRun,paragraphs=[...$('#readerText').querySelectorAll('p[data-para]')];
  let index=Math.max(0,start);speechActive=true;
  function next() {
    if(run!==speechRun||!$('#reader').open)return;
    if(index>=paragraphs.length){speechActive=false;$('#speechHint').textContent='本章朗读结束，试着用自己的话复述。';return;}
    const p=paragraphs[index];speakingParagraph=index;
    document.querySelectorAll('.speaking').forEach(x=>x.classList.remove('speaking'));p.classList.add('speaking');
    $('#reader').scrollTop+=p.getBoundingClientRect().top-readingTop()-12;capturePosition();persist();
    const u=new SpeechSynthesisUtterance(p.textContent);u.lang='en-US';u.rate=Number($('#speechRate').value);
    const voices=window.speechSynthesis.getVoices();const voice=voices.find(v=>/^en[-_]US/i.test(v.lang))||voices.find(v=>/^en/i.test(v.lang));if(voice)u.voice=voice;
    $('#speechHint').textContent='合成朗读 · 第 '+(index+1)+' / '+paragraphs.length+' 段';
    u.onend=()=>{if(run===speechRun){p.classList.remove('speaking');index++;next();}};
    u.onerror=e=>{if(run===speechRun&&!['canceled','interrupted'].includes(e.error)){speechActive=false;p.classList.remove('speaking');$('#speechHint').textContent='朗读未能启动：请检查设备英语语音或更换浏览器。';}};
    window.speechSynthesis.speak(u);
  }
  next();
}
$('#speak').onclick=()=>startReadingSpeech();
$('#pauseSpeech').onclick=()=>{if(!('speechSynthesis'in window))return;if(!speechActive)return toast('请先开始朗读');if(window.speechSynthesis.paused){window.speechSynthesis.resume();$('#speechHint').textContent='已继续朗读';}else{window.speechSynthesis.pause();$('#speechHint').textContent='已暂停，点击可继续';}};
$('#stopSpeech').onclick=stopReadingSpeech;
$('#speechRate').onchange=()=>{if(speechActive)startReadingSpeech(speakingParagraph);};
$('#reader').addEventListener('close',stopReadingSpeech);
