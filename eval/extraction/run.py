#!/usr/bin/env python3
"""Rebuild fictional table/scan PDFs and measure location-sensitive extraction."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

ROOT=Path(__file__).parent


def run(output):
    output.mkdir(parents=True,exist_ok=True)
    fixtures=json.loads((ROOT/'fixtures.json').read_text())
    table=output/'fictional-tables.pdf';scan=output/'fictional-scans.pdf'
    pdf=canvas.Canvas(str(table),pagesize=letter,invariant=1)
    for page,item in enumerate(fixtures,1):
        pdf.setFont('Helvetica-Bold',16);pdf.drawString(40,745,item['title'])
        pdf.setFont('Helvetica',11);pdf.drawString(40,720,'Fictional fixture | Audience: '+item['audience'])
        xs=[40,175,280,355];y=675
        for index,row in enumerate([item['columns']]+item['rows']):
            pdf.setFont('Helvetica-Bold' if index==0 else 'Helvetica',10)
            for x,text in zip(xs,row):pdf.drawString(x,y,text)
            pdf.line(40,y-8,565,y-8);y-=38
        pdf.setFont('Helvetica',10);pdf.drawString(40,510,item['exception'])
        pdf.drawString(40,45,'Fixture '+item['id']+' | page '+str(page))
        pdf.showPage()
    pdf.save()
    with tempfile.TemporaryDirectory() as folder:
        prefix=Path(folder)/'page'
        subprocess.run(['pdftoppm','-r','150','-png',str(table),str(prefix)],check=True,capture_output=True)
        images=sorted(Path(folder).glob('page-*.png'))
        pdf=canvas.Canvas(str(scan),pagesize=letter,invariant=1)
        for img in images:pdf.drawImage(str(img),0,0,width=612,height=792);pdf.showPage()
        pdf.save()
        results=[]
        for mode,path in [('digital_layout',table),('scan_without_ocr',scan)]:
            text=subprocess.check_output(['pdftotext','-layout',str(path),'-']).decode()
            for item,page in zip(fixtures,text.split('\f')):results.append(score(mode,item,page))
        for item,img in zip(fixtures,images):
            text=subprocess.check_output(['tesseract',str(img),'stdout','--psm','6'],stderr=subprocess.DEVNULL).decode()
            results.append(score('scan_ocr',item,text))
    report={'fixtures':len(fixtures),'checks':results,
            'scope':'Fictional clean 150-DPI scans only. Row association, date/role/exception and privacy-label recovery; not a claim of arbitrary PDF accuracy.',
            'privacy':'Audience is supplied in fixtures.json; extracted labels never grant access.',
            'versions':{'poppler':subprocess.run(['pdftotext','-v'],capture_output=True,text=True).stderr.splitlines()[0],
                        'tesseract':subprocess.check_output(['tesseract','--version']).decode().splitlines()[0]}}
    (output/'results.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


def score(mode,item,text):
    lines=text.splitlines();pairs=[]
    for row in item['rows']:
        pairs.append(all(any(cell in line and row[0] in line for line in lines) for cell in row[1:]))
    return {'method':mode,'fixture':item['id'],'row_association_correct':sum(pairs),'rows':len(pairs),
            'exception_recovered':item['exception'] in text,'privacy_label_recovered':item['audience'] in text,
            'page_location_recovered':'Fixture '+item['id'] in text}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'artifacts');args=parser.parse_args();run(args.output)
