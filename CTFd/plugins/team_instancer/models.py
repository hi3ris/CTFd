"""Data models for the team instancer.

- TeamInstanceChallenge: the challenge type. Subclasses Challenges directly and
  carries its own dynamic-scoring columns (so we keep decay scoring WITHOUT
  coupling to the dynamic_challenges table) plus the two docker fields. We reuse
  only the decay math from dynamic_challenges, never its table.
- TeamInstance: one live instance, keyed on the TEAM (account_id), not the user.
- FrpPort: the pool of public ports, one row per port, allocated atomically.
"""

import datetime

from CTFd.models import Challenges, db


class TeamInstanceChallenge(Challenges):
    __tablename__ = "team_instance_challenge"
    __mapper_args__ = {"polymorphic_identity": "team_instance"}
    id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), primary_key=True
    )
    # Dynamic-scoring columns (same semantics as dynamic_challenges).
    initial = db.Column(db.Integer, default=0)
    minimum = db.Column(db.Integer, default=0)
    decay = db.Column(db.Integer, default=0)
    function = db.Column(db.String(32), default="logarithmic")
    # Instancer columns.
    docker_image = db.Column(db.String(160))   # e.g. "ctf-web-jwt-cousin:latest"
    internal_port = db.Column(db.Integer)      # port the container listens on

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        # value tracks initial like dynamic challenges do.
        if "initial" in kwargs:
            self.value = kwargs["initial"]


class TeamInstance(db.Model):
    __tablename__ = "team_instance"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, index=True, nullable=False)  # team id in teams mode
    challenge_id = db.Column(
        db.Integer, db.ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False
    )
    container_id = db.Column(db.String(64))
    port = db.Column(db.Integer)
    network_name = db.Column(db.String(128))
    proxy_name = db.Column(db.String(64))
    status = db.Column(db.String(16), default="spawning")  # spawning|running|stopped|error
    # Python-side defaults (NOT server_default): SQLAlchemy populates them on
    # INSERT on every backend. A server_default is DDL-only and would be emitted
    # by create_all (SQLite dev) but not by the Alembic migration (MariaDB prod),
    # leaving start_time NULL in prod so instances would never be reaped.
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    # start_time anchors the TTL; renew pushes it forward.
    start_time = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    renew_count = db.Column(db.Integer, default=0)

    # One instance per (team, challenge): blocks double-spawn at the DB level.
    __table_args__ = (
        db.UniqueConstraint("account_id", "challenge_id", name="uq_team_challenge"),
    )


class FrpPort(db.Model):
    __tablename__ = "frp_port"
    port = db.Column(db.Integer, primary_key=True)
    instance_id = db.Column(db.Integer, db.ForeignKey("team_instance.id"), nullable=True)
    account_id = db.Column(db.Integer, nullable=True)
    challenge_id = db.Column(db.Integer, nullable=True)
