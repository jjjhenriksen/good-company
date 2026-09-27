"""Reviewed translated evidence, with original conditions retained verbatim."""
import json
from .core import required, digest, stamp


def register(coordinator, source, section, original, translated, language, authority, now=None):
    if language != 'es': raise ValueError('Only reviewed Spanish translations are currently supported.')
    for value,label in [(source,'source'),(section,'section'),(original,'original text'),(translated,'reviewed translation'),(authority,'translation reviewer')]:required(value,label)
    if len(translated)>65536: raise ValueError('Translation is too large.')
    with coordinator.db:
        coordinator.db.execute('BEGIN IMMEDIATE')
        row=coordinator.db.execute("SELECT content FROM knowledge WHERE source=? AND section=? AND audience='volunteer'",(source,section)).fetchone()
        if not row or row[0]!=original or coordinator._source_retired(source):
            raise ValueError('Translation must match the current participant-visible source exactly.')
        key='translation:'+digest([source,section,original,language])
        payload={'source':source,'section':section,'original':original,'translated':translated,'language':language,'authority':authority}
        coordinator.db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(key,json.dumps(payload)))
        coordinator.log('translation_reviewed',digest(key),{'authority':authority,'source':source},stamp(now))
    return {'registered':True,'language':language}


def evidence(coordinator, question, address, on=None, now=None):
    row=coordinator.db.execute('SELECT payload FROM contact_preferences WHERE address=?',(address.casefold(),)).fetchone()
    preferences=json.loads(row[0]) if row else {}
    language=preferences.get('language','en');format=preferences.get('format','plain_text')
    result=coordinator.retrieve(question,audience='volunteer',on=on,now=now)
    for item in result['evidence']:
        item['original']=item['content']
        item['translation_status']='original_language'
        if language=='es':
            key='translation:'+digest([item['source'],item['section'],item['content'],language])
            translation=coordinator.db.execute('SELECT value FROM settings WHERE key=?',(key,)).fetchone()
            if translation:
                item['translated']=json.loads(translation[0])['translated'];item['translation_status']='reviewed'
            else:item['translation_status']='unavailable_original_retained'
        if format=='structured_plain_text':
            item['presentation']={'source':item['source'],'section':item['section'],
                                  'original_conditions':item['original'],'reviewed_translation':item.get('translated')}
    return dict(result,language=language,format=format,
                limits='Reviewed evidence only; original source, conditions, dates and gaps remain authoritative. Automatic translated outbound notices are not supported.')
