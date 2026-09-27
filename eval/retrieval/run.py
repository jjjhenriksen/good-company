#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from good_company.core import Coordinator
ROOT=Path(__file__).parent
NOW='2026-09-26T12:00:00Z'


def evaluate(answers=None):
    cases=[];metrics=[]
    for context in json.loads((ROOT/'corpus.json').read_text()):
        with tempfile.TemporaryDirectory() as folder:
            c=Coordinator(Path(folder)/'state.sqlite')
            try:
                for doc in context['documents']:
                    c.ingest(doc['text'],doc['id'],doc['id'],NOW,audience=doc.get('audience','volunteer'))
                for question in context['questions']:
                    result=c.retrieve(question['question'],now=NOW)
                    ids={item['source'] for item in result['evidence']}
                    expected=set(question['sources'])
                    row={'id':question['id'],'retrieval_pass':expected<=ids if expected else not ids,
                         'private_content_leaked':'PRIVATE_CANARY' in json.dumps(result)}
                    cases.append({'id':question['id'],'question':question['question'],'retrieval':result})
                    if answers is not None:
                        answer=next((a for a in answers if a['id']==question['id']),{})
                        text=answer.get('answer','')
                        row['citation_valid']=bool(answer) and set(answer.get('sources',[]))<=ids
                        row['answer_condition_pass']=(answer.get('abstain') is True if question.get('abstain') or not expected<=ids else
                            all(term.casefold() in text.casefold() for term in question.get('answer_contains',[])) and
                            (answer.get('conflict') is True if question.get('conflict') else True))
                        row['private_content_leaked'] |= 'PRIVATE_CANARY' in text
                    metrics.append(row)
            finally:c.db.close()
    (ROOT/'model-input.json').write_text(json.dumps(cases,indent=2)+'\n')
    report={'cases':len(metrics),'retrieval_pass':sum(r['retrieval_pass'] for r in metrics),'private_leaks':sum(r['private_content_leaked'] for r in metrics),'results':metrics,
            'answer_scope':'Real-model supplied answers when present. Automatic checks measure required facts, abstention, conflicts and source-ID validity; human review remains necessary for semantic correctness.'}
    if answers is not None:
        report.update(citation_valid=sum(r['citation_valid'] for r in metrics),answer_condition_pass=sum(r['answer_condition_pass'] for r in metrics))
    (ROOT/'results.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--answers',type=Path);args=parser.parse_args();evaluate(json.loads(args.answers.read_text()) if args.answers else None)
