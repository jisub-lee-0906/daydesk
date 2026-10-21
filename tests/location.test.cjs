const {test}=require('node:test'),assert=require('node:assert/strict');
const {LocationTracker,coarseLocation}=require('../web/location.js');
test('location rounds before transfer and resists cell-boundary jitter',()=>{
 assert.deepEqual(coarseLocation({latitude:37.241,longitude:127.178}),{latitude:37.2,longitude:127.2});
 const old={latitude:37.2,longitude:127.2};
 assert.equal(coarseLocation({latitude:37.251,longitude:127.201},old),old);
 assert.throws(()=>coarseLocation({latitude:91,longitude:0}));
});
test('pause stops watch, stale callbacks ignored, resume creates a fresh watch',()=>{
 let success,cleared=[],sent=[],fallback=[];
 const geo={watchPosition(s){success=s;return cleared.length+1;},clearWatch(id){cleared.push(id);}};
 const t=new LocationTracker(geo,p=>sent.push(p),r=>fallback.push(r));t.start();const oldCallback=success;
 success({coords:{latitude:37.24,longitude:127.18}});assert.equal(sent.length,1);
 success({coords:{latitude:37.251,longitude:127.201}});assert.equal(sent.length,1);
 t.pause();assert.deepEqual(cleared,[1]);oldCallback({coords:{latitude:50,longitude:50}});assert.equal(sent.length,1);
 assert.equal(fallback.at(-1),'paused');t.resume();success({coords:{latitude:38,longitude:128}});assert.equal(sent.length,2);
 t.disable();assert.equal(t.enabled,false);
});
test('unavailable geolocation returns default instead of pretending to track',()=>{
 let reason;const t=new LocationTracker(null,()=>assert.fail(),r=>reason=r);t.start();
 assert.equal(t.enabled,false);assert.equal(reason,'unsupported');
});

test('a synchronous browser geolocation error cannot break the dashboard',()=>{
 let reason;const t=new LocationTracker({watchPosition(){throw Error('blocked');},clearWatch(){}},()=>{},r=>reason=r);
 assert.doesNotThrow(()=>t.start());assert.equal(t.enabled,false);assert.equal(reason,'unavailable');
});
