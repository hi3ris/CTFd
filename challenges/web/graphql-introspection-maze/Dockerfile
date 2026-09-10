# ctf-graphql-introspection-maze:latest
#
# Build:  docker build -t ctf-graphql-introspection-maze:latest .
# Run:    docker run --rm -p 8080:8080 \
#             -e TEAM_SECRET="<per-team-secret>" \
#             ctf-graphql-introspection-maze:latest
#
# TEAM_SECRET is injected at instance-creation time. No secret is baked in.
#
# IMPORTANT: run with a SINGLE gunicorn worker. Per-session clearance (the
# privileged EFFECT that gates the flag) lives in an in-process dict; multiple
# workers would not share it. The workload is a per-team instance, so one
# worker with threads is plenty.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/app.py .

RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "8", "--timeout", "30", "app:app"]
