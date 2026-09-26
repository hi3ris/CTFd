# ctf-poisoned-pipeline:latest -- MiniCI shared build runner (per-team instance).
#
# Untrusted pipelines run on the runner; the deploy secret (the flag) is injected
# only into deploy-stage steps and masked from logs. The challenge is exfil'ing
# it past the (literal-only) mask.
FROM python:3.11-slim

RUN mkdir -p /opt/ci
COPY src/minici.py /opt/ci/minici.py
COPY flag.py /opt/ci/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/ci/minici.py

WORKDIR /opt/ci
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
