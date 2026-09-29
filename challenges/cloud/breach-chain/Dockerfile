# ctf-breach-chain:latest -- Kékéli Cloud "breach chain" (per-team instance).
#
# One container hosts the whole kill chain: a public app (SSRF + a
# credential-gated admin endpoint) and an internal IMDS-style metadata service
# bound to 127.0.0.1 that is only reachable through the SSRF.
FROM python:3.11-slim

RUN mkdir -p /opt/app
COPY src/app.py /opt/app/app.py
COPY flag.py /opt/app/flag.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/app/app.py

WORKDIR /opt/app
EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
