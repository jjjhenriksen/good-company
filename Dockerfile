FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-771198a9609dcef54d44843e7da5329c17fa51b4@sha256:f1e7c421b97a80f1bd17015f96daceb965f350a241f7edc7e4d856a0e3a6f8f5
USER root
COPY good_company/ /opt/good-company/good_company/
COPY LICENSE /opt/good-company/LICENSE
COPY third_party/ /opt/good-company/third_party/
COPY third_party/agent-index-client/agent_index_client.py /opt/plow/agent-index-client.py
COPY scripts/start_runtime.py /opt/good-company/start_runtime.py
COPY scripts/runtime_preflight.py /opt/good-company/runtime_preflight.py
COPY scripts/good-company /usr/local/bin/good-company
COPY scripts/good-company-cycle /usr/local/bin/good-company-cycle
COPY scripts/good-company-availability /usr/local/bin/good-company-availability
RUN chmod 0755 /usr/local/bin/good-company /usr/local/bin/good-company-cycle /usr/local/bin/good-company-availability && mkdir -p /var/lib/good-company && chown node:node /var/lib/good-company
COPY prompt/AGENTS.md /opt/plow/prompt/AGENTS.md
COPY skills/ /opt/plow/skills/
COPY examples/ /opt/good-company/examples/
ENV PYTHONPATH=/opt/good-company GOOD_COMPANY_DB=/var/lib/good-company/state.sqlite
ENV AGENT_ID=good-company AGENT_NAME="Good Company"
ENV AGENT_BLURB="An executive assistant for busy community leaders: knows the supplied rules, coordinates volunteers, and handles routine reminders."
LABEL org.opencontainers.image.title="Good Company" org.opencontainers.image.licenses="MIT"
USER node
CMD ["python3", "/opt/good-company/start_runtime.py"]
