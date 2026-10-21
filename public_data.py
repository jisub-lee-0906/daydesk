"""Bounded public RSS/weather worker; device sampling and precise geolocation stay separate."""
from copy import deepcopy
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import io
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET
from xml.parsers import expat

SOURCES = {
 'github': ('GitHub', 'https://github.blog/changelog/feed/'),
 'huggingface': ('Hugging Face', 'https://huggingface.co/blog/feed.xml'),
 'geeknews': ('GeekNews', 'https://news.hada.io/rss/news'),
}
YONGIN = (37.2, 127.2)
MAX_BYTES = 2 * 1024 * 1024

def finite(value):
 if isinstance(value,bool) or not isinstance(value,(int,float)):return False
 try:return math.isfinite(value)
 except OverflowError:return False

def normalize_location(latitude, longitude):
 if not finite(latitude) or not finite(longitude) or not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
  raise ValueError('invalid_location')
 return (round(latitude,1), round(longitude,1))

def safe_news_url(value):
 try:
  u=urlsplit(value)
  if u.scheme!='https' or not u.hostname or u.username or u.password or u.port not in (None,443):
   return None
  query=urlencode([(k,v) for k,v in parse_qsl(u.query) if not k.lower().startswith('utm_')])
  return urlunsplit(('https',u.netloc.lower(),u.path or '/',query,''))
 except (ValueError,TypeError):return None

def parsed_time(value):
 try:
  try:date=datetime.fromisoformat(value.replace('Z','+00:00'))
  except (ValueError,AttributeError):date=parsedate_to_datetime(value)
  if date.tzinfo is None:date=date.replace(tzinfo=timezone.utc)
  return date.timestamp()
 except (ValueError,TypeError,AttributeError,OverflowError):return None

def parse_feed(body, source):
 if len(body)>MAX_BYTES:raise ValueError('invalid_feed')
 def deny_doctype(*args):raise ValueError('invalid_feed')
 check=expat.ParserCreate();check.StartDoctypeDeclHandler=deny_doctype
 try:check.Parse(body,True)
 except expat.ExpatError as error:raise ValueError('invalid_feed') from error
 items=[]
 try:
  for _,node in ET.iterparse(io.BytesIO(body),events=('end',)):
   kind=node.tag.split('}')[-1]
   if kind not in ('item','entry'):continue
   fields={}
   for child in node:
    key=child.tag.split('}')[-1]
    if key=='link':
     if child.attrib.get('rel','alternate')=='alternate':
      fields['link']=child.attrib.get('href') or child.text
    elif key in ('title','pubDate','published','updated'):
     fields[key]=''.join(child.itertext()).strip()
   url=safe_news_url(fields.get('link'))
   title=fields.get('title','').strip()[:240]
   if url and title:
    items.append({'title':title,'url':url,'source':source,'published_at':parsed_time(fields.get('pubDate') or fields.get('published') or fields.get('updated'))})
   node.clear()
   if len(items)>=12:break
 except ET.ParseError as error:raise ValueError('invalid_feed') from error
 return items

def merge_news(items):
 result=[];seen=set()
 for item in sorted(items,key=lambda i:i.get('published_at') or 0,reverse=True):
  if item['url'] in seen:continue
  seen.add(item['url']);result.append(item)
 return result[:36]

def project_weather(raw):
 current=raw.get('current',{}) if isinstance(raw,dict) else {}
 daily=raw.get('daily',{}) if isinstance(raw,dict) else {}
 current=current if isinstance(current,dict) else {}
 daily=daily if isinstance(daily,dict) else {}
 def scalar(value):return value if finite(value) else None
 def first(key):
  v=daily.get(key)
  return scalar(v[0]) if isinstance(v,list) and v else None
 return {'temperature':scalar(current.get('temperature_2m')),'code':scalar(current.get('weather_code')),
         'high':first('temperature_2m_max'),'low':first('temperature_2m_min'),'rain':first('precipitation_probability_max')}

class FixedRedirect(HTTPRedirectHandler):
 def redirect_request(self, req, fp, code, msg, headers, newurl):
  allowed={'api.open-meteo.com','github.blog','huggingface.co','news.hada.io'}
  u=urlsplit(newurl)
  if u.scheme!='https' or u.hostname not in allowed or u.username or u.password or u.port not in (None,443):
   raise ValueError('redirect_not_allowed')
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_public(url):
 request=Request(url,headers={'User-Agent':'Daydesk/1.0 personal-headline-reader','Accept-Encoding':'identity'})
 with build_opener(FixedRedirect()).open(request,timeout=8) as response:
  data=response.read(MAX_BYTES+1)
  if len(data)>MAX_BYTES:raise ValueError('response_too_large')
  return data

def empty_weather():
 return {'data':None,'updated_at':None,'error':False}

class PublicData:
 def __init__(self, cache_path, fetch=fetch_public, now=time.time):
  self.cache_path=Path(cache_path);self.fetch=fetch;self.now=now
  self.lock=threading.Lock();self.stop=threading.Event();self.wake=threading.Event()
  self.mode='default';self.coords=YONGIN;self.generation=0;self.owner=None;self.lease=0
  self.default=empty_weather();self.current=empty_weather()
  self.feeds={k:{'items':[],'updated_at':None,'error':False} for k in SOURCES}
  self.last_attempt={'default':-math.inf,'current':-math.inf,**{k:-math.inf for k in SOURCES}}
  self.last_seen=self.now();self._load()
  self.thread=threading.Thread(target=self.run,name='public-data',daemon=True)

 def _load(self):
  try:
   if self.cache_path.stat().st_size>MAX_BYTES:return
   data=json.loads(self.cache_path.read_text(encoding='utf-8'))
   weather=data.get('default_weather',{})
   fields=('temperature','code','high','low','rain')
   if isinstance(weather.get('data'),dict) and finite(weather.get('updated_at')):
    self.default={'data':{k:weather['data'].get(k) if finite(weather['data'].get(k)) else None for k in fields},'updated_at':weather['updated_at'],'error':False}
   for key in SOURCES:
    stored=data.get('feeds',{}).get(key,{})
    items=[]
    for item in stored.get('items',[])[:12]:
     url=safe_news_url(item.get('url'))
     if url and isinstance(item.get('title'),str):
      items.append({'title':item['title'][:240],'url':url,'source':key,'published_at':item.get('published_at') if finite(item.get('published_at')) else None})
    self.feeds[key]={'items':items,'updated_at':stored.get('updated_at') if finite(stored.get('updated_at')) else None,'error':False}
  except (OSError,ValueError,TypeError,AttributeError,RecursionError):pass

 def _save(self):
  with self.lock:
   data={'version':1,'default_weather':deepcopy(self.default),'feeds':deepcopy(self.feeds)}
  try:
   self.cache_path.parent.mkdir(parents=True,exist_ok=True)
   temp=self.cache_path.with_suffix('.tmp')
   temp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False),encoding='utf-8')
   os.replace(temp,self.cache_path)
  except OSError:pass

 def _expire(self):
  if self.mode=='current' and self.now()>self.lease:
   self.mode='default';self.coords=YONGIN;self.current=empty_weather();self.owner=None;self.generation+=1

 def set_location(self, latitude=None, longitude=None, owner='test-owner'):
  coords=None if latitude is None and longitude is None else normalize_location(latitude,longitude)
  if not isinstance(owner,str) or not 1<=len(owner)<=80 or not all(c.isalnum() or c=='-' for c in owner):
   raise ValueError('invalid_owner')
  with self.lock:
   self._expire()
   if self.owner and self.owner!=owner:return False
   mode='current' if coords is not None else 'default'
   coords=coords or YONGIN
   if mode!=self.mode or coords!=self.coords:
    self.generation+=1;self.current=empty_weather()
   self.mode=mode;self.coords=coords;self.owner=owner if mode=='current' else None
   self.lease=self.now()+90 if mode=='current' else 0;self.last_seen=self.now()
  self.wake.set()
  return True

 def snapshot(self):
  now=self.now()
  with self.lock:
   self._expire();self.last_seen=now
   entry=deepcopy(self.current if self.mode=='current' else self.default)
   entry.update({'mode':self.mode,'location':'현재 위치 주변' if self.mode=='current' else '용인','stale':self._stale(entry,1800,now),'loading':entry['data'] is None})
   sources={k:{'name':SOURCES[k][0],'updated_at':v['updated_at'],'stale':self._stale(v,3600,now),'error':v['error']} for k,v in self.feeds.items()}
   news=merge_news([deepcopy(item) for v in self.feeds.values() for item in v['items']])
  # Dates in the future never gain a false 'latest' priority.
  for item in news:
   if item['published_at'] is not None and item['published_at']>now+300:item['published_at']=None
  news=merge_news(news)
  return {'weather':entry,'news':news,'sources':sources}

 @staticmethod
 def _stale(entry, ttl, now):
  updated=entry.get('updated_at')
  return entry.get('error',False) or updated is None or now-updated>ttl or updated>now+60

 def refresh(self):
  now=self.now()
  with self.lock:
   self._expire()
   mode,coords,generation=self.mode,self.coords,self.generation
   entry=self.current if mode=='current' else self.default
   due=self._stale(entry,1800,now)
   gap=300 if mode=='current' else 60
   weather_due=due and now-self.last_attempt[mode]>=gap
   if weather_due:self.last_attempt[mode]=now
  if weather_due:
   args=urlencode({'latitude':coords[0],'longitude':coords[1],'current':'temperature_2m,weather_code','daily':'temperature_2m_max,temperature_2m_min,precipitation_probability_max','forecast_days':1,'timezone':'auto'})
   try:
    data=project_weather(json.loads(self.fetch('https://api.open-meteo.com/v1/forecast?'+args)))
    if data['temperature'] is None:raise ValueError('missing_weather')
    fresh={'data':data,'updated_at':self.now(),'error':False}
   except (OSError,ValueError,TimeoutError,HTTPException,RecursionError):
    fresh=None
   with self.lock:
    if mode=='default':
     if fresh:self.default=fresh
     else:self.default['error']=True
    elif self.mode==mode and self.coords==coords and self.generation==generation:
     if fresh:self.current=fresh
     else:self.current['error']=True
  changed=weather_due
  for key,(_,url) in SOURCES.items():
   now=self.now()
   with self.lock:
    due=self._stale(self.feeds[key],3600,now) and now-self.last_attempt[key]>=300
    if due:self.last_attempt[key]=now
   if not due:continue
   changed=True
   try:
    items=parse_feed(self.fetch(url),key)
    if not items:raise ValueError('empty_feed')
    fresh={'items':items,'updated_at':self.now(),'error':False}
   except (OSError,ValueError,TimeoutError,HTTPException,RecursionError):fresh=None
   with self.lock:
    if fresh:self.feeds[key]=fresh
    else:self.feeds[key]['error']=True
  if changed:self._save()

 def run(self):
  while not self.stop.is_set():
   if self.now()-self.last_seen<120:self.refresh()
   self.wake.wait(30);self.wake.clear()

 def close(self):
  self.stop.set();self.wake.set()
  self.thread.join(timeout=1)
