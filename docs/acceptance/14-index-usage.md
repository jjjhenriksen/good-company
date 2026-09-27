# Index identity and usage acceptance (#14)

Passed on 2026-09-27 UTC. The authenticated inherited client created
[Good Company](https://aiworthusing.com/agent-index/good-company), and a public
read-back confirmed the intended slug and owner. The first genuine report was
accepted with HTTP 200 for two day/model rows, totalling 1,881,898 tokens.

The deployment now sets `AGENT_ID=good-company`, enabling the inherited five-minute
reporter. Replacing the running image preserved the exact persistent Index state
and install identity. After restart, a fresh real GLM-5.2 setup run consumed
685,177 tokens. With no manual report after restart, the public Index total rose
by exactly that amount to 2,567,075 at the next periodic pass. This is observed
automatic reporting, not merely a saved timer or synthetic usage.

[`index-live.json`](../../eval/providers/index-live.json) preserves sanitized
registration, report, run and identity-hash evidence. The report contains only
day-by-model token counts; prompts, messages and credentials were not submitted.
The registration state remains private on the persistent volume.

Media, public source/image references and organizer admission are still #12/#15;
identity and usage acceptance does not imply those steps are complete.
