# ctf-koth-throne:latest -- shared King-of-the-Hill "hill" service.
#
# NOT a per-team instance: this is ONE container the whole event attacks. Deploy
# it as an arena service and point the CTFd `koth` plugin at it via KOTH_HILLS.
# The flag/identity model is per-team but lives in CTFd, not here: the hill only
# stores whatever opaque token was last claimed with a valid signature.
FROM python:3.11-slim

COPY app.py /opt/throne/app.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/throne/app.py

EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
