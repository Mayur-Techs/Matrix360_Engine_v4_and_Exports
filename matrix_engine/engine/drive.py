"""Read-only Drive REST adapter. Requires a user-provided OAuth access token.
ChatGPT's connected session is NOT exported or reused by this program.
"""
import os,re,json,time,hashlib
from pathlib import Path
import requests
from .core import run
class Drive:
 def __init__(self,token=None):
  token=token or os.environ.get('MATRIX_DRIVE_ACCESS_TOKEN')
  if not token:raise RuntimeError('Set MATRIX_DRIVE_ACCESS_TOKEN to an authorized read-only Drive OAuth token')
  self.session=requests.Session();self.session.headers['Authorization']='Bearer '+token
 def get(self,url,**kwargs):
  for attempt in range(4):
   r=self.session.get(url,timeout=(15,180),**kwargs)
   if r.status_code not in (429,500,502,503,504):r.raise_for_status();return r
   r.close();time.sleep(min(2**attempt,8))
  raise RuntimeError('Drive retry limit exceeded')
 def inventory(self,url):
  match=re.search(r'/folders/([\w-]+)',url)
  if not match:raise ValueError('Expected a Google Drive folder URL')
  queue=[(match.group(1),'')];visited=set();files=[]
  while queue:
   folder,prefix=queue.pop(0)
   if folder in visited:continue
   visited.add(folder);page=None
   while True:
    params={'q':f"'{folder}' in parents and trashed=false",'fields':'nextPageToken,files(id,name,mimeType,size,modifiedTime,md5Checksum)','pageSize':1000,'supportsAllDrives':'true','includeItemsFromAllDrives':'true'}
    if page:params['pageToken']=page
    d=self.get('https://www.googleapis.com/drive/v3/files',params=params).json()
    for f in d.get('files',[]):
     if f['mimeType']=='application/vnd.google-apps.folder':queue.append((f['id'],prefix+f['id']+'/'))
     else:files.append({**f,'relative_path':prefix+f['id']+'/'+Path(f['name']).name})
    page=d.get('nextPageToken')
    if not page:break
  return files
 def sync(self,url,destination):
  dest=Path(destination);dest.mkdir(parents=True,exist_ok=True);files=self.inventory(url);events=[]
  # Whole inventory must succeed before deletion reconciliation.
  for f in files:
   p=dest/f['relative_path'];p.parent.mkdir(parents=True,exist_ok=True);meta=p.with_name(p.name+'.drive-meta');sig=json.dumps(f,sort_keys=True)
   if p.exists() and meta.exists() and meta.read_text()==sig:events.append({'id':f['id'],'status':'UNCHANGED'});continue
   if f['mimeType'].startswith('application/vnd.google-apps.'):
    events.append({'id':f['id'],'status':'UNSUPPORTED_NATIVE_FILE'});continue
   tmp=p.with_name(p.name+'.download')
   try:
    with self.get('https://www.googleapis.com/drive/v3/files/'+f['id'],params={'alt':'media','supportsAllDrives':'true'},stream=True) as r:
     with tmp.open('wb') as out:
      for chunk in r.iter_content(1048576):out.write(chunk)
    if f.get('size') and tmp.stat().st_size!=int(f['size']):raise ValueError('Download size mismatch')
    if f.get('md5Checksum'):
     h=hashlib.md5()
     with tmp.open('rb') as inp:
      for b in iter(lambda:inp.read(1048576),b''):h.update(b)
     if h.hexdigest()!=f['md5Checksum']:raise ValueError('Download checksum mismatch')
    os.replace(tmp,p);meta.write_text(sig);events.append({'id':f['id'],'status':'DOWNLOADED'})
   finally:tmp.unlink(missing_ok=True)
  return files,events
if __name__=='__main__':
 import argparse,shutil
 a=argparse.ArgumentParser();a.add_argument('--url',required=True);a.add_argument('--cache',required=True);a.add_argument('--workspace',required=True);v=a.parse_args()
 files,events=Drive().sync(v.url,v.cache)
 # Build exact current snapshot excluding metadata and removed files.
 stage=Path(v.cache).parent/'current_snapshot'
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir()
 for f in files:
  p=Path(v.cache)/f['relative_path']
  if p.exists():
   q=stage/f['relative_path'];q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 result=run(stage,v.workspace);Path(v.workspace,'drive_manifest.json').write_text(json.dumps({'files':files,'events':events},indent=2));print(json.dumps(result,indent=2))
