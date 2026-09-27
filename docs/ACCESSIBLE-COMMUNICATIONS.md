# Accessible evidence and reviewed translations

Supported preferences are English (`en`) or reviewed Spanish (`es`), with
`plain_text` or `structured_plain_text` presentation. The supported output is
source-grounded participant evidence. Automatic reminder and task emails remain
English plain text; a recipient requesting another format or language is
explicitly deferred rather than sent an unsupported message.

An owner records a verified participant preference through
`set-contact-preferences`, or a provider supplies it through the authenticated
`apply_verified_reply` boundary. Settings survive restart. An unverified sender
cannot change them; setting preferences never reverses an opt-out. Other language
or format codes are rejected without overwriting the previous supported settings.

The participant credential issuer may bind an `address` to the server-side
credential record. The existing `/v1/evidence` endpoint then loads that person's
saved preferences from the credential's organization. Request JSON accepts only
`question` and optional `on`; clients cannot choose an address, language override,
organization, audience or action. Credentials without an address retain the
existing default evidence response. This change adds no participant write endpoint.

## Reading the response

The returned `text` is linear plain text with source citations, update dates,
review warnings and verbatim original conditions. Structured mode labels each
source separately. English and Spanish labels are provided; no color, table,
icon or visual layout is necessary to understand the content.

Spanish excerpts appear only when an owner-identified reviewer has registered a
translation against the exact current participant-visible source section. Original
text and its source citation remain alongside the translation. A source edit
invalidates the matching translation. A missing translation is stated explicitly
and the original is retained; withdrawal or private visibility excludes the source
entirely. The renderer does not generate translations or certify a reviewer's
linguistic accuracy. It does not turn an excerpt into an asserted current rule:
unknown review metadata, stale sources and retrieval gaps retain warnings.

## Issue #39 acceptance evidence

| Criterion | Evidence |
| --- | --- |
| Persist verified language and format preferences | `test_verified_preferences_persist_and_spoof_cannot_change_them` applies the verified-reply contract, reopens SQLite, and rejects an unauthenticated change. Owner-attested preferences and consent remain covered by contact-preference tests. |
| Preserve conditions and link the original source in translated answers | The four-case English/Spanish × plain/structured matrix preserves complete role, date, time and cancellation conditions plus the original source URL. Spanish also includes the reviewed translation. |
| Explicitly handle unsupported languages/formats | Unsupported French/audio preferences are rejected without replacing saved preferences. Missing or invalidated translations retain the original with an explicit explanation. Unsupported automatic notices remain deferred. |
| Validate representative accessible messages and locales | Tests cover both formats, English/Los Angeles and Spanish/Madrid preferences, translated and untranslated excerpts, empty results, withdrawn/private sources, and a real local HTTP request through the authenticated participant endpoint. |

The HTTP tests also reject caller-supplied addresses and language overrides and
exclude other organizations' and coordinator-private content. Existing timezone
tests cover participant quiet hours across daylight-saving changes.

These are executable library and local endpoint acceptance tests with fictional
data. They do not claim live email sender verification, professional translation
review, assistive-technology certification, or multilingual outbound delivery.
Live provider identity acceptance remains tracked in #29, separately from #39's
supported accessible evidence and preference behavior.
