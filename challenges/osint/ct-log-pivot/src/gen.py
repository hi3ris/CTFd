"""Generate a CT-log pivot bundle.

Artifacts:
  * cert.tg.zone       public BIND zone (the hosts the operator admits to)
  * whois.txt          registrar / nameserver record (flavour + confirms apex)
  * ct-log.txt         certificate-transparency style issuance log with SANs
  * resolver_cache.txt cached DNS answers incl. TXT records

Pivot: a CT-log entry lists a `cert.tg` subdomain that is NOT in the public zone
(a shadow host exposed only by a leaked certificate). That host's TXT record in
the resolver cache is base32 that decodes to the flag. Decoy CT entries include
other domains, a wildcard, and an expired cert; decoy TXT records decode to junk.

Run:  python3 gen.py
"""

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

FLAG = "NCTF{ct_log_san_leaked_shadow_subdomain}"
SHADOW = "mgmt-legacy.cert.tg"


def b32(s: bytes) -> str:
    return base64.b32encode(s).decode()


ZONE = """$ORIGIN cert.tg.
$TTL 3600
@       IN SOA  ns1.cert.tg. hostmaster.cert.tg. (
                2025061001 7200 3600 1209600 3600 )
@       IN NS   ns1.cert.tg.
@       IN NS   ns2.cert.tg.
@       IN A    41.207.180.10
www     IN A    41.207.180.10
blog    IN A    41.207.180.12
mail    IN A    41.207.180.20
@       IN MX   10 mail.cert.tg.
ns1     IN A    41.207.180.2
ns2     IN A    41.207.180.3
vpn     IN A    41.207.180.30
portail IN CNAME www.cert.tg.
@       IN TXT  "v=spf1 mx -all"
"""

WHOIS = """Domain Name: CERT.TG
Registry Domain ID: TG-2019-CERT
Registrar: NIC Togo
Updated Date: 2025-06-10T09:12:00Z
Creation Date: 2019-04-01T00:00:00Z
Name Server: NS1.CERT.TG
Name Server: NS2.CERT.TG
Registrant Organization: Agence Nationale de Cybersecurite
Registrant Country: TG
DNSSEC: unsigned
"""

# CT log: not_before | status | issuer | serial | SANs(comma)
CT_ROWS = [
    ("2024-11-02", "valid", "R3/LetsEncrypt", "03a1", "www.cert.tg,cert.tg"),
    ("2024-11-02", "valid", "R3/LetsEncrypt", "03a2", "blog.cert.tg"),
    ("2025-01-15", "valid", "E1/LetsEncrypt", "0510", "mail.cert.tg"),
    ("2025-02-01", "valid", "GTS/Google", "77ff", "vpn.cert.tg"),
    # noise: a different domain entirely
    ("2025-02-03", "valid", "GTS/Google", "8801", "www.togocom.tg,togocom.tg"),
    # decoy: wildcard reveals no specific label
    ("2025-03-10", "valid", "R3/LetsEncrypt", "0912", "*.cert.tg"),
    # decoy: expired cert for a host that IS public
    ("2023-05-01", "expired", "R3/LetsEncrypt", "0044", "portail.cert.tg"),
    # THE PIVOT: valid cert for a host absent from the zone
    ("2025-05-22", "valid", "R3/LetsEncrypt", "0aa0", "mgmt-legacy.cert.tg"),
    # more noise
    ("2025-06-01", "valid", "E1/LetsEncrypt", "0b12", "status.togocom.tg"),
]

# resolver cache lines: host  TTL  CLASS  TYPE  DATA
CACHE_ROWS = [
    ("www.cert.tg.", "A", "41.207.180.10"),
    ("blog.cert.tg.", "A", "41.207.180.12"),
    ("mail.cert.tg.", "A", "41.207.180.20"),
    ("cert.tg.", "TXT", '"v=spf1 mx -all"'),
    # decoy TXT that decodes to junk
    ("_dmarc.cert.tg.", "TXT", f'"nctf-b32={b32(b"not-the-flag-decoy-01")}"'),
    ("vpn.cert.tg.", "TXT", f'"nctf-b32={b32(b"maintenance-window-ok")}"'),
    # the shadow host: A + the real flag TXT
    (SHADOW + ".", "A", "41.207.180.99"),
    (SHADOW + ".", "TXT", f'"nctf-b32={b32(FLAG.encode())}"'),
]


def main() -> None:
    with open(os.path.join(ROOT, "cert.tg.zone"), "w") as fh:
        fh.write(ZONE)
    with open(os.path.join(ROOT, "whois.txt"), "w") as fh:
        fh.write(WHOIS)
    with open(os.path.join(ROOT, "ct-log.txt"), "w") as fh:
        fh.write("# not_before | status | issuer | serial | sans\n")
        for row in CT_ROWS:
            fh.write(" | ".join(row) + "\n")
    with open(os.path.join(ROOT, "resolver_cache.txt"), "w") as fh:
        fh.write("; host  TYPE  DATA\n")
        for host, typ, data in CACHE_ROWS:
            fh.write(f"{host}\t3600\tIN\t{typ}\t{data}\n")
    print("wrote cert.tg.zone, whois.txt, ct-log.txt, resolver_cache.txt")


if __name__ == "__main__":
    main()
