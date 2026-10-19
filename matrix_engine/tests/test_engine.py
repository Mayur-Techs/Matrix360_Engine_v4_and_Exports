import csv,json
from pathlib import Path
import pytest,duckdb
from engine.core import run,canonical,mapping,lock

def put(p,rows):
 with p.open('w',newline='') as f:csv.writer(f).writerows(rows)
def test_resume_change_delete(tmp_path):
 src=tmp_path/'input';src.mkdir();ws=tmp_path/'ws'
 put(src/'a.csv',[['Name','Email','City','Company'],['A','a@b.com','Howrah','Steel works'],['B','a@b.com','Surat','Car']])
 r=run(src,ws);assert r['active_rows']==2 and r['reconciled']
 c=duckdb.connect(str(ws/'warehouse.duckdb'));assert c.execute('select records from contact_collisions').fetchone()[0]==2;c.close()
 assert run(src,ws)['events'][0]['status']=='SKIPPED_UNCHANGED'
 put(src/'a.csv',[['Name','Email'],['X','x@y.com']]);assert run(src,ws)['active_rows']==1
 (src/'a.csv').unlink();assert run(src,ws)['active_rows']==0
 assert not (ws/'all_records.csv').exists()

def test_unsupported_and_invalid(tmp_path):
 src=tmp_path/'input';src.mkdir();(src/'a.rar').write_bytes(b'x');r=run(src,tmp_path/'ws');assert r['events'][0]['status']=='FAILED'
def test_no_car_intent_or_geo_inference():
 h=['NAME','REG. NO','PHONE'];r=canonical(['A','GJ05AA1','123'],h,mapping(h),'x','s',2,'v')
 assert r['geo_status']=='GEO_UNKNOWN' and r['lakhotia_class']=='REVIEW_REQUIRED' and not r['phone_normalized']
 assert r['whatsapp_eligibility'].startswith('HOLD')
def test_phone_source_preserves_leading_zero_without_numeric_coercion():
 h=['Name','Phone','City'];r=canonical(['A','09876543210','Howrah'],h,mapping(h),'x','s',2,'v')
 assert r['phone_source']=='09876543210'
 assert r['phone_normalized']==''
def test_excel_text_prefix_phone_normalizes_without_mutating_source():
 h=['Name','Phone','City'];r=canonical(['A',"'9876543210",'Howrah'],h,mapping(h),'x','s',2,'v')
 assert r['phone_source']=="'9876543210"
 assert r['phone_normalized']=='919876543210'
def test_headerless_first_record(tmp_path):
 src=tmp_path/'input';src.mkdir();put(src/'a.csv',[['','a@b.com'],['','c@d.com']]);assert run(src,tmp_path/'ws')['active_rows']==2
def test_lock(tmp_path):
 with lock(tmp_path):
  with pytest.raises(RuntimeError):
   with lock(tmp_path):pass

def test_conflicting_geography():
 h=['City','State'];r=canonical(['Howrah','Gujarat'],h,mapping(h),'x','s',2,'v');assert r['geo_status']=='REVIEW_REQUIRED'
def test_failed_replacement_excludes_old(tmp_path):
 src=tmp_path/'i';src.mkdir();p=src/'a.csv';put(p,[['Name'],['A']]);ws=tmp_path/'w';assert run(src,ws)['active_rows']==1
 put(p,[['Unmapped'],['A']]);assert run(src,ws)['active_rows']==0

def test_drive_pagination_and_recursion():
 from engine.drive import Drive
 class Response:
  def __init__(self,d):self.d=d
  def json(self):return self.d
 d=object.__new__(Drive);calls=[]
 def get(url,params):
  calls.append(params)
  if 'child' in params['q']:return Response({'files':[{'id':'f2','name':'b.csv','mimeType':'text/csv'}]})
  if params.get('pageToken'):return Response({'files':[{'id':'child','name':'nested','mimeType':'application/vnd.google-apps.folder'}]})
  return Response({'nextPageToken':'p2','files':[{'id':'f1','name':'a.csv','mimeType':'text/csv'}]})
 d.get=get
 assert len(d.inventory('https://drive.google.com/drive/folders/root'))==2
 assert len(calls)==3
