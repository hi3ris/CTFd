# ctf-adversarial-gate:latest
#
# Build:  docker build -t ctf-adversarial-gate:latest .
# Run:    docker run --rm -p 8080:8080 -e TEAM_SECRET="<per-team-secret>" \
#             ctf-adversarial-gate:latest
#
# TEAM_SECRET (derives the per-team flag) is injected at instance-creation
# time. No secret is baked into the image. The classifier weights and the
# DENIED badge are common to all teams -- the artifact IS the challenge; only
# the emitted flag is per-team.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HANDOUT_DIR=/srv/handout

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# server code + model + target (never the author tooling or reference solution)
COPY app/app.py app/gatemodel.py app/gatepkt.py ./
COPY app/weights.npz app/denied_badge.npy ./
# team-common artifacts served from the live instance under /assets/
COPY handout/ ./handout/

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

# CPU-only NumPy inference; a couple of threads is plenty for a 32x32 CNN.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "60", "app:app"]
