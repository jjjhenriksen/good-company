# Resource booking pilot decision (#46)

Decision: no-go pending an actual pilot inventory and booking authority. Fictional
examples do not establish who owns equipment or permits reservations. No module,
booking API, external write or implementation issue is enabled by this draft.

Required pilot evidence: named inventory owner and authoritative system; resource
identifiers and quantity; availability and setup/transport windows; exclusive versus
shared use; who can approve reservations; conflict priority; cancellation and damage
handoff; access and retention owner. Record source references rather than copying
private inventory or participant details into this public-ready document.

Bounded MVP if justified: read authoritative availability, propose one resource
reservation, commit only within explicit booking authority, retain the returned
reservation ID, and cancel exactly that reservation. Exclude purchases, payments,
asset depreciation and maintenance decisions. Acceptance must demonstrate two
simultaneous requests cannot double-book and cancellation releases only owned
capacity. Create implementation issues only after those choices are supplied.
