# ctf-koth-reseau-fortune:latest -- shared King-of-the-Hill "hill" service.
#
# NOT a per-team instance: ONE container the whole event shares. Deploy it as an
# arena service and point the CTFd `koth` plugin at it via KOTH_HILLS. Teams join
# with their KotH token; the hill crowns whichever network is richest via /king.
FROM python:3.11-slim

RUN pip install --no-cache-dir Flask==3.0.3 Werkzeug==3.0.3

COPY app.py /opt/reseau/app.py
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh /opt/reseau/app.py

EXPOSE 8080
ENV PORT=8080
ENTRYPOINT ["/opt/entrypoint.sh"]
