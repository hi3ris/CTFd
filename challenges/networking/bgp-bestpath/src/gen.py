#!/usr/bin/env python3
"""Generate a simplified BGP RIB (Adj-RIB-In) as JSON.

For each destination prefix there are several candidate routes. The best route
is chosen with a trimmed BGP decision process:

    1. highest LOCAL_PREF
    2. shortest AS_PATH length
    3. lowest ORIGIN code (igp=0, egp=1, incomplete=2)
    4. lowest MED
    5. lowest peer_id (tie-break)

Each route carries a one-character ``label``. Reading the labels of the winning
routes, ordered by prefix, spells the flag. Losing (decoy) routes carry other
characters.
"""

import ipaddress
import json
import os
import random

FLAG = "NCTF{bgp_bestpath_localpref_beats_aspath_len}"

ORIGIN = {"igp": 0, "egp": 1, "incomplete": 2}


def rank(route):
    return (
        -route["local_pref"],
        len(route["as_path"]),
        ORIGIN[route["origin"]],
        route["med"],
        route["peer_id"],
    )


def best(routes):
    return min(routes, key=rank)


def main():
    rng = random.Random(0xB6B00B)
    prefixes = []
    base = ipaddress.ip_network("198.51.100.0/24")
    # /28 subnets, one per flag character
    subs = list(base.subnets(new_prefix=30))
    for i in range(len(FLAG)):
        prefixes.append(str(subs[i]))

    entries = []
    decoy = list("qwzx98765mnbv")
    for i, pfx in enumerate(prefixes):
        win_char = FLAG[i]
        n = rng.randint(2, 4)
        routes = []
        # winner: pick a decision dimension that makes it win
        strategy = i % 3
        if strategy == 0:
            # winner has highest local_pref
            winner = {
                "peer_id": rng.randint(10, 99),
                "local_pref": 300,
                "as_path": [
                    rng.randint(64500, 65000) for _ in range(rng.randint(2, 5))
                ],
                "origin": rng.choice(["igp", "egp", "incomplete"]),
                "med": rng.randint(0, 200),
                "label": win_char,
            }
            others = []
            for _ in range(n - 1):
                others.append(
                    {
                        "peer_id": rng.randint(10, 99),
                        "local_pref": rng.choice([100, 150, 200]),
                        "as_path": [
                            rng.randint(64500, 65000) for _ in range(rng.randint(1, 3))
                        ],
                        "origin": "igp",
                        "med": rng.randint(0, 50),
                        "label": decoy[rng.randrange(len(decoy))],
                    }
                )
        elif strategy == 1:
            # all equal local_pref; winner has shortest as_path
            lp = 200
            winner = {
                "peer_id": rng.randint(10, 99),
                "local_pref": lp,
                "as_path": [rng.randint(64500, 65000) for _ in range(2)],
                "origin": rng.choice(["igp", "egp"]),
                "med": rng.randint(0, 200),
                "label": win_char,
            }
            others = []
            for _ in range(n - 1):
                others.append(
                    {
                        "peer_id": rng.randint(10, 99),
                        "local_pref": lp,
                        "as_path": [
                            rng.randint(64500, 65000) for _ in range(rng.randint(4, 7))
                        ],
                        "origin": "igp",
                        "med": rng.randint(0, 50),
                        "label": decoy[rng.randrange(len(decoy))],
                    }
                )
        else:
            # equal local_pref and as_path length; winner has lowest MED
            lp = 150
            plen = 3
            winner = {
                "peer_id": rng.randint(50, 99),
                "local_pref": lp,
                "as_path": [rng.randint(64500, 65000) for _ in range(plen)],
                "origin": "igp",
                "med": 5,
                "label": win_char,
            }
            others = []
            for _ in range(n - 1):
                others.append(
                    {
                        "peer_id": rng.randint(10, 49),
                        "local_pref": lp,
                        "as_path": [rng.randint(64500, 65000) for _ in range(plen)],
                        "origin": "igp",
                        "med": rng.randint(80, 300),
                        "label": decoy[rng.randrange(len(decoy))],
                    }
                )

        routes = [winner] + others
        rng.shuffle(routes)
        assert best(routes)["label"] == win_char, (i, pfx)
        entries.append({"prefix": pfx, "routes": routes})

    rng.shuffle(entries)
    doc = {
        "decision": [
            "highest local_pref",
            "shortest as_path",
            "lowest origin (igp<egp<incomplete)",
            "lowest med",
            "lowest peer_id",
        ],
        "rib": entries,
    }
    here = os.path.dirname(os.path.abspath(__file__))
    dest = os.path.join(here, "..", "bgp_rib.json")
    with open(dest, "w") as f:
        json.dump(doc, f, indent=2)
        f.write("\n")
    print("wrote", os.path.normpath(dest), "prefixes=%d" % len(entries))


if __name__ == "__main__":
    main()
