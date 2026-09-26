# ctf-padding-oracle-lite:latest
#
# Build:  docker build -t ctf-padding-oracle-lite:latest .
# Run:    docker run --rm -p 9007:9007 \
#             -e FLAG="NCTF{...}" \
#             ctf-padding-oracle-lite:latest
#   (or -e CHALLENGE_SECRET="<per-challenge-hex>" to derive the flag)
#
# The platform instancier injects per-challenge FLAG / CHALLENGE_SECRET at
# instance-creation time (no longer the team master secret). The AES key/IV and
# the session token are generated fresh inside the process on every start. No
# secret is baked into the image.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    BIND_HOST=0.0.0.0 \
    BIND_PORT=9007

WORKDIR /srv

COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY flag.py .
COPY app/server.py .

# non-root
RUN useradd --no-create-home --uid 10001 appuser
USER appuser

EXPOSE 9007

CMD ["python3", "server.py"]
