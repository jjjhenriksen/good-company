"""Versioned document evidence, with dates supplied by the source owner."""
import json
import sqlite3
from datetime import date
from .core import required, stamp


def validate_metadata(metadata):
    if metadata is None:
        return
    if not isinstance(metadata, dict):
        raise ValueError('Source metadata must be an object.')
    for key in ('version', 'original_source', 'review_authority', 'effective_from', 'review_by'):
        required(metadata.get(key), key)
    start = date.fromisoformat(metadata['effective_from'])
    date.fromisoformat(metadata['review_by'])
    if metadata.get('effective_until') and date.fromisoformat(metadata['effective_until']) <= start:
        raise ValueError('Source effective_until must follow effective_from.')


def retrieve_versions(coordinator, query, audience, on, now):
    """Use an ephemeral FTS index for applicable archived versions and legacy text.

    The persistent archive stays immutable. Current source privacy also gates its
    prior versions, so reclassification cannot expose older public copies.
    """
    day = date.fromisoformat(on) if on else stamp(now).date()
    current = {}
    for row in coordinator.db.execute('SELECT source,audience FROM knowledge'):
        current[row['source']] = row['audience']
    retired = {row[0] for row in coordinator.db.execute('SELECT source FROM retired_sources')}
    gaps, selected = [], []
    versioned_sources = set()
    for row in coordinator.db.execute('SELECT * FROM document_versions ORDER BY source,version'):
        source = row['source']
        if source in retired or source not in current or (audience != 'coordinator' and (current[source] == 'coordinator' or row['audience'] == 'coordinator')):
            continue
        meta = json.loads(row['metadata'])
        if meta is None:
            continue
        versioned_sources.add(source)
        if day < date.fromisoformat(meta['effective_from']) or (meta.get('effective_until') and day >= date.fromisoformat(meta['effective_until'])):
            continue
        if max(day, stamp(now).date()) > date.fromisoformat(meta['review_by']):
            gaps.append({'source': source, 'version': row['version'], 'reason': 'review_overdue'})
            continue
        for chunk in json.loads(row['payload']):
            selected.append(tuple(chunk) + (row['version'],))
    for source in sorted(versioned_sources):
        if not any(chunk[0] == source for chunk in selected) and not any(g['source'] == source for g in gaps):
            gaps.append({'source': source, 'reason': 'no_reviewed_version_effective_on_requested_date'})
    for row in coordinator.db.execute('SELECT source,title,section,content,updated,audience FROM knowledge'):
        if row['source'] in versioned_sources or row['source'] in retired or (audience != 'coordinator' and row['audience'] == 'coordinator'):
            continue
        selected.append(tuple(row) + ('legacy-unreviewed',))
    index = sqlite3.connect(':memory:')
    index.row_factory = sqlite3.Row
    try:
        index.execute("CREATE VIRTUAL TABLE evidence USING fts5(source UNINDEXED,title,section,content,updated UNINDEXED,audience UNINDEXED,version UNINDEXED, tokenize='porter unicode61')")
        index.executemany('INSERT INTO evidence VALUES(?,?,?,?,?,?,?)', selected)
        rows = index.execute('SELECT *,bm25(evidence) AS rank FROM evidence WHERE evidence MATCH ? ORDER BY rank LIMIT 5', (query,)).fetchall()
        evidence = []
        for row in rows:
            item = dict(row)
            item['stale'] = (stamp(now) - stamp(item['updated'])).days > 180 if item['version'] == 'legacy-unreviewed' else False
            if item['version'] == 'legacy-unreviewed':
                item['review_status'] = 'legacy_metadata_unknown'
            evidence.append(item)
        versions = {}
        for chunk in selected:
            versions.setdefault(chunk[0], set()).add(chunk[6])
        for source, values in versions.items():
            if len(values) > 1:
                gaps.append({'source': source, 'reason': 'overlapping_applicable_versions'})
        return evidence, gaps
    finally:
        index.close()
