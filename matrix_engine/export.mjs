import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const [input,out]=process.argv.slice(2);const data=JSON.parse(await fs.readFile(input,'utf8'));
const projects=['Lakhotia','Shree Heights','Vrindavan Greens'];
async function build(names,file){
 const wb=Workbook.create();
 for(const name of names){const rows=data[name];const s=wb.worksheets.add(name);s.getRange('A1').write(rows.map(r=>r.map(v=>/^[=+@-]/.test(String(v))?"'"+v:String(v))));s.getRange(`A1:V${Math.max(rows.length,2)}`).format.numberFormat='@';s.getRange('A1:V1').format.fill='#14344B';s.getRange('A1:V1').format.font.color='#FFFFFF';s.getRange('A1:V1').format.font.bold=true;s.getRange('A:V').format.columnWidth=24;if(name==='Summary'){s.getRange('A:A').format.columnWidth=30;s.getRange('B:B').format.columnWidth=90;s.getRange('A1:B14').format.wrapText=true;s.getRange('A1:B14').format.rowHeight=32;}}
 await (await SpreadsheetFile.exportXlsx(wb)).save(`${out}/${file}.xlsx`);
 if(file==='Matrix360_Combined_Leads'){try{const p=await wb.render({sheetName:'Summary',range:'A1:B12',scale:1,format:'png'});await fs.writeFile(`${out}/preview.png`,new Uint8Array(await p.arrayBuffer()));}catch(e){console.error('Preview:',e.message);}}
}
await fs.mkdir(out,{recursive:true});
for(const p of projects)await build(['Summary',p],p.replaceAll(' ','_'));
await build(['Summary',...projects,'Review'],'Matrix360_Combined_Leads');
console.log('Four workbooks exported');
