(function(root){
 'use strict';
 function coarseLocation(coords,previous){
  const lat=coords.latitude,lon=coords.longitude;
  if(typeof lat!=='number'||typeof lon!=='number'||!Number.isFinite(lat)||!Number.isFinite(lon)||Math.abs(lat)>90||Math.abs(lon)>180)throw Error('invalid location');
  if(previous&&Math.abs(lat-previous.latitude)<0.08&&Math.abs(lon-previous.longitude)<0.08)return previous;
  return {latitude:Math.round(lat*10)/10,longitude:Math.round(lon*10)/10};
 }
 class LocationTracker{
  constructor(geo,onPosition,onFallback){this.geo=geo;this.onPosition=onPosition;this.onFallback=onFallback;this.enabled=false;this.watch=null;this.generation=0;this.position=null;}
  start(){
   this.enabled=true;if(this.watch!==null)return;
   if(!this.geo){this.fail('unsupported');return;}
   const generation=++this.generation;
   try{this.watch=this.geo.watchPosition(pos=>{
    if(generation!==this.generation||!this.enabled)return;
    try{const next=coarseLocation(pos.coords,this.position);if(next!==this.position){this.position=next;this.onPosition(next);}}catch{this.fail('invalid');}
   },error=>{if(generation===this.generation)this.fail(error?.code===1?'permission-denied':error?.code===3?'timeout':'unavailable');},{enableHighAccuracy:false,maximumAge:600000,timeout:10000});}catch{this.fail('unavailable');}
  }
  clear(){++this.generation;if(this.watch!==null){this.geo.clearWatch(this.watch);this.watch=null;}this.position=null;}
  pause(){this.clear();if(this.enabled)this.onFallback('paused');}
  resume(){if(this.enabled)this.start();}
  fail(reason){this.clear();this.enabled=false;this.onFallback(reason);}
  disable(){this.clear();this.enabled=false;this.onFallback('disabled');}
 }
 const api={LocationTracker,coarseLocation};
 if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.DeskLocation=api;
})(typeof window!=='undefined'?window:globalThis);
