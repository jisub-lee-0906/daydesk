const {test} = require('node:test');
const assert = require('node:assert/strict');
const {safeUrl, monthlyTotals, normalizeState, daysUntil} = require('../web/logic.js');

test('unsafe shortcuts never become executable links', () => {
  for (const value of ['javascript:alert(1)', 'data:text/html,test', 'file:///C:/secret', 'http://evil.test', 'https://user:pass@example.com']) assert.equal(safeUrl(value), null);
  assert.equal(safeUrl('https://example.com').hostname, 'example.com');
  assert.equal(safeUrl('http://127.0.0.1:10100/').port, '10100');
});
test('monthly equivalents preserve currencies, exclude missing and untracked amounts', () => {
  assert.deepEqual(monthlyTotals([
    {amount: 120000, currency:'KRW', cycle:'yearly', tracking:true},
    {amount: 20, currency:'USD', cycle:'monthly', tracking:true},
    {amount: null, currency:'KRW', tracking:true},
    {amount: 999, currency:'KRW', tracking:false},
  ]), {KRW:10000, USD:20});
});
test('malformed local storage cannot inject invalid state or lose default subscriptions', () => {
  const seeds = [{id:'codex', name:'Codex'}];
  const state=normalizeState({focus:123,tasks:[{}, {id:'x',text:'task',done:true}],links:[{name:'bad',url:'javascript:bad'}], subscriptions:'oops'}, seeds);
  assert.equal(state.focus,'');
  assert.equal(state.tasks.length,1);
  assert.equal(state.links.length,0);
  assert.equal(state.subscriptions[0].id,'codex');
});
test('calendar renewal date uses local day and retains overdue dates', () => {
  const now = new Date(2026,9,20,23,50);
  assert.equal(daysUntil('2026-10-20',now),0);
  assert.equal(daysUntil('2026-10-21',now),1);
  assert.equal(daysUntil('2026-10-19',now),-1);
  assert.equal(daysUntil('',now),null);
});

test('subscription saving preserves old focus, tasks, bookmarks and unknown settings',()=>{
 const {withSubscriptions}=require('../web/logic.js');
 const raw={focus:'keep',tasks:[{text:'legacy'}],links:[{url:'https://example.com/'}],custom:{keep:true},subscriptions:[{id:'old'}]};
 const before=JSON.stringify(raw);const next=withSubscriptions(raw,[{id:'new'}]);
 assert.equal(next.focus,'keep');assert.deepEqual(next.tasks,raw.tasks);assert.deepEqual(next.links,raw.links);assert.deepEqual(next.custom,{keep:true});
 assert.equal(next.subscriptions[0].id,'new');assert.equal(JSON.stringify(raw),before);
});
