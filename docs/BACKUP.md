# Private backup and restore

These helpers operate on an **offline private state directory**, not a public
artifact. Stop the gateway and its operational scheduler first. Confirm no other
process writes the directory; the `offline=True` argument is an operator assertion,
not process detection. Preserve the entire state directory so the reporter's
install identity, operating remit and provider histories travel together.

From a trusted Python operator session:

```python
from good_company.state_backup import backup_state, restore_state
backup_state('/private/stopped-state', '/private/backups/snapshot-001', offline=True)
restore_state('/private/backups/snapshot-001', '/private/recovered-state', offline=True)
```

Use actual private absolute paths outside Git repositories and public outputs.
The destination must not exist. Snapshots use SQLite's backup API and integrity
check, private file modes, and a checksum manifest. Restore validates all content
before atomically publishing the new directory. Existing state is never replaced.
Symlinks and special files are refused for explicit review; do not silently omit
linked identity data. Restore the verified directory as the stopped instance's
state volume, preserving its container uid/gid as required by deployment.

Before resuming, verify the install identity, standing remit and original provider
receipts, then enable exactly one scheduler. A restored accepted/uncertain claim
must never be replayed. Keep the prior directory until recovery is verified.
The fixture test proves ledger recovery; live base-image upgrade and scheduler
acceptance remain separate (#57). Backups may contain credentials and personal
data and must never enter Git, logs, PR attachments or public outputs.
