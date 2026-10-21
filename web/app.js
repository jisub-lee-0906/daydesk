'use strict';
const $=id=>document.getElementById(id),{safeUrl,monthlyTotals,normalizeState,daysUntil}=DeskLogic;
const STORAGE='my-pc-desk.v1', LOCATION_KEY='daydesk.location-enabled';
const AI=[['codex','Codex','✳','https://chatgpt.com/'],['claude','Claude','C','https://claude.ai/'],['grok','Grok','𝕏','https://grok.com/'],['gemini','Gemini','✧','https://gemini.google.com/']];
const el=(tag,cls,value)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(value!==undefined)n.textContent=value;return n;};
const text=(id,value)=>{if($(id))$(id).textContent=value;};
const number=(n,d=0)=>Number(n).toLocaleString('ko-KR',{maximumFractionDigits:d});
const gb=n=>number(n/1073741824,1);
const money=(n,c)=>new Intl.NumberFormat('ko-KR',{style:'currency',currency:c,maximumFractionDigits:c==='KRW'?0:2}).format(n);
const age=ts=>{if(!ts)return '시각 미확인';const n=Math.max(0,Date.now()/1000-ts);return n<60?'방금':n<3600?`${Math.floor(n/60)}분 전`:n<86400?`${Math.floor(n/3600)}시간 전`:`${Math.floor(n/86400)}일 전`;};
const dateLabel=ts=>ts?new Date(ts*1000).toLocaleString('ko-KR',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}):'미확인';
const uid=()=>crypto.randomUUID();
let storageReadable=true,state,savedRaw={},lastData,publicData,source='all',timer,controller,inFlight=false,lastPublic=0,aiSignature='',newsSignature='',tracker,owner=uid(),locationQueue=Promise.resolve();
function notice(message){text('notice',message);$('notice').hidden=!message;}
function save(){
 if(!storageReadable){notice('읽지 못한 기존 설정을 보호하기 위해 저장하지 않았어요.');return false;}
 try{savedRaw=DeskLogic.withSubscriptions(savedRaw,state.subscriptions);localStorage.setItem(STORAGE,JSON.stringify(savedRaw));return true;}
 catch{notice('설정을 저장하지 못했어요. 브라우저 저장 공간을 확인해 주세요.');return false;}
}
function value(id,n,unit){$(id).replaceChildren(document.createTextNode(n===null||n===undefined?'—':String(n)),el('small','',unit));}
function meter(id,n){const bar=$(id),unknown=n===null||n===undefined;bar.hidden=unknown;bar.parentElement.classList.toggle('unknown',unknown);bar.style.width=`${unknown?0:n}%`;}
function clock(){text('today',new Date().toLocaleDateString('ko-KR',{month:'long',day:'numeric',weekday:'long'}));}
function renderStatus(data){
 lastData=data;const p=data.pc||{},ram=p.memory,disk=p.disk,gpu=(data.gpus||[])[0],mem=gpu?.memory,c=data.comfy||{};
 const stale=!data.sampled_at||Date.now()/1000-data.sampled_at>40||data.sample_error;
 $('connection-dot').className=stale?'offline':'online';text('connection-text',stale?'수집 확인 필요':'내 PC 연결됨');
 value('cpu-value',p.cpu_percent,'%');value('ram-value',ram?gb(ram.used):null,'GB');value('disk-value',disk?gb(disk.free):null,'GB');
 $('ram-value').title=ram?`${gb(ram.total)} GB 중 ${ram.percent}% 사용`:'확인 불가';
 value('collector-value',p.collector_bytes?number(p.collector_bytes/1048576,1):null,'MiB');
 text('collector-caption',p.uptime_seconds===null||p.uptime_seconds===undefined?'가동 시간 미확인':`PC 켜진 지 ${Math.floor(p.uptime_seconds/3600)}시간`);
 value('gpu-value',mem?gb(mem.used):null,mem?`/ ${gb(mem.total)} GiB`:'GiB');meter('gpu-bar',mem?mem.used/mem.total*100:null);
 text('gpu-free',mem?gb(mem.free):'—');text('gpu-name',gpu?gpu.name.replace('NVIDIA GeForce ',''):'GPU 미확인');
 text('gpu-detail',gpu?`${gpu.temperature??'—'}°C · GPU ${gpu.utilization??'—'}%`:'NVML 확인 필요');
 $('comfy-dot').className=c.online?'online':'offline';text('comfy-status',c.online?c.running===null?'연결됨 · 큐 미확인':c.running?'작업 실행 중':'연결됨 · 대기 중':'연결 대기');
 text('comfy-running',c.running??'—');text('comfy-pending',c.pending??'—');$('comfy-link').href=`http://127.0.0.1:${Number(c.port)||8188}/`;
 text('comfy-caption',`GPU 전체 기준${mem&&mem.reserved!==null?' · 시스템 예약 '+gb(mem.reserved)+' GiB':''}`);
 const service=data.service||{};$('ocx-dot').className=service.online?'online':'offline';text('ocx-status',service.online?'연결됨':'연결 확인 필요');$('ocx-link').href=`http://127.0.0.1:${Number(service.port)||10100}/`;
 text('updated',`${stale?'이전 수집값 · ':''}PC ${dateLabel(data.sampled_at)}`);
 renderAI();if($('details').open)renderApps(data.apps);
}
function renderAI(){
 const quotas=lastData?.quotas||{};const sig=JSON.stringify([quotas,state.subscriptions,lastData?.apps?.find(a=>a.id==='codex')?.count]);if(sig===aiSignature)return;aiSignature=sig;
 const focused=document.activeElement?.dataset.ai;
 const container=$('ai-cards');container.replaceChildren();
 for(const [id,name,glyph,url] of AI){
  const q=quotas[id]||{windows:[]},s=state.subscriptions.find(s=>s.id===id&&s.tracking),card=el('article','ai-card '+id),heading=el('div','ai-heading'),identity=el('div','ai-identity'),usage=el('div','ai-usage'),windows=el('div','quota-windows'),link=el('a','ai-link');
  link.href=url;link.target='_blank';link.rel='noopener noreferrer';link.dataset.ai=id;link.append(el('span','app-icon '+id,glyph),el('h3','',name),el('span','link-arrow','↗'));
  heading.append(link);identity.append(heading);
  if(s?.plan&&s.plan!=='플랜 미입력'){const plan=el('p','ai-plan',s.plan);plan.title=s.source||'직접 입력';identity.append(plan);}
  const stale=q.stale||!q.updated_at||Date.now()/1000-q.updated_at>900;
  if(!q.windows.length)windows.append(el('p','quota-empty','사용량 미확인'));
  for(const w of q.windows){const row=el('div','quota-row'),desc=el('div','quota-label'),bar=el('div','quota-bar'),fill=el('span');desc.append(el('span','',w.label.startsWith(name+' ')?w.label.slice(name.length+1):w.label),el('strong','',`${w.used_percent>0&&w.used_percent<0.1?'<0.1':number(w.used_percent,1)}%`));fill.style.width=`${w.used_percent}%`;bar.append(fill);row.append(desc,bar);if(w.reset_at)row.title='초기화 '+dateLabel(w.reset_at);windows.append(row);}
  usage.append(windows,el('p','ai-foot '+(stale?'stale':''),`${stale?'이전 캐시 · ':''}${age(q.updated_at)}`));card.append(identity,usage);container.append(card);
 }
 if(focused)container.querySelector(`[data-ai="${focused}"]`)?.focus({preventScroll:true});
 renderSubscriptionSummary();
}
function renderApps(apps){
 const container=$('app-list');container.replaceChildren();
 if(!apps){container.append(el('p','empty','실행 상태 미확인'));return;}
 for(const a of apps){const row=el('div','running-app');row.append(el('strong','',a.name),el('span','',a.count?`${a.count}개 · ${a.memory_complete?number(a.memory_bytes/1048576)+' MiB':'메모리 미확인'}`:'미실행'));container.append(row);}
}
function renewalLabel(s){const d=daysUntil(s.renewal);return d===null?'':d<0?`갱신일 ${-d}일 지남`:d===0?'오늘 갱신':`${d}일 뒤 갱신`;}
function renderSubscriptionSummary(){
 const tracked=state.subscriptions.filter(s=>s.tracking),totals=monthlyTotals(tracked),parts=Object.entries(totals).map(([c,n])=>money(n,c));
 $('subscription-summary').hidden=!parts.length;text('monthly-total',parts.length?'월 환산 '+parts.join(' + '):'');
 const next=tracked.filter(s=>s.renewal).sort((a,b)=>a.renewal.localeCompare(b.renewal))[0];text('renewal-summary',next?`${next.name} · ${renewalLabel(next)}`:'');
 const container=$('subscription-list');container.replaceChildren();
 for(const s of tracked){const row=el('div','subscription-row'),left=el('div'),right=el('div','subscription-info');left.append(el('strong','',s.name));if(s.plan&&s.plan!=='플랜 미입력')left.append(el('p','muted',s.plan));right.append(el('span','',s.amount===null?'':money(s.amount,s.currency)+' / '+(s.cycle==='yearly'?'년':'월')),el('p','footnote',renewalLabel(s)));row.append(left,right);container.append(row);}
}
function weatherLabel(code){
 if(code===null||code===undefined)return ['◌','상태 미확인'];if(code===0)return ['☀','맑음'];if(code<=3)return ['◒',code===1?'대체로 맑음':'구름 많음'];if(code<=48)return ['≋','안개'];if(code>=71&&code<=77)return ['❄','눈'];if(code>=95)return ['ϟ','뇌우'];return ['☂','비·소나기'];
}
function renderPublic(data){
 publicData=data;const w=data.weather||{},d=w.data,description=weatherLabel(d?.code);
 text('weather-place',w.location||'용인');text('weather-symbol',description[0]);text('weather-temperature',d?.temperature===null||!d?'—':number(d.temperature,1)+'°');
 text('weather-description',d?description[1]:w.error?'연결 확인 필요':'날씨 조회 중');
 text('weather-range',d?[`최고 ${d.high??'—'}°`,`최저 ${d.low??'—'}°`,d.rain===null?'':`강수 ${d.rain}%`].filter(Boolean).join(' · '):'기상 데이터를 기다리는 중');
 text('weather-status',`날씨 ${w.stale&&d?'이전 자료 · ':''}${age(w.updated_at)} · Open-Meteo`);
 renderNews();
}
function renderNews(){
 if(!publicData)return;const all=publicData.news||[],items=all.filter(n=>source==='all'||n.source===source).slice(0,8),sources=publicData.sources||{};
 const signature=JSON.stringify([items,sources,source]);if(signature===newsSignature)return;newsSignature=signature;
 text('news-count',items.length+'개');const list=$('news-list');list.replaceChildren();
 if(!items.length)list.append(el('p','empty','표시할 소식이 아직 없어요.'));
 for(const n of items){
  const url=safeUrl(n.url);if(!url||url.protocol!=='https:')continue;
  const row=el('article','news-item'),a=el('a','news-link',n.title);a.href=url.href;a.target='_blank';a.rel='noopener noreferrer';
  const s=sources[n.source]||{},meta=el('div','news-meta');meta.append(el('span','source-tag '+n.source,s.name||n.source),el('span','',n.published_at?age(n.published_at):'게시일 미확인'));
  if(s.stale)meta.append(el('span','stale','이전 자료'));row.append(meta,a);list.append(row);
 }
 const entries=Object.values(sources),errors=entries.filter(s=>s.error).length,oldest=Math.min(...entries.map(s=>s.updated_at||0));
 text('news-status',`${errors?errors+'개 출처 연결 확인 · ':''}${oldest?'확인 '+age(oldest):'첫 수집 중'} · 원문 제목`);
}
function editorField(label,type,value,cls,options){
 const wrapper=el('label','',label),input=el(type==='select'?'select':'input',cls);
 if(type==='select')for(const [v,l]of options){const o=el('option','',l);o.value=v;input.append(o);}else input.type=type;
 input.value=value??'';wrapper.append(input);return wrapper;
}
function addSubscriptionEditor(s){
 const row=el('section','subscription-editor');row._original=s;
 const header=el('header'),name=el('input','sub-name'),tracked=el('label'),check=el('input','sub-tracking');name.value=s.name;name.required=true;name.maxLength=50;name.setAttribute('aria-label','구독 이름');check.type='checkbox';check.checked=s.tracking;tracked.append(check,document.createTextNode('표시'));
 const remove=el('button','remove','×');remove.type='button';remove.setAttribute('aria-label',s.name+' 구독 삭제');remove.addEventListener('click',()=>row.remove());header.append(name,tracked,remove);row.append(header);
 const fields=el('div','editor-fields');fields.append(editorField('플랜','text',s.plan,'sub-plan'),editorField('결제 금액','number',s.amount,'sub-amount'),editorField('통화','select',s.currency,'sub-currency',[['KRW','KRW'],['USD','USD'],['EUR','EUR']]),editorField('결제 주기','select',s.cycle,'sub-cycle',[['monthly','월간'],['yearly','연간']]),editorField('다음 갱신일','date',s.renewal,'sub-renewal'));
 fields.querySelector('.sub-plan').maxLength=80;const amount=fields.querySelector('.sub-amount');amount.min='0';amount.max='999999999';amount.step='0.01';row.append(fields,el('p','footnote',s.source||'직접 입력'));$('subscription-fields').append(row);
}
function rememberTracking(enabled){try{localStorage.setItem(LOCATION_KEY,enabled?'on':'off');}catch{}}
function postLocation(mode,position){
 const body=JSON.stringify({mode,owner,...(position||{})});
 locationQueue=locationQueue.catch(()=>{}).then(async()=>{const r=await fetch('/api/location',{method:'POST',headers:{'Content-Type':'application/json'},body,keepalive:true,signal:AbortSignal.timeout(4000)});if(!r.ok)throw Error(r.status===409?'another_tab':'connection');return r;});
 return locationQueue;
}
function setTracking(){
 tracker=new DeskLocation.LocationTracker(navigator.geolocation,p=>{
  postLocation('current',p).then(()=>{if(tracker.enabled&&!document.hidden){text('location-status','현재 위치를 사용 중이에요.');lastPublic=0;}}).catch(e=>text('location-status',e.message==='another_tab'?'다른 탭에서 현재 위치를 사용 중이에요.':'위치 전송 연결을 확인해 주세요.'));
 },reason=>{
  if(reason!=='paused')rememberTracking(false);
  text('location-status',reason==='paused'?'화면을 숨겨 위치 추적을 쉬고 있어요.':reason==='disabled'?'용인 기준으로 표시합니다.':reason==='permission-denied'?'위치 권한이 거부되어 용인으로 표시합니다.':reason==='timeout'?'위치 응답 시간이 지나 용인으로 표시합니다.':'이 브라우저에서 위치를 확인하지 못해 용인으로 표시합니다.');
  postLocation('default').catch(()=>{});lastPublic=0;
 });
 try{owner=sessionStorage.getItem('daydesk.owner')||owner;sessionStorage.setItem('daydesk.owner',owner);}catch{}
 let enabled=false;try{enabled=localStorage.getItem(LOCATION_KEY)==='on';}catch{}
 if(enabled&&!document.hidden)tracker.start();
}
function events(){
 for(const b of document.querySelectorAll('[data-close]'))b.addEventListener('click',()=>$(b.dataset.close).close());
 $('open-details').addEventListener('click',()=>{$('details').open=!$('details').open;if($('details').open){$('details').scrollIntoView({block:'nearest'});$('details').querySelector('summary').focus({preventScroll:true});if(lastData)renderApps(lastData.apps);}});
 $('details').addEventListener('toggle',()=>{$('open-details').setAttribute('aria-expanded',String($('details').open));if($('details').open&&lastData)renderApps(lastData.apps);});
 $('location-settings').addEventListener('click',()=>$('location-dialog').showModal());
 $('use-location').addEventListener('click',()=>{rememberTracking(true);text('location-status','브라우저 위치 권한을 확인하고 있어요.');tracker.start();});
 $('use-yongin').addEventListener('click',()=>tracker.disable());
 for(const b of document.querySelectorAll('[data-source]'))b.addEventListener('click',()=>{source=b.dataset.source;for(const other of document.querySelectorAll('[data-source]')){other.classList.toggle('active',other===b);other.setAttribute('aria-pressed',String(other===b));}newsSignature='';renderNews();});
 $('edit-subscriptions').addEventListener('click',()=>{$('subscription-fields').replaceChildren();state.subscriptions.forEach(addSubscriptionEditor);$('subscription-dialog').showModal();});
 $('add-subscription').addEventListener('click',()=>{if($('subscription-fields').children.length<30)addSubscriptionEditor({id:uid(),name:'새 구독',plan:'',amount:null,currency:'KRW',cycle:'monthly',renewal:'',tracking:true,source:'직접 입력',verified_at:null});});
 $('subscription-form').addEventListener('submit',e=>{e.preventDefault();state.subscriptions=[...$('subscription-fields').children].map(row=>{const get=c=>row.querySelector('.sub-'+c),old=row._original,name=get('name').value.trim(),plan=get('plan').value.trim(),edited=name!==old.name||plan!==old.plan;return {...old,name,plan,tracking:get('tracking').checked,amount:get('amount').value===''?null:Number(get('amount').value),currency:get('currency').value,cycle:get('cycle').value,renewal:get('renewal').value,source:edited?'직접 입력 · '+new Date().toLocaleDateString('ko-KR'):old.source,verified_at:edited?null:old.verified_at};});save();aiSignature='';renderAI();$('subscription-dialog').close();});
 document.addEventListener('visibilitychange',()=>{clearTimeout(timer);if(document.hidden){controller?.abort();tracker.pause();}else{tracker.resume();lastPublic=0;if(!inFlight)poll();}});
 window.addEventListener('pagehide',()=>tracker.pause());
}
async function poll(){
 if(document.hidden||inFlight)return;inFlight=true;controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),4000);
 try{
  const r=await fetch('/api/status',{signal:controller.signal,cache:'no-store'});if(!r.ok)throw Error();renderStatus(await r.json());
  if(Date.now()-lastPublic>30000){
   const p=await fetch('/api/public',{signal:controller.signal,cache:'no-store'});if(p.ok){renderPublic(await p.json());lastPublic=Date.now();}
   if(tracker.enabled&&tracker.position)postLocation('current',tracker.position).catch(()=>{});
  }
 }catch{if(!document.hidden){$('connection-dot').className='offline';text('connection-text','수집기 연결 끊김');text('updated','이전 수집값 표시 중');}}
 finally{clearTimeout(timeout);inFlight=false;clock();if(!document.hidden)timer=setTimeout(poll,3000);}
}
async function init(){
 clock();
 try{
  const r=await fetch('/api/info');if(!r.ok)throw Error();const info=await r.json();
  try{const raw=JSON.parse(localStorage.getItem(STORAGE)||'{}');savedRaw=raw&&typeof raw==='object'&&!Array.isArray(raw)?raw:{};}catch{storageReadable=false;notice('저장 설정을 읽지 못했어요. 기존 값을 덮어쓰지 않도록 백업 후 확인해 주세요.');}
  state=normalizeState(savedRaw,info.subscriptions);setTracking();events();renderSubscriptionSummary();poll();
 }catch{notice('수집기 연결 상태를 확인하고 새로고침해 주세요.');}
}
init();
