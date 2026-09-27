FROM public.ecr.aws/e1h7x4a2/plow-cloud-agents:base-1e73c82c4b3e0c9f76935bc0cc45061875b34aee@sha256:5f8ef7c3762b037420cd8843a767a7ab7e2433b1c8319e7cfe2ad1bdef5dee8a
USER root
COPY good_company/ /opt/good-company/good_company/
COPY LICENSE /opt/good-company/LICENSE
COPY third_party/ /opt/good-company/third_party/
COPY scripts/start_runtime.py /opt/good-company/start_runtime.py
COPY scripts/runtime_preflight.py /opt/good-company/runtime_preflight.py
COPY scripts/good-company /usr/local/bin/good-company
COPY scripts/good-company-cycle /usr/local/bin/good-company-cycle
RUN chmod 0755 /usr/local/bin/good-company /usr/local/bin/good-company-cycle && mkdir -p /var/lib/good-company && chown node:node /var/lib/good-company
COPY prompt/AGENTS.md /opt/plow/prompt/AGENTS.md
COPY skills/ /opt/plow/skills/
COPY examples/ /opt/good-company/examples/
ENV PYTHONPATH=/opt/good-company GOOD_COMPANY_DB=/var/lib/good-company/state.sqlite
ENV AGENT_ID=good-company AGENT_NAME="Good Company"
ENV AGENT_BLURB="An executive assistant for busy community leaders: knows the supplied rules, coordinates volunteers, and handles routine reminders."
LABEL org.opencontainers.image.title="Good Company" org.opencontainers.image.licenses="MIT"
USER node
CMD ["python3", "/opt/good-company/start_runtime.py"]
