"""Standalone source-preserving batch engine. No external AI calls."""
import argparse,csv,hashlib,json,re,sqlite3,time,os
from pathlib import Path
from contextlib import contextmanager
import openpyxl,duckdb,pyarrow as pa,pyarrow.parquet as pq
from .targeting import VERSION, phone_text, classify as target_classify
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def text(v):return '' if v is None else str(v).strip()
def key(v):return re.sub(r'[^a-z0-9]','',text(v).lower())
ALIASES={'name':['name','contactname','owner','ownercontact','contactperson'], 'company':['company','companyname','businessname','organisation'], 'phone':['phone','mobile','mobileno','phoneno','contactnumber','whatsapp91','whatsappnormalized'], 'email':['email','emailid','emailaddress'], 'city':['city','businesscity','town'], 'district':['district','districtname'], 'state':['state','statename'], 'address':['address','address1','address2'], 'vehicle':['regno','registrationnumber','vehicleno'], 'sector':['industry','sector','businesssectorhint','sourcesectorhint'], 'interest':['interest','intereststatus','propertyinterest','intent'], 'enquiry':['enquiry','inquiry','enquirystatus'], 'budget':['budget','budgetrange'], 'timeline':['timeline','purchasetimeline'], 'notes':['notes','remarks','comment']}
def mapping(headers):
 out={}
 for i,h in enumerate(headers):
  for name,aliases in ALIASES.items():
   if key(h) in aliases:out.setdefault(name,[]).append(i)
 return out
def read_tables(p):
 ext=p.suffix.lower()
 if ext in ('.xlsx','.xlsm'):
  w=openpyxl.load_workbook(p,read_only=True,data_only=True)
  try:
   for s in w:yield s.title,enumerate(s.values,1)
  finally:w.close()
 elif ext in ('.csv','.tsv'):
  with p.open(encoding='utf-8-sig',newline='') as f:yield 'data',enumerate(csv.reader(f,delimiter='\t' if ext=='.tsv' else ','),1)
 elif ext=='.xls':
  import xlrd
  w=xlrd.open_workbook(p,on_demand=True)
  try:
   for s in w.sheets():yield s.name,((i+1,s.row_values(i)) for i in range(s.nrows))
  finally:w.release_resources()
 elif ext=='.xlsb':
  from pyxlsb import open_workbook
  with open_workbook(str(p)) as w:
   for n in w.sheets:
    with w.get_sheet(n) as s:yield n,((i+1,[c.v for c in row]) for i,row in enumerate(s.rows()))
 elif ext in ('.jsonl','.ndjson'):
  def rows():
   headers=None
   with p.open(encoding='utf-8-sig') as f:
    for i,line in enumerate(f,1):
     d=json.loads(line)
     if headers is None:headers=list(d);yield 0,headers
     if set(d)-set(headers):raise ValueError('JSONL schema changed; explicit mapping required')
     yield i,[d.get(h) for h in headers]
  yield 'data',rows()
 else:raise ValueError('UNSUPPORTED_FORMAT: '+ext)
def canonical(values,headers,m,source,sheet,row,version):
 def get(n):return ' | '.join(text(values[i]) for i in m.get(n,[]) if i<len(values) and text(values[i]))
 phone,phone_flag=phone_text(get('phone'));phone=phone[2:] if phone.startswith('91') else phone
 valid=bool(re.fullmatch('[6-9][0-9]{9}',phone));email=get('email').lower();ev=bool(re.fullmatch(r"[^\s@]+@[^\s@]+\.[a-z]{2,}",email))
 flags=[]
 if get('phone') and not valid:flags.append('INVALID_OR_MULTIPLE_PHONE')
 if email and not ev:flags.append('INVALID_OR_MULTIPLE_EMAIL')
 if not valid and not ev:flags.append('NO_VALID_CONTACT')
 vehicle=get('vehicle');category='Vehicle owner' if vehicle else 'Business directory' if get('company') else 'Contact directory' if email or phone else 'Unknown'
 raw={str(h or 'column_'+str(i+1)):text(values[i]) if i<len(values) else '' for i,h in enumerate(headers)}
 result=dict(source_record_id=hashlib.sha256(f'{source}|{version}|{sheet}|{row}'.encode()).hexdigest(),source_file=source,source_version=version,source_sheet=sheet,source_row=row,name=get('name'),company=get('company'),phone_source=get('phone'),phone_normalized='91'+phone if valid else '',email_normalized=email if ev else '',city=get('city'),district=get('district'),state=get('state'),address=get('address'),vehicle_registration=vehicle,dataset_category=category,vehicle_location_hint='GJ registration only; residence unknown' if vehicle.upper().startswith('GJ') else '',whatsapp_eligibility='HOLD_PERMISSION_UNKNOWN',instagram_eligibility='HOLD_PERMISSION_UNKNOWN',referral_eligibility='HOLD_NO_PARTICIPATION_EVIDENCE',quality_flags=';'.join(flags),original_fields=json.dumps(raw,ensure_ascii=False),rule_version=VERSION)
 for field in ('sector','interest','enquiry','budget','timeline','notes'):
  result[field]=get(field)
 result=target_classify(result)
 result['quality_flags']=';'.join(x for x in [phone_flag if get('phone') else '',result['geo_status'] if result['geo_status'] in ('GEO_UNKNOWN','REVIEW_REQUIRED','WB_POSSIBLE') else '', 'NO_VALID_CONTACT' if not valid and not ev else ''] if x)
 return result
@contextmanager
def lock(ws):
 p=ws/'run.lock'
 try:fd=os.open(p,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
 except FileExistsError:raise RuntimeError('Workspace locked. Confirm no worker remains before removing run.lock.')
 try:os.write(fd,str(os.getpid()).encode());os.close(fd);yield
 finally:p.unlink(missing_ok=True)
def run(input_dir,workspace,on_progress=None):
 src=Path(input_dir).resolve();ws=Path(workspace).resolve()
 if src==ws or src in ws.parents or ws in src.parents:raise ValueError('Input and workspace must be separate trees')
 ws.mkdir(parents=True,exist_ok=True);(ws/'parquet').mkdir(exist_ok=True)
 with lock(ws):
  db=sqlite3.connect(ws/'jobs.sqlite');db.execute('CREATE TABLE IF NOT EXISTS jobs(source TEXT PRIMARY KEY,version TEXT,status TEXT,rows INTEGER,path TEXT,error TEXT)');db.commit()
  start=time.monotonic();seen=[];events=[]
  files=[p for p in sorted(src.rglob('*')) if p.is_file()]
  for source_index,p in enumerate(files,1):
   if on_progress:on_progress(source_index-1,len(files),str(p.relative_to(src)))
   source=str(p.relative_to(src));seen.append(source);v=digest(p)+'-'+VERSION;old=db.execute('SELECT version,status FROM jobs WHERE source=?',(source,)).fetchone()
   if old==(v,'DONE'):
    events.append({'source':source,'status':'SKIPPED_UNCHANGED'})
    if on_progress:on_progress(source_index,len(files),source)
    continue
   target=ws/'parquet'/(hashlib.sha256((source+v).encode()).hexdigest()+'.parquet');tmp=target.with_suffix('.partial');writer=None;count=0;batch=[]
   db.execute('INSERT OR REPLACE INTO jobs VALUES(?,?,?,?,?,?)',(source,v,'RUNNING',0,'',''));db.commit()
   try:
    for sheet,it in read_tables(p):
     it=iter(it);first=next(it,None)
     if not first:continue
     hr,headers=first;m=mapping(headers)
     # Headerless contact-only sheets preserve the first row rather than losing it.
     if not m and any('@' in text(x) for x in headers):
      import itertools
      m={'email':[next(i for i,x in enumerate(headers) if '@' in text(x))]};it=itertools.chain([first],it);headers=['column_'+str(i+1) for i in range(len(headers))]
     if not m:raise ValueError('SCHEMA_REVIEW_REQUIRED: no recognized columns in '+sheet)
     for row,values in it:
      if not any(text(x) for x in values):continue
      batch.append(canonical(values,headers,m,source,sheet,row,v));count+=1
      if len(batch)>=10000:
       t=pa.Table.from_pylist(batch)
       if writer is None:writer=pq.ParquetWriter(tmp,t.schema)
       writer.write_table(t);batch=[]
    if batch:
     t=pa.Table.from_pylist(batch)
     if writer is None:writer=pq.ParquetWriter(tmp,t.schema)
     writer.write_table(t)
    if writer:writer.close();writer=None;os.replace(tmp,target)
    db.execute('UPDATE jobs SET status=?,rows=?,path=?,error=? WHERE source=?',('DONE',count,str(target) if count else '','',source));db.commit();events.append({'source':source,'status':'DONE','rows':count})
   except Exception as e:
    if writer:writer.close()
    tmp.unlink(missing_ok=True);db.execute('UPDATE jobs SET status=?,rows=0,path=?,error=? WHERE source=?',('FAILED','',type(e).__name__+': '+str(e),source));db.commit();events.append({'source':source,'status':'FAILED','error':str(e)})
   if on_progress:on_progress(source_index,len(files),source)
  # Only a successfully completed scan can mark missing sources inactive.
  for (source,) in db.execute('SELECT source FROM jobs').fetchall():
   if source not in seen:db.execute("UPDATE jobs SET status='REMOVED' WHERE source=?",(source,))
  db.commit();active=db.execute("SELECT path,rows FROM jobs WHERE status='DONE' AND path<>''").fetchall()
  con=duckdb.connect(str(ws/'warehouse.duckdb'));con.execute("SET memory_limit='512MB'");con.execute('SET threads=2')
  if active:
   con.read_parquet([p for p,n in active]).create_view('active_source',replace=True)
   con.execute('CREATE OR REPLACE TABLE records AS SELECT * FROM active_source')
   # Contact collisions are review groups, never automatic person merges.
   con.execute("CREATE OR REPLACE TABLE contact_collisions AS SELECT 'phone' kind,phone_normalized contact,count(*) records FROM records WHERE phone_normalized<>'' GROUP BY 2 HAVING count(*)>1 UNION ALL SELECT 'email',email_normalized,count(*) FROM records WHERE email_normalized<>'' GROUP BY 2 HAVING count(*)>1")
   actual=con.execute('SELECT count(*) FROM records').fetchone()[0];assert actual==sum(n for p,n in active)
   for name,query in {'all_records':'SELECT * FROM records','wb_research_leads':"SELECT * FROM records WHERE geo_status='WB_CONFIRMED' AND (lakhotia_class IN ('Q1','Q2','P1','P2') OR shree_class IN ('Q1','Q2','P1','P2') OR vrindavan_class IN ('Q1','Q2','P1','P2'))",'contact_collisions':'SELECT * FROM contact_collisions'}.items():
    path=str(ws/(name+'.csv')).replace("'","''");con.execute(f"COPY ({query}) TO '{path}' (HEADER,FORMAT CSV)")
  else:
   actual=0
   con.execute('DROP VIEW IF EXISTS active_source')
   con.execute('DROP TABLE IF EXISTS records')
   con.execute('DROP TABLE IF EXISTS contact_collisions')
   for name in ('all_records.csv','wb_research_leads.csv','contact_collisions.csv'):(ws/name).unlink(missing_ok=True)
  event_rows=sum(int(event.get('rows',0)) for event in events if event.get('status')=='DONE')
  failed_files=sum(1 for event in events if event.get('status')=='FAILED')
  geo_counts={}
  collision_groups=0
  if active:
   geo_counts=dict(con.execute("SELECT geo_status,count(*) FROM records GROUP BY geo_status").fetchall())
   collision_groups=con.execute('SELECT count(*) FROM contact_collisions').fetchone()[0]
  report={'version':VERSION,'input_files':len(seen),'active_rows':actual,'expected_rows':sum(n for p,n in active),'reconciled':actual==sum(n for p,n in active),'elapsed_seconds':round(time.monotonic()-start,3),'events':events,'reconciliation':{'input_rows_processed':event_rows,'active_rows':actual,'rejected_rows':0,'failed_files':failed_files,'geography_counts':geo_counts,'deduplication_review_groups':collision_groups,'automatic_merges':0},'limitations':['No inferred buying intent or consent','Conservative geography dictionary; unknown locations retained','File-level restart; interrupted files restart from beginning','No automatic identity merges','Unsupported formats explicitly fail; no archive extraction']}
  (ws/'report.json').write_text(json.dumps(report,indent=2));con.close();db.close();return report
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',required=True);a.add_argument('--workspace',required=True);v=a.parse_args();print(json.dumps(run(v.input,v.workspace),indent=2))
