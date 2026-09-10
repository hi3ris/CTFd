"""
The DECOY: a fake link-local cloud-metadata mirror at 169.254.169.254:80.

It answers the classic IMDS paths and returns *plausible but useless* creds.
This is the single allowed decoy for the challenge. It is refutable from the
challenge's own evidence in minutes:

  * The public robots.txt calls it a "mirror" whose "creds here are stale".
  * The challenge description states the flag is ONLY emitted by the internal
    admin ping -- never by metadata creds.
  * The returned AccessKeyId is a documentation-style placeholder and the
    token/expiry are already in the past.

No flag material is present here.
"""
from flask import Flask, Response

app = Flask(__name__)

_INDENT = "        "

FAKE_ROLE = "s3-thumbnail-reader"

# Intentionally stale / placeholder. Expiration is in the past; the AccessKeyId
# uses the AWS-documentation prefix. These will never authenticate anywhere.
FAKE_CREDS = (
    "{\n"
    '  "Code" : "Success",\n'
    '  "LastUpdated" : "2019-04-01T09:15:00Z",\n'
    '  "Type" : "AWS-HMAC",\n'
    '  "AccessKeyId" : "AKIAIOSFODNN7EXAMPLE",\n'
    '  "SecretAccessKey" : "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",\n'
    '  "Token" : "IQoJb3JpZ2luX2VjEXAMPLESTALEMIRRORTOKENdGhpcyBpcyBub3QgYSBmbGFn",\n'
    '  "Expiration" : "2019-04-01T15:15:00Z"\n'
    "}\n"
)


@app.route("/")
def root():
    return Response("1.0\nlatest\n", mimetype="text/plain")


@app.route("/latest/meta-data/")
def meta_index():
    return Response(
        "ami-id\nhostname\niam/\ninstance-id\nlocal-ipv4\nmac\n",
        mimetype="text/plain",
    )


@app.route("/latest/meta-data/instance-id")
def instance_id():
    return Response("i-0abcd1234mirror00", mimetype="text/plain")


@app.route("/latest/meta-data/iam/")
def iam_index():
    return Response("security-credentials/\n", mimetype="text/plain")


@app.route("/latest/meta-data/iam/security-credentials/")
def cred_index():
    return Response(FAKE_ROLE + "\n", mimetype="text/plain")


@app.route("/latest/meta-data/iam/security-credentials/<role>")
def creds(role):
    if role != FAKE_ROLE:
        return Response("Not Found\n", status=404, mimetype="text/plain")
    return Response(FAKE_CREDS, mimetype="text/plain")


@app.errorhandler(404)
def nf(_e):
    return Response("Not Found\n", status=404, mimetype="text/plain")
