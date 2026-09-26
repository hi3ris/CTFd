#!/usr/bin/env python3
"""Envoie un e-mail de test via le SMTP configuré (variables MAIL_* de l'env).

À lancer SUR LE FRONT (là où le SMTP peut sortir), **avant** de passer
`verify_emails=ON` : prouver que la chaîne d'envoi marche évite un lockout
massif à l'inscription (avec la vérification ON, un joueur ne peut rien faire
tant qu'il n'a pas reçu et cliqué le mail de confirmation).

    make mail-test TO=toi@exemple.com
    # ou directement, en exportant les MAIL_* de front/.env :
    #   TO=toi@exemple.com python3 deploy/scripts/mail-test.py

Lit : MAIL_SERVER, MAIL_PORT (587), MAIL_USERNAME, MAIL_PASSWORD, MAIL_TLS,
MAIL_SSL, MAILFROM_ADDR (ou MAILSENDER_ADDR). Ne révèle jamais le mot de passe.
Sortie 0 si l'envoi part, 1 sinon.
"""
import os
import smtplib
import ssl
import sys
from email.message import EmailMessage


def _env(*names, default=""):
    for n in names:
        v = os.environ.get(n)
        if v not in (None, ""):
            return v
    return default


def _truthy(v):
    return str(v or "").strip().lower() in ("1", "true", "yes", "on")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    to = argv[0] if argv else os.environ.get("TO", "")
    if not to:
        print("usage: mail-test.py <destinataire>  (ou TO=...)", file=sys.stderr)
        return 2

    server = _env("MAIL_SERVER")
    if not server:
        print("[FAIL] MAIL_SERVER vide -> SMTP non configuré", file=sys.stderr)
        return 1
    try:
        port = int(_env("MAIL_PORT", default="587"))
    except ValueError:
        print("[FAIL] MAIL_PORT invalide", file=sys.stderr)
        return 1
    user = _env("MAIL_USERNAME")
    password = _env("MAIL_PASSWORD")
    use_ssl = _truthy(_env("MAIL_SSL"))
    use_tls = _truthy(_env("MAIL_TLS", default="true"))
    sender = _env(
        "MAILFROM_ADDR", "MAILSENDER_ADDR", default=user or ("noreply@" + server)
    )

    msg = EmailMessage()
    msg["Subject"] = "NCTF26 — test SMTP"
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(
        "Test d'envoi NCTF26.\n\nSi tu lis ceci (boîte de réception, pas spam), "
        "la chaîne SMTP marche et tu peux passer verify_emails=ON.\n"
    )

    ctx = ssl.create_default_context()
    try:
        if use_ssl:
            smtp = smtplib.SMTP_SSL(server, port, timeout=20, context=ctx)
        else:
            smtp = smtplib.SMTP(server, port, timeout=20)
            if use_tls:
                smtp.starttls(context=ctx)
        try:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
        finally:
            smtp.quit()
    except Exception as e:  # noqa: BLE001
        print("[FAIL] envoi impossible via %s:%d : %r" % (server, port, e))
        print(
            "       vérifie MAIL_USERNAME/MAIL_PASSWORD (clé SMTP), le port, "
            "et que le front peut sortir en SMTP."
        )
        return 1

    print(
        "[OK] e-mail de test envoyé à %s via %s:%d — vérifie la boîte ET le spam."
        % (to, server, port)
    )
    print("     Deliverabilité en spam = DKIM/SPF/DMARC à finir avant d'ouvrir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
