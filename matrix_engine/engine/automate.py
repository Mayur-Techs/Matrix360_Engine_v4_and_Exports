"""Single command: ingest, WB gate, optional AI review, four workbook exports."""
import argparse,csv,json,subprocess,os,tempfile,shutil
from pathlib import Path
from .core import run
from .ai import annotate
PROJECTS={'Lakhotia':'lakhotia','Shree Heights':'shree','Vrindavan Greens':'vrindavan'}
def export(workspace,output,ai=False,max_calls=20):
 ws=Path(workspace);out=Path(output);out.mkdir(parents=True,exist_ok=True)
 # Export is bounded in memory; warehouse ingestion remains streamed.
 p=ws/'all_records.csv'
 with p.open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
 if len(rows)>250000:raise RuntimeError('EXPORT_REVIEW: XLSX exporter capped at 250000 rows; use warehouse/partition CSV for larger runs')
 if ai:annotate(rows,ws/'ai_cache.json',max_calls)
 headers=['source_record_id','name','company','phone_normalized','email_normalized','city','state','geo_status','lakhotia_class','shree_class','vrindavan_class','rationale','whatsapp_eligibility','instagram_eligibility','referral_eligibility','quality_flags','source_file','source_sheet','source_row','ai_status','ai_suggestion','ai_evidence']
 def matrix(rs):return [headers]+[[str(r.get(h,'')) for h in headers] for r in rs]
 wb=[r for r in rows if r['geo_status']=='WB_CONFIRMED']
 tabs={name:matrix([r for r in wb if r[p+'_class']=='P2']) for name,p in PROJECTS.items()}
 tabs['Review']=matrix([r for r in rows if r['geo_status'] in ('GEO_UNKNOWN','REVIEW_REQUIRED') or r.get('ai_status')=='SUGGESTION_REQUIRES_REVIEW'])
 counts={k:len(v)-1 for k,v in tabs.items()}
 tabs['Summary']=[['Metric','Value'],['Source records',str(len(rows))],['WB confirmed',str(len(wb))],['Outside WB',str(sum(r['geo_status']=='OUTSIDE_WB' for r in rows))],['Research meaning','P2 = observed fit only; no buying intent established'],['Phone handling','Full digits stored as text; source-rounded digits cannot be recovered'],['AI','Suggestions require review; cannot promote geography or contact permission']]+[[k,str(v)] for k,v in counts.items()]
 data=out/'export_data.json';data.write_text(json.dumps(tabs,ensure_ascii=False))
 node=os.environ.get('CODEX_PRIMARY_RUNTIME_NODE','node')
 builder=Path(__file__).resolve().parents[1]/'export.mjs'
 if os.environ.get('CODEX_PRIMARY_RUNTIME_NODE_MODULES'):
  temp=Path(tempfile.mkdtemp(prefix='matrix-export-'));shutil.copy(builder,temp/'export.mjs');(temp/'node_modules').symlink_to(os.environ['CODEX_PRIMARY_RUNTIME_NODE_MODULES'],target_is_directory=True);builder=temp/'export.mjs'
 subprocess.run([node,str(builder),str(data.resolve()),str(out.resolve())],check=True)
 (out/'run_summary.json').write_text(json.dumps(counts,indent=2));return counts
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--input',required=True);a.add_argument('--workspace',required=True);a.add_argument('--output',required=True);a.add_argument('--ai',action='store_true');a.add_argument('--max-ai-calls',type=int,default=20);v=a.parse_args()
 run(v.input,v.workspace);print(json.dumps(export(v.workspace,v.output,v.ai,v.max_ai_calls)))
