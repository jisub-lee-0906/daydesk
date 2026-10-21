import json
from pathlib import Path
import tempfile
import unittest
from public_data import PublicData, normalize_location, parse_feed, merge_news, project_weather, FixedRedirect
RSS=b'<rss><channel><item><title>New &amp; useful</title><link>https://example.com/a?utm_source=x</link><pubDate>Tue, 20 Oct 2026 00:00:00 GMT</pubDate><description>PRIVATE BODY</description></item><item><title>bad</title><link>javascript:bad</link></item></channel></rss>'
ATOM=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom news</title><link href="https://example.com/b"/><updated>2026-10-20T01:00:00Z</updated></entry></feed>'
WEATHER={'current':{'temperature_2m':18,'weather_code':2},'daily':{'temperature_2m_max':[21],'temperature_2m_min':[10],'precipitation_probability_max':[30]}}
class PublicTests(unittest.TestCase):
 def test_coordinate_boundaries_and_privacy_rounding(self):
  self.assertEqual(normalize_location(37.241,127.178),(37.2,127.2))
  self.assertEqual(normalize_location(-90,180),(-90.0,180.0))
  for lat,lon in [(90.01,0),(0,180.1),(True,0),(float('nan'),0),('37',127),(10**400,0)]:
   with self.assertRaises(ValueError): normalize_location(lat,lon)
 def test_rss_atom_projection_and_unsafe_link(self):
  rss=parse_feed(RSS,'github');atom=parse_feed(ATOM,'geeknews')
  self.assertEqual(len(rss),1);self.assertEqual(rss[0]['title'],'New & useful')
  self.assertEqual(rss[0]['url'],'https://example.com/a');self.assertEqual(atom[0]['title'],'Atom news')
  self.assertNotIn('PRIVATE BODY',json.dumps(rss))
  self.assertIsNotNone(rss[0]['published_at'])
 def test_doctype_inside_article_cdata_is_not_a_document_dtd(self):
  feed=b'<rss><channel><item><title>HTML example</title><link>https://example.com/html</link><description><![CDATA[<!DOCTYPE html><html>example</html>]]></description></item></channel></rss>'
  self.assertEqual(len(parse_feed(feed,"github")),1)
 def test_limit_dedup_and_date_order(self):
  items=parse_feed(RSS,'github')+parse_feed(ATOM,'geeknews');items.append(dict(items[0]))
  result=merge_news(items);self.assertEqual(len(result),2);self.assertEqual(result[0]['title'],'Atom news')
  xml=b'<rss><channel>'+b'<item><title>x</title><link>https://example.com/a</link></item>'*30+b'</channel></rss>'
  self.assertEqual(len(parse_feed(xml,'github')),12)
  with self.assertRaises(ValueError):parse_feed(b'<!DOCTYPE rss [<!ENTITY x "evil">]><rss/>','github')
 def test_weather_missing_does_not_become_zero(self):
  self.assertEqual(project_weather(WEATHER)['temperature'],18)
  self.assertIsNone(project_weather({})['temperature'])
  self.assertIsNone(project_weather({'current':{'temperature_2m':True}})['temperature'])
 def test_cache_ttl_failure_and_restart(self):
  with tempfile.TemporaryDirectory() as td:
   clock=[10000];calls=[]
   def fetch(url):
    calls.append(url);return json.dumps(WEATHER).encode() if 'forecast?' in url else (ATOM if 'hada.io' in url else RSS)
   p=Path(td)/'public.json';app=PublicData(p,fetch=fetch,now=lambda:clock[0]);app.refresh()
   first=len(calls);app.refresh();self.assertEqual(len(calls),first)
   initial=app.snapshot()['weather']['updated_at'];clock[0]+=1801
   app.fetch=lambda _: (_ for _ in ()).throw(OSError('offline'));app.refresh();snap=app.snapshot()
   self.assertEqual(snap['weather']['updated_at'],initial);self.assertEqual(snap['weather']['data']['temperature'],18);self.assertTrue(snap['weather']['stale'])
   self.assertEqual(PublicData(p,fetch=fetch,now=lambda:clock[0]).snapshot()['weather']['data']['temperature'],18)
 def test_location_change_during_request_never_relabels_old_weather(self):
  with tempfile.TemporaryDirectory() as td:
   app=None
   def fetch(url):
    if 'forecast?' in url:
     app.set_location(12.34,45.67);return json.dumps(WEATHER).encode()
    return RSS
   app=PublicData(Path(td)/'public.json',fetch=fetch,now=lambda:10000);app.refresh()
   weather=app.snapshot()['weather'];self.assertEqual(weather['mode'],'current');self.assertIsNone(weather['data'])
 def test_current_location_not_persisted_and_coalesced(self):
  with tempfile.TemporaryDirectory() as td:
   clock=[10000];calls=[]
   def fetch(url):
    calls.append(url);return json.dumps(WEATHER).encode() if 'forecast?' in url else RSS
   path=Path(td)/'public.json';app=PublicData(path,fetch=fetch,now=lambda:clock[0])
   app.set_location(12.34,45.67);app.refresh();self.assertEqual(app.snapshot()['weather']['mode'],'current')
   first=len(calls);app.set_location(12.31,45.69);app.refresh();self.assertEqual(len(calls),first)
   app.set_location(13,46);app.refresh();self.assertEqual(len(calls),first);self.assertIsNone(app.snapshot()['weather']['data'])
   clock[0]+=300;app.set_location(13,46);app.refresh();self.assertEqual(len(calls),first+1)
   saved=json.loads(path.read_text());self.assertNotIn('current',saved);self.assertNotIn('latitude',path.read_text())
   self.assertEqual(PublicData(path,fetch=fetch,now=lambda:clock[0]).snapshot()['weather']['mode'],'default')
 def test_owner_lease_prevents_other_tab_reset(self):
  with tempfile.TemporaryDirectory() as td:
   clock=[10000];app=PublicData(Path(td)/'public.json',now=lambda:clock[0])
   self.assertTrue(app.set_location(37,127,owner='one'))
   self.assertFalse(app.set_location(None,None,owner='two'))
   self.assertEqual(app.snapshot()['weather']['mode'],'current')
   clock[0]+=91;self.assertEqual(app.snapshot()['weather']['mode'],'default')
 def test_source_failure_preserves_headlines_and_success_time(self):
  with tempfile.TemporaryDirectory() as td:
   clock=[10000]
   def fetch(url):return json.dumps(WEATHER).encode() if 'forecast?' in url else RSS
   app=PublicData(Path(td)/'public.json',fetch=fetch,now=lambda:clock[0]);app.refresh()
   before=app.snapshot()['sources']['github']['updated_at'];clock[0]+=3601
   app.fetch=lambda _: (_ for _ in ()).throw(OSError('offline'));app.refresh();snap=app.snapshot()
   self.assertTrue(snap['sources']['github']['stale']);self.assertEqual(snap['sources']['github']['updated_at'],before);self.assertTrue(snap['news'])
 def test_incomplete_response_and_recursive_json_preserve_cache_and_recover(self):
  from http.client import IncompleteRead
  for failure in [IncompleteRead(b'partial'),RecursionError('deep JSON')]:
   with self.subTest(failure=type(failure).__name__),tempfile.TemporaryDirectory() as td:
    clock=[10000]
    def good(url):return json.dumps(WEATHER).encode() if 'forecast?' in url else RSS
    app=PublicData(Path(td)/'cache.json',fetch=good,now=lambda:clock[0]);app.refresh()
    clock[0]+=3601
    def bad(_):raise failure
    app.fetch=bad
    app.refresh();self.assertTrue(app.snapshot()['weather']['stale']);self.assertEqual(app.snapshot()['weather']['updated_at'],10000)
    clock[0]+=301;app.fetch=good;app.refresh();self.assertFalse(app.snapshot()['sources']['github']['error'])
 def test_redirect_port_is_fixed(self):
  from urllib.request import Request
  redirect=FixedRedirect();request=Request('https://github.blog/changelog/feed/')
  with self.assertRaises(ValueError):redirect.redirect_request(request,None,302,'',{},'https://github.blog:444/feed/')
  self.assertIsNotNone(redirect.redirect_request(request,None,302,'',{},'https://github.blog:443/feed/'))
if __name__=='__main__':unittest.main()

