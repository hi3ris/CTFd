#!/usr/bin/env bash
# Contrôle de la délégation DNS de ctf.tg au niveau du TLD .tg.
#
# Contexte (2026-09-25) : deux des serveurs du TLD .tg (ns1.nic.tg, tld.cafe.tg)
# hébergent encore une vieille copie de la zone ctf.tg (SOA ns1.gouv.tg, serial
# 2024061000, aucun A pour l'apex, www -> ctftogo.ctfd.io) et y répondent en
# AUTORITAIRE au lieu de renvoyer la délégation vers Cloudflare. Résultat : ~1
# résolution non cachée sur 4 échoue dans le monde, et presque toutes chez les
# résolveurs togolais (qui préfèrent les serveurs nationaux).
#
# Ce script interroge CHAQUE serveur du TLD sans récursion et vérifie qu'il
# renvoie bien la délégation Cloudflare. Sortie non nulle tant que la zone
# périmée est servie quelque part. À rejouer après la correction par nic.tg,
# et dans la check-list d'avant ouverture.
#
# Usage : deploy/scripts/dns-delegation-check.sh [domaine] (défaut ctf.tg)
# Dépendances : python3 (aucune lib externe), réseau UDP/53 sortant.
set -euo pipefail
DOMAIN="${1:-ctf.tg}"
EXPECTED_NS="${EXPECTED_NS:-hal.ns.cloudflare.com wally.ns.cloudflare.com}"

python3 - "$DOMAIN" "$EXPECTED_NS" <<'EOF'
import socket, struct, sys, random

domain, expected = sys.argv[1], set(sys.argv[2].split())
tld = domain.rsplit(".", 1)[-1]

def qname(n):
    return b"".join(struct.pack("B", len(l)) + l.encode() for l in n.rstrip(".").split(".")) + b"\x00"

def build(name, qtype, rd):
    ident = random.randint(0, 65535)
    flags = 0x0100 if rd else 0x0000
    return struct.pack(">HHHHHH", ident, flags, 1, 0, 0, 0) + qname(name) + struct.pack(">HH", qtype, 1)

def read_name(msg, off):
    labels, jumped, end = [], False, None
    while True:
        l = msg[off]
        if l & 0xC0 == 0xC0:
            ptr = struct.unpack(">H", msg[off:off+2])[0] & 0x3FFF
            if not jumped: end = off + 2
            off, jumped = ptr, True
            continue
        off += 1
        if l == 0:
            break
        labels.append(msg[off:off+l].decode(errors="replace")); off += l
    return ".".join(labels), (end if jumped else off)

def parse(msg):
    ident, flags, qd, an, ns, ar = struct.unpack(">HHHHHH", msg[:12])
    off = 12
    for _ in range(qd):
        _, off = read_name(msg, off); off += 4
    recs = []
    for _ in range(an + ns + ar):
        name, off = read_name(msg, off)
        rtype, rclass, ttl, rdlen = struct.unpack(">HHIH", msg[off:off+10]); off += 10
        rdata = msg[off:off+rdlen]
        val = None
        if rtype in (2, 5, 6):
            val, _ = read_name(msg, off)
        elif rtype == 1 and rdlen == 4:
            val = ".".join(str(b) for b in rdata)
        recs.append((name, rtype, val))
        off += rdlen
    aa = bool(flags & 0x0400)
    return aa, recs[:an], recs[an:an+ns]

def query(server, name, qtype, rd):
    ip = socket.gethostbyname(server)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(4)
    try:
        s.sendto(build(name, qtype, rd), (ip, 53))
        data, _ = s.recvfrom(4096)
    finally:
        s.close()
    return parse(data)

# 1. liste des serveurs du TLD via un résolveur public
_, ans, _ = query("8.8.8.8", tld, 2, True)
tld_servers = sorted(v for _, t, v in ans if t == 2)
if not tld_servers:
    print(f"impossible d'obtenir les NS de .{tld}"); sys.exit(2)
print(f">> Serveurs du TLD .{tld} : {len(tld_servers)}")

bad = 0
for srv in tld_servers:
    try:
        aa, ans, auth = query(srv, domain, 1, False)
    except Exception as e:
        print(f"  {srv:<22} INJOIGNABLE ({e})"); continue
    ns_ref = {v.lower() for _, t, v in auth if t == 2}
    soa = [v for _, t, v in auth if t == 6]
    a = [v for _, t, v in ans if t == 1]
    if aa:
        bad += 1
        print(f"  {srv:<22} PERIME  : répond en AUTORITAIRE (SOA {soa[0] if soa else '?'}, A={a or 'aucun'}) au lieu de déléguer")
    elif ns_ref and ns_ref <= expected:
        print(f"  {srv:<22} OK      : délègue vers {' '.join(sorted(ns_ref))}")
    else:
        bad += 1
        print(f"  {srv:<22} SUSPECT : délégation {sorted(ns_ref) or 'vide'} (attendu {sorted(expected)})")

# 2. les anciens serveurs de la zone périmée (hors TLD) doivent NE PLUS répondre pour le domaine
for srv in ("ns1.gouv.tg", "ns2.gouv.tg"):
    try:
        aa, ans, auth = query(srv, domain, 6, False)
        soa = [v for _, t, v in ans if t == 6]
        if aa and soa:
            bad += 1
            print(f"  {srv:<22} PERIME  : sert encore la zone (SOA {soa[0]})")
        else:
            print(f"  {srv:<22} OK      : ne se déclare plus autoritaire")
    except Exception as e:
        print(f"  {srv:<22} injoignable ({e})")

print()
if bad:
    print(f"ECHEC : {bad} serveur(s) servent encore la zone périmée de {domain}. Demander à nic.tg de la supprimer.")
    sys.exit(1)
print(f"OK : tous les serveurs du TLD délèguent {domain} vers {' '.join(sorted(expected))}.")
EOF
