# ctf-web-shipyard-sqli2:latest  (SERVED CHALLENGE STUB -- implement the vuln before shipping)
FROM python:3.12-alpine

RUN apk add --no-cache su-exec

WORKDIR /app
COPY app/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app/ /app/
COPY flag.py /app/flag.py
RUN chmod +x /app/entrypoint.sh
RUN adduser -D -H appuser

EXPOSE 8080

# Dev default only; the instancier injects FLAG / CHALLENGE_SECRET in production.
ENV TEAM_SECRET=devsecret

ENTRYPOINT ["/app/entrypoint.sh"]
