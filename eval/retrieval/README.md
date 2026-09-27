# Retrieval and grounding baseline

Run `python eval/retrieval/run.py --answers eval/retrieval/answers.json` to reproduce
retrieval and scoring against the committed fictional corpus. Food-bank, arts and
board contexts each have literal, paraphrased, absent, conflicting and private
questions. Each organization uses a separate temporary database.

On 2026-09-26 the real `plow/z-ai/glm-5.2` runtime answered all 15 committed evidence
packets from candidate `a077b50`. The prompt prohibited external knowledge/tools,
required source IDs, abstention on missing evidence, and both sides of conflicts.
The committed answers are the model output, manually inspected against the evidence;
private raw run metadata is retained outside the repository.

- Retrieval passed 12/15 cases. All three paraphrases failed; among nine answerable
  cases, six retrieved the needed sources. FTS stemming does not resolve synonyms.
- The model preserved all three explicit conflicts and qualified legacy metadata.
- All nine cited source IDs (across six substantive answers) existed in the supplied
  evidence. It abstained on nine cases, including the three retrieval misses.
- Conditional answer/abstention checks passed 15/15. This is **not** 100% useful-answer
  accuracy: the three paraphrase failures remain failures of the complete system.
- No private canary appeared in retrieved evidence or generated answers.

The automatic scorer checks required facts, explicit conflict/abstention flags and
citation IDs; it does not prove arbitrary semantic entailment. The corpus is small
and clean. The measured 3/3 synonym failures justify a separately scoped hybrid or
semantic retrieval experiment, evaluated on this held-out structure plus a larger
corpus before adoption. Do not weaken privacy filtering or invent an answer to
improve apparent recall. Extraction limitations are reported separately in #35.
