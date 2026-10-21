import http.client,json,threading,unittest
from server import make_server
class Sampler:
 def snapshot(self):return {'pc':{'cpu_percent':5},'history':[]}
class Public:
 def __init__(self):self.calls=[]
 def snapshot(self):return {'weather':{'location':'용인'},'news':[]}
 def set_location(self,lat=None,lon=None,owner=''):
  self.calls.append((lat,lon,owner))
  if isinstance(lat,bool) or (lat is not None and not -90<=lat<=90):raise ValueError()
  return owner!='other'
class LocationApiTests(unittest.TestCase):
 def setUp(self):
  self.public=Public();self.server=make_server(Sampler(),0,self.public)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join()
 def request(self,body,origin=None,content='application/json',path='/api/location'):
  c=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=3)
  host='http://127.0.0.1:'+str(self.server.server_port)
  c.request('POST',path,body=body,headers={'Content-Type':content,'Origin':origin or host})
  r=c.getresponse();data=r.read();c.close();return r.status,data
 def test_valid_location_and_reset(self):
  for data in [{'mode':'current','latitude':37.2,'longitude':127.2,'owner':'one'},{'mode':'default','owner':'one'}]:
   self.assertEqual(self.request(json.dumps(data))[0],200)
  self.assertEqual(self.public.calls[-1],(None,None,'one'))
 def test_invalid_origin_type_body_and_owner_conflict(self):
  payload=json.dumps({'mode':'current','latitude':37,'longitude':127,'owner':'one'})
  self.assertEqual(self.request(payload,origin='https://evil.example')[0],403)
  self.assertEqual(self.request(payload,content='text/plain')[0],415)
  self.assertEqual(self.request('{bad')[0],400)
  self.assertEqual(self.request(json.dumps({'mode':'current','owner':'one'}))[0],400)
  self.assertEqual(self.request('x'*513)[0],413)
  self.assertEqual(self.request(json.dumps({'mode':'default','owner':'other'}))[0],409)
  self.assertEqual(self.request(json.dumps({'mode':'current','latitude':True,'longitude':127,'owner':'one'}))[0],400)
class PublicResponsivenessTests(unittest.TestCase):
 def test_blocked_internet_worker_does_not_block_pc_api(self):
  import tempfile,time
  from pathlib import Path
  from public_data import PublicData
  started=threading.Event();release=threading.Event()
  def fetch(url):
   started.set();release.wait(3)
   return b'{"current":{"temperature_2m":18}}'
  with tempfile.TemporaryDirectory() as td:
   public=PublicData(Path(td)/'cache.json',fetch=fetch)
   server=make_server(Sampler(),0,public)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();public.thread.start()
   try:
    self.assertTrue(started.wait(2));begin=time.perf_counter()
    c=http.client.HTTPConnection('127.0.0.1',server.server_port,timeout=1)
    c.request('GET','/api/status');r=c.getresponse();body=json.loads(r.read());c.close()
    self.assertEqual(body['pc']['cpu_percent'],5);self.assertLess(time.perf_counter()-begin,1)
   finally:
    release.set();public.close();server.shutdown();server.server_close();thread.join()
if __name__=='__main__':unittest.main()

