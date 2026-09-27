"""Verified provider replies for reserved shift offers, RSVPs and waitlists."""
import json
from .core import digest, stamp, iso
from .providers import authenticated_account, ProviderError
from .replies import VerifiedReply


def _check_account(coordinator, account):
    policy = coordinator.autonomy()
    if (not policy or not policy['enabled'] or not isinstance(account.sender, str)
            or account.sender.casefold() != policy['sender'].casefold()):
        raise ProviderError('signup_account_outside_remit')
    return policy


def _reserve(coordinator, task_id, person, policy, now):
    assignment_id = digest([task_id, person['id']])[:24]
    if coordinator.db.execute('SELECT 1 FROM assignments WHERE id=?', (assignment_id,)).fetchone():
        return None
    coordinator.db.execute("INSERT INTO assignments VALUES(?,?,?,'offered',?)",
                           (assignment_id, task_id, person['id'], digest(policy)))
    coordinator.log('shift_offer_reserved', task_id, {'assignment_id': assignment_id}, now)
    return assignment_id


def promote_waitlist(coordinator, task_id, now):
    """Reserve one eligible replacement inside the caller's write transaction."""
    db = coordinator.db
    policy = coordinator.autonomy()
    row = db.execute("SELECT payload FROM tasks WHERE id=? AND status='open'", (task_id,)).fetchone()
    if not row or not policy or not policy['enabled']:
        return None
    task = json.loads(row[0])
    if (not task.get('signup_required') or task['category'] not in policy['allowed_task_categories']
            or stamp(task['start']) <= now):
        return None
    if db.execute("SELECT 1 FROM assignments WHERE task_id=? AND status IN ('assigned','offered')", (task_id,)).fetchone():
        return None
    wait_key = 'waitlist:' + task_id
    row = db.execute('SELECT value FROM settings WHERE key=?', (wait_key,)).fetchone()
    waiting = json.loads(row[0]) if row else []
    for candidate_id in waiting:
        row = db.execute('SELECT payload FROM volunteers WHERE id=?', (candidate_id,)).fetchone()
        if not row:
            continue
        candidate = json.loads(row[0])
        if coordinator._eligible(candidate, task, policy):
            assignment_id = _reserve(coordinator, task_id, candidate, policy, now)
            if assignment_id:
                waiting.remove(candidate_id)
                db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)', (wait_key, json.dumps(waiting)))
                return assignment_id
    return None


def apply(coordinator, provider, message_id, now=None):
    account=authenticated_account(provider)
    _check_account(coordinator, account)
    reply=provider.verified_reply(message_id)
    if not isinstance(reply,VerifiedReply) or not reply.authenticated or reply.message_id!=message_id or not reply.evidence:
        raise ProviderError('unverified_signup_identity')
    if reply.action not in ('signup','accept_offer','decline_offer'):raise ProviderError('unsupported_signup_action')
    now=stamp(now);db=coordinator.db;receipt='shift-reply:'+digest([account.provider,account.account_id,message_id])
    with db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT 1 FROM settings WHERE key=?',(receipt,)).fetchone():raise ProviderError('reply_already_processed')
        # Recheck after the provider read in case the owner changed the remit.
        policy=_check_account(coordinator, account)
        people=[json.loads(r[0]) for r in db.execute('SELECT payload FROM volunteers')]
        actors=[v for v in people if v['email'].casefold()==reply.sender.casefold()]
        if len(actors)!=1:raise ProviderError('sender_not_unique_in_roster')
        actor=actors[0]
        row=db.execute("SELECT payload FROM tasks WHERE id=? AND status='open'",(reply.target_id,)).fetchone()
        if not row:raise ProviderError('slot_not_open')
        task=json.loads(row[0]);task_id=task['id']
        if not task.get('signup_required') or task['category'] not in policy['allowed_task_categories'] or stamp(task['start'])<=now:
            raise ProviderError('slot_outside_signup_scope')
        wait_key='waitlist:'+task_id
        row=db.execute('SELECT value FROM settings WHERE key=?',(wait_key,)).fetchone()
        waiting=json.loads(row[0]) if row else []
        reservation=db.execute("SELECT * FROM assignments WHERE task_id=? AND status IN ('assigned','offered')",(task_id,)).fetchone()
        if reply.action=='signup':
            if not coordinator._eligible(actor,task,policy):raise ProviderError('signup_ineligible_or_no_personal_capacity')
            if reservation and reservation['volunteer_id']==actor['id']:raise ProviderError('already_reserved_or_confirmed')
            if db.execute('SELECT 1 FROM assignments WHERE task_id=? AND volunteer_id=?',(task_id,actor['id'])).fetchone():raise ProviderError('previous_slot_outcome_requires_owner_review')
            if reservation:
                if actor['id'] not in waiting:waiting.append(actor['id'])
                state='waitlisted'
            else:_reserve(coordinator,task_id,actor,policy,now);state='offered'
        elif reply.action=='accept_offer':
            if not reservation or reservation['volunteer_id']!=actor['id'] or reservation['status']!='offered':raise ProviderError('offer_not_owned_by_sender')
            if not coordinator._eligible(actor,task,policy):raise ProviderError('offer_no_longer_eligible')
            db.execute("UPDATE assignments SET status='assigned',policy_hash=? WHERE id=?",(digest(policy),reservation['id']))
            coordinator.log('shift_rsvp_confirmed',task_id,{'assignment_id':reservation['id'],'evidence':reply.evidence},now)
            state='confirmed'
        else:
            if reservation and reservation['volunteer_id']==actor['id']:
                db.execute("UPDATE assignments SET status='declined' WHERE id=?",(reservation['id'],))
                coordinator._retire_pending(task_id)
            elif actor['id'] in waiting:waiting.remove(actor['id'])
            else:raise ProviderError('no_owned_offer_or_waitlist_entry')
            state='declined'
        db.execute('INSERT OR REPLACE INTO settings VALUES(?,?)',(wait_key,json.dumps(waiting)))
        if reply.action == 'decline_offer':
            promote_waitlist(coordinator, task_id, now)
        db.execute('INSERT INTO settings VALUES(?,?)',(receipt,json.dumps({'status':state,'at':iso(now),'evidence':reply.evidence})))
    return {'status':state,'task_id':reply.target_id,'scope':'Offer/RSVP state only; no provider message or attendance is asserted.'}
