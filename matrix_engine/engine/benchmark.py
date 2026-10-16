import argparse,csv,json
try:
 import resource
except ImportError:
 resource=None
from pathlib import Path
from .core import run
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--rows',type=int,default=500000);p.add_argument('--input',required=True);p.add_argument('--workspace',required=True);a=p.parse_args()
 src=Path(a.input);src.mkdir(parents=True,exist_ok=True)
 with (src/'synthetic.csv').open('w',newline='') as f:
  w=csv.writer(f);w.writerow(['Name','Company','City','Email'])
  for i in range(a.rows):w.writerow([f'Synthetic {i}','Steel works','Howrah',f'record{i}@example.invalid'])
 r=run(src,a.workspace);r['peak_rss_kib_linux']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss if resource else None;print(json.dumps(r,indent=2))
