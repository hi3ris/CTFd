# ctf-model-inversion:latest
#
# Build:  docker build -t ctf-model-inversion:latest .
# Run:    docker run --rm -p 8080:8080 -e CHALLENGE_SECRET="<per-challenge-hex>" \
#             ctf-model-inversion:latest
#         # (or -e FLAG="NCTF{...}" -- the instancer injects one or both)
#
# The per-team instancer injects PER-CHALLENGE values at instance-creation time:
# FLAG (the exact flag string) and/or CHALLENGE_SECRET (per-challenge hex, whose
# first 24 chars are the flag body). No secret is baked into the image. The
# embedding E (and hence the similarity metric M = E^T E) is common to all teams
# -- the artifact IS the challenge; only the memorised record and the flag are
# per-team, both derived from CHALLENGE_SECRET at start-up (record in memory
# only, never on disk or served).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HANDOUT_DIR=/srv/handout

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# server code + model builder (never the reference solution)
COPY app/app.py app/model.py app/build_model.py ./
# team-common artifacts served from the live instance under /assets/
COPY handout/ ./handout/

# Build the team-common embedding deterministically AT IMAGE BUILD, so no
# pre-baked weights are trusted from the build context. Fixed seed => identical
# to the shipped handout/weights.npz.
RUN python build_model.py

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 8080

# CPU-only NumPy scoring; a couple of threads is plenty for a 24-d bilinear form.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "60", "app:app"]
