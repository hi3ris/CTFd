"""Generate a Maltego-style entity graph (nodes.csv + edges.csv).

The graph mixes VERIFIED links (shared email, phone, device, wallet, domain
registration, confirmed alias) with SPECULATIVE links (mentions, follows,
similar-name guesses). Pivoting only along verified links from the seed persona
reaches exactly one real PERSON node, whose `note` holds the flag. Speculative
links lead to decoy identities.

Run from anywhere:  python3 gen.py
Outputs nodes.csv and edges.csv one directory up (the challenge root).
"""

import csv
import os

FLAG = "NCTF{maltego_pivot_kossivi_agbeko_unmasked}"

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# id, type, label, value, note
NODES = [
    ("h_seed", "handle", "z3ro_237", "z3ro_237@x", "leaker of the CERT.tg dump"),
    ("e1", "email", "operateur", "z3r0.lome@protomail.tg", ""),
    ("h_cobra", "handle", "cobra_lome", "cobra_lome@social", ""),
    ("p1", "phone", "msisdn", "+22890114477", ""),
    ("dev1", "device", "imei", "356938035643809", ""),
    ("w1", "wallet", "btc", "1KossiViAgbeko9xQwErTyUiOpAsDfGh", ""),
    ("dom1", "domain", "registered", "mining-togo.tg", ""),
    (
        "person_true",
        "person",
        "identity",
        "Kossivi Agbeko",
        FLAG,
    ),
    # --- decoy cluster (reachable only via speculative edges) ---
    ("h_ghost", "handle", "ghost228", "ghost228@social", ""),
    (
        "person_decoy1",
        "person",
        "identity",
        "Yao Mensah",
        "NCTF{wrong_pivot_speculative_link}",
    ),
    ("person_decoy2", "person", "identity", "Ama Dede", "not the operator"),
    ("e2", "email", "personal", "yao.mensah@webmail.tg", ""),
    # --- unrelated noise ---
    ("h_noise1", "handle", "lome_foot", "lome_foot@social", ""),
    ("dom_noise", "domain", "registered", "actu-togo.tg", ""),
    ("person_noise", "person", "identity", "Kodjo Ali", "journalist, unrelated"),
]

# src, dst, relation  (verified relations pivot; speculative ones do not)
VERIFIED = {
    "same_email",
    "same_phone",
    "same_device",
    "owns_wallet",
    "registered_by",
    "confirmed_aka",
}
EDGES = [
    ("h_seed", "e1", "same_email"),
    ("e1", "h_cobra", "same_email"),
    ("h_cobra", "p1", "same_phone"),
    ("p1", "dev1", "same_device"),
    ("dev1", "w1", "owns_wallet"),
    ("w1", "dom1", "registered_by"),
    ("dom1", "person_true", "confirmed_aka"),
    # speculative / decoy
    ("h_seed", "h_ghost", "mentions"),
    ("h_ghost", "person_decoy1", "similar_name"),
    ("h_ghost", "e2", "follows"),
    ("e2", "person_decoy1", "same_email"),
    ("h_cobra", "person_decoy2", "similar_name"),
    ("p1", "person_decoy2", "mentions"),
    # noise
    ("h_noise1", "dom_noise", "mentions"),
    ("dom_noise", "person_noise", "registered_by"),
    ("h_noise1", "person_noise", "follows"),
]


def main() -> None:
    with open(os.path.join(ROOT, "nodes.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "type", "label", "value", "note"])
        w.writerows(NODES)

    with open(os.path.join(ROOT, "edges.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["src", "dst", "relation"])
        w.writerows(EDGES)

    print("wrote nodes.csv and edges.csv")
    print("verified relations:", sorted(VERIFIED))


if __name__ == "__main__":
    main()
