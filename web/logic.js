(function(root) {
  'use strict';
  function safeUrl(value) {
    try {
      const url=new URL(value);
      if (url.username || url.password || !(url.protocol==='https:' || (url.protocol==='http:' && ['127.0.0.1','localhost','[::1]'].includes(url.hostname)))) return null;
      return url;
    } catch { return null; }
  }
  function monthlyTotals(subscriptions) {
    const totals={};
    for (const s of subscriptions) {
      if (!s.tracking || typeof s.amount!=='number' || !Number.isFinite(s.amount) || s.amount<0 || !['KRW','USD','EUR'].includes(s.currency)) continue;
      totals[s.currency]=(totals[s.currency]||0)+s.amount/(s.cycle==='yearly'?12:1);
    }
    return totals;
  }
  function daysUntil(date, now=new Date()) {
    if (typeof date!=='string' || !/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
    const [y,m,d]=date.split('-').map(Number);
    const target=new Date(y,m-1,d);
    if (target.getFullYear()!==y || target.getMonth()!==m-1 || target.getDate()!==d) return null;
    return Math.round((Date.UTC(y,m-1,d)-Date.UTC(now.getFullYear(),now.getMonth(),now.getDate()))/86400000);
  }
  function normalizeState(raw, seeds=[]) {
    raw=raw && typeof raw==='object' ? raw : {};
    const text=(v,n)=>typeof v==='string'?v.slice(0,n):'';
    return {
      focus:text(raw.focus,180),
      tasks:(Array.isArray(raw.tasks)?raw.tasks:[]).filter(t=>t && typeof t.id==='string' && typeof t.text==='string' && t.text.trim()).slice(0,50).map(t=>({id:text(t.id,80),text:text(t.text,120),done:t.done===true})),
      links:(Array.isArray(raw.links)?raw.links:[]).filter(l=>l && typeof l.name==='string' && safeUrl(l.url)).slice(0,24).map(l=>({id:text(l.id,80),name:text(l.name,30),url:safeUrl(l.url).href})),
      subscriptions:(Array.isArray(raw.subscriptions)?raw.subscriptions:seeds).filter(s=>s && typeof s.id==='string' && typeof s.name==='string').slice(0,30).map(s=>({id:text(s.id,80),name:text(s.name,50),plan:text(s.plan,80),source:text(s.source,120),verified_at:typeof s.verified_at==='number'?s.verified_at:null,amount:typeof s.amount==='number' && Number.isFinite(s.amount) && s.amount>=0 ? s.amount : null,currency:['KRW','USD','EUR'].includes(s.currency)?s.currency:'KRW',cycle:s.cycle==='yearly'?'yearly':'monthly',renewal:daysUntil(s.renewal)===null?'':s.renewal,tracking:s.tracking!==false}))
    };
  }
  function withSubscriptions(raw,subscriptions) {return {...raw,subscriptions};}
  const api={safeUrl,monthlyTotals,normalizeState,daysUntil,withSubscriptions};
  if (typeof module!=='undefined' && module.exports) module.exports=api;
  else root.DeskLogic=api;
})(typeof window!=='undefined'?window:globalThis);
