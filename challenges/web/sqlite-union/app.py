"""Souvenir shop search API -- source handout (backed by shop.db).

The product search builds SQL by string concatenation. The exact query is
reproduced below. A snapshot of the live database (shop.db) is shipped with
this handout.
"""

import sqlite3

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/api/search")
def search():
    q = request.args.get("q", "")
    db = sqlite3.connect("shop.db")
    # Vulnerable: user input concatenated straight into the query.
    query = "SELECT id, name, price FROM products WHERE name LIKE '%" + q + "%'"
    rows = db.execute(query).fetchall()
    db.close()
    return jsonify(results=[{"id": r[0], "name": r[1], "price": r[2]} for r in rows])


if __name__ == "__main__":
    app.run(port=8080)
