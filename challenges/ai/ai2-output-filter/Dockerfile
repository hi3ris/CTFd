# ctf-ai2-output-filter:latest
#
# Build:
#   docker build -t ctf-ai2-output-filter:latest .
# Run (TEAM_SECRET is injected per team by the platform at instance creation):
#   docker run --rm -e TEAM_SECRET=<team-secret> -p 8080:8080 \
#       ctf-ai2-output-filter:latest
#
# No secret is baked into the image. The flag and the guarded SIGMA value are
# both derived from TEAM_SECRET at runtime and never written to disk.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PORT=8080

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ /app/

# Non-root.
RUN adduser --disabled-password --gecos "" --uid 10001 ctf \
    && chown -R ctf:ctf /app
USER ctf

EXPOSE 8080

# 2 workers is plenty; the app is stateless and CPU-light.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:8080", "--timeout", "30", "app:app"]
