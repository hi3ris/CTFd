# ctf-race-the-coupon:latest
FROM python:3.12-slim

# --- unprivileged runtime user -------------------------------------------
RUN useradd --create-home --uid 10001 shop

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py flag.py ./
RUN chown -R shop:shop /app

USER shop
EXPOSE 8080

# IMPORTANT: a single worker with multiple threads.
#   -w 1        : one process, so the in-memory wallet state is shared and the
#                 check-then-decrement race is actually reachable and coherent.
#   --threads N : real concurrency inside that worker (the GIL is released
#                 across the processing sleep), which is what the exploit needs.
# Do NOT scale to multiple workers: each worker would hold its own wallet and
# reads/writes would land on different copies.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", \
     "--workers", "1", "--threads", "16", "--worker-class", "gthread", \
     "--timeout", "120", "app:app"]
