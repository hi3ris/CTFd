"""Queue Poison — a worker that deserializes queue messages into live objects.

Design (served challenge, per-team flag):

  * ``/enqueue`` accepts a JSON message. Messages name their class in
    ``__class__`` and the worker instantiates it from a registry — with no
    allow-list. A normal message is ``{"__class__":"Notification","text":...}``.
  * The registry still contains a dangerous ``FlagDumper`` gadget (a debugging
    class left in) whose construction reads the instance secret. An unknown
    ``__class__`` returns an error that leaks the registry, so the gadget is
    discoverable.
  * ``/work`` drains the queue, building each message's object and appending its
    ``render()`` to the results log; ``/results`` returns that log.

Intended path: probe with a bogus ``__class__`` to leak the registry → enqueue
``{"__class__":"FlagDumper"}`` → run the worker → read the results.

The flag at ``/flag.txt`` is served by no route; it only reaches the attacker as
the rendered output of the gadget the poisoned message instantiated.
"""
import os

from flask import Flask, jsonify, request

app = Flask(__name__)

QUEUE = []
RESULTS = []


def _flag():
    try:
        with open("/flag.txt", encoding="utf-8") as fh:
            return fh.read().strip()
    except OSError:
        return "NCTF{flag-unavailable-in-dev}"


class Notification:
    def __init__(self, text="", **_):
        self.text = text

    def render(self):
        return f"notify: {self.text}"


class FlagDumper:
    # Debugging gadget left in the registry: reads the instance secret on build.
    def __init__(self, **_):
        self.output = _flag()

    def render(self):
        return self.output


REGISTRY = {"Notification": Notification, "FlagDumper": FlagDumper}


def deserialize(msg):
    cls = REGISTRY[msg["__class__"]]
    kwargs = {k: v for k, v in msg.items() if k != "__class__"}
    return cls(**kwargs)


@app.route("/")
def index():
    return jsonify(
        {
            "service": "queue-poison",
            "enqueue": "POST /enqueue {__class__, ...}",
            "work": "POST /work  -> drains the queue",
            "results": "GET /results",
        }
    )


@app.route("/enqueue", methods=["POST"])
def enqueue():
    msg = request.get_json(silent=True) or {}
    cls = msg.get("__class__", "Notification")
    if cls not in REGISTRY:
        return (
            jsonify({"error": "unknown message class", "registry": sorted(REGISTRY)}),
            400,
        )
    msg["__class__"] = cls
    QUEUE.append(msg)
    return jsonify({"queued": True, "depth": len(QUEUE)})


@app.route("/work", methods=["POST"])
def work():
    n = 0
    while QUEUE:
        msg = QUEUE.pop(0)
        obj = deserialize(msg)  # no allow-list: any registry class is built
        RESULTS.append(obj.render())
        n += 1
    return jsonify({"processed": n})


@app.route("/results")
def results():
    return jsonify({"results": RESULTS})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "8080")))
