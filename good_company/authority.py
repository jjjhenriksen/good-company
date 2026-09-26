"""Apply only supplied, scoped and currently reviewable source precedence."""
import json
from datetime import date
from .core import required, digest, stamp


def set_precedence(c, rule, authority, now=None):
    required(authority, 'verified organizational authority')
    if not isinstance(rule, dict):
        raise ValueError('Precedence rule must be an object.')
    for key in ('preferred_source', 'overridden_source', 'evidence_source', 'section', 'event_type', 'role', 'effective_from', 'effective_until', 'review_by'):
        required(rule.get(key), key)
    if rule['preferred_source'] == rule['overridden_source']:
        raise ValueError('A source cannot override itself.')
    if date.fromisoformat(rule['effective_from']) >= date.fromisoformat(rule['effective_until']):
        raise ValueError('Precedence needs a positive effective interval.')
    date.fromisoformat(rule['review_by'])
    if not c.db.execute('SELECT 1 FROM knowledge WHERE source=?', (rule['evidence_source'],)).fetchone() or c._source_retired(rule['evidence_source']):
        raise ValueError('Ingest current evidence for the precedence decision first.')
    rule = dict(rule, evidence_hash=digest([list(r) for r in c.db.execute('SELECT source,title,section,content,updated,audience FROM knowledge WHERE source=? ORDER BY section', (rule['evidence_source'],))]))
    rid = digest(rule)[:24]
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        graph = {}
        for row in c.db.execute('SELECT payload FROM source_precedence'):
            old = json.loads(row[0])
            graph.setdefault(old['preferred_source'], set()).add(old['overridden_source'])
        graph.setdefault(rule['preferred_source'], set()).add(rule['overridden_source'])
        def visit(node, path):
            if node in path:
                raise ValueError('Cyclic source precedence is unresolved.')
            for child in graph.get(node, set()):
                visit(child, path | {node})
        for node in graph:
            visit(node, set())
        c.db.execute('INSERT OR IGNORE INTO source_precedence VALUES(?,?)', (rid, json.dumps(rule)))
        for row in c.db.execute('SELECT id FROM events').fetchall():
            c._invalidate(row['id'])
        c.log('source_precedence', rid, {'authority': authority, 'evidence_source': rule['evidence_source']}, stamp(now))
    return {'id': rid}


def resolve(c, matches, event_type, role, event_date, today, audience):
    available = {r['source'] for r in matches}
    removed, decisions = set(), []
    for row in c.db.execute('SELECT payload FROM source_precedence ORDER BY id'):
        rule = json.loads(row[0])
        if rule['preferred_source'] not in available or rule['overridden_source'] not in available:
            continue
        if rule['event_type'].casefold() not in ('*', event_type) or rule['role'].casefold() not in ('*', role):
            continue
        if not date.fromisoformat(rule['effective_from']) <= event_date < date.fromisoformat(rule['effective_until']):
            continue
        if max(today, event_date) > date.fromisoformat(rule['review_by']) or c._source_retired(rule['evidence_source']):
            continue
        evidence = c.db.execute('SELECT audience FROM knowledge WHERE source=? LIMIT 1', (rule['evidence_source'],)).fetchone()
        if not evidence or (audience != 'coordinator' and evidence[0] == 'coordinator'):
            continue
        current_hash = digest([list(r) for r in c.db.execute('SELECT source,title,section,content,updated,audience FROM knowledge WHERE source=? ORDER BY section', (rule['evidence_source'],))])
        if current_hash != rule['evidence_hash']:
            continue
        removed.add(rule['overridden_source'])
        decisions.append({k: rule[k] for k in ('preferred_source', 'overridden_source', 'evidence_source', 'section')})
    return [r for r in matches if r['source'] not in removed], decisions
