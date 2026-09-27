"""Narrow trusted-owner data lifecycle operations that retain send tombstones."""
import json
from .core import required, required_time, stamp, iso


def export_summary(c, authority):
    required(authority, 'owner export authority')
    tables = {r[0] for r in c.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    counts = {}
    for table in ('events', 'volunteers', 'tasks', 'reminders', 'task_notices', 'corrections'):
        if table in tables:
            counts[table] = c.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]
    return {'format': 1, 'counts': counts, 'scope': 'Aggregate counts only; no recipients, message text, credentials or skill assessments.'}


def delete_source(c, source, authority, now=None):
    required(authority, 'owner source deletion authority')
    # Withdrawal must succeed first, so any interruption fails closed.
    c.withdraw_source(source, authority, now=now)
    with c.db:
        c.db.execute('DELETE FROM knowledge WHERE source=?', (source,))
        c.db.execute('DELETE FROM dress_rules WHERE source=?', (source,))
        c.db.execute('DELETE FROM document_versions WHERE source=?', (source,))
        # Translation records retain both original and translated source text,
        # including versions that are no longer the current knowledge entry.
        translations = c.db.execute("SELECT key,value FROM settings WHERE key LIKE 'translation:%'").fetchall()
        for key, value in translations:
            if json.loads(value)['source'] == source:
                c.db.execute('DELETE FROM settings WHERE key=?', (key,))
        c.log('source_content_deleted', source, {'authority': authority}, stamp(now))
    return {'deleted': True, 'scope': 'Logical deletion of stored source content, archived versions and reviewed translations. Source tombstone, audit references and delivery history retained. SQLite free pages and independent backups are not securely erased.'}


def retain_delivery_history(c, before, authority, now=None):
    required(authority, 'owner retention authority')
    cutoff, now = required_time(before, 'retention cutoff'), stamp(now)
    if cutoff >= now:
        raise ValueError('Retention cutoff must be in the past.')
    tables = {r[0] for r in c.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    changed = 0
    with c.db:
        c.db.execute('BEGIN IMMEDIATE')
        for table, action in [('reminders', 'send_claim'), ('task_notices', 'task_notice_claim'), ('corrections', 'correction_claim')]:
            if table not in tables:
                continue
            rows = c.db.execute(f'''SELECT n.id,n.message FROM {table} n WHERE n.status IN ('sent','failed')
              AND EXISTS (SELECT 1 FROM audit a WHERE a.object_id=n.id AND a.action=? AND a.at<?)''', (action, iso(cutoff))).fetchall()
            for row in rows:
                old = json.loads(row['message'])
                minimal = {key: old[key] for key in ('sender', 'to', 'bcc') if key in old}
                minimal.update(subject='[removed by retention policy]', body='[removed by retention policy]')
                if minimal != old:
                    c.db.execute(f'UPDATE {table} SET message=? WHERE id=?', (json.dumps(minimal), row['id']))
                    changed += 1
        c.log('delivery_content_retention', 'history', {'before': iso(cutoff), 'changed': changed, 'authority': authority}, now)
    return {'redacted_messages': changed, 'scope': 'Finalized message content removed; recipient routing, receipt IDs and attempt tombstones remain for deduplication and reconciliation. Unknown deliveries are preserved.'}
