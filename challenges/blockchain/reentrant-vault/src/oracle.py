#!/usr/bin/env python3
"""Reentrant Vault -- per-team launcher / flag oracle.

On startup this connects to the local anvil node, compiles and deploys the
vulnerable Vault, seeds it with honest deposits, and funds a fresh player
account. It then serves ONE HTTP port that:

  * proxies JSON-RPC (POST /) to the internal anvil node, so the player points
    web3/foundry at this URL to deploy their exploit and send transactions;
  * GET /info  -> the RPC url, chain id, funded player private key, Vault address;
  * GET /flag  -> the team flag IFF the vault has been drained to 0 (the effect
    that constitutes solving), else the current vault balance.

The flag is never on-chain and never in the RPC; only /flag reveals it, and only
once the vault balance is zero. The chain-building and solved-check helpers are
kept provider-agnostic so they can be exercised against an in-process
eth-tester chain as well as a real anvil node.
"""
import json
import os
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import solcx
from eth_account import Account
from web3 import Web3

import flag as flagmod

PORT = int(os.environ.get("PORT", "8080"))
RPC_INTERNAL = os.environ.get("RPC_INTERNAL", "http://127.0.0.1:8545")
SOLC_VERSION = "0.8.20"
VAULT_SOL = os.environ.get(
    "VAULT_SOL",
    os.path.join(os.path.dirname(__file__), "..", "contracts", "Vault.sol"),
)
FLAG = flagmod.get_flag()


def compile_vault():
    with open(VAULT_SOL) as fh:
        src = fh.read()
    out = solcx.compile_source(
        src, output_values=["abi", "bin"], solc_version=SOLC_VERSION
    )
    key = next(k for k in out if k.endswith(":Vault"))
    return out[key]["abi"], out[key]["bin"]


def setup_chain(w3, seed=(3, 2), player_funds=10):
    """Deploy + seed the Vault and fund a fresh player. Returns (vault_addr, abi,
    player_account). Provider-agnostic (anvil or eth-tester)."""
    deployer = w3.eth.accounts[0]
    abi, bytecode = compile_vault()
    c = w3.eth.contract(abi=abi, bytecode=bytecode)
    rcpt = w3.eth.wait_for_transaction_receipt(
        c.constructor().transact({"from": deployer})
    )
    vault = w3.eth.contract(address=rcpt.contractAddress, abi=abi)
    for user, amount in zip(w3.eth.accounts[1:3], seed):
        w3.eth.wait_for_transaction_receipt(
            vault.functions.deposit().transact(
                {"from": user, "value": w3.to_wei(amount, "ether")}
            )
        )
    player = Account.create()
    w3.eth.wait_for_transaction_receipt(
        w3.eth.send_transaction(
            {
                "from": deployer,
                "to": player.address,
                "value": w3.to_wei(player_funds, "ether"),
            }
        )
    )
    return vault.address, abi, player


def is_solved(w3, vault_addr):
    return w3.eth.get_balance(vault_addr) == 0


# --------------------------------------------------------------------------
# HTTP: JSON-RPC proxy + info + flag
# --------------------------------------------------------------------------
def _make_handler(state):
    class Handler(BaseHTTPRequestHandler):
        server_version = "vault-launcher/1.0"

        def _json(self, code, obj):
            data = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            path = urlparse(self.path).path
            if path in ("/info", "/"):
                self._json(
                    200,
                    {
                        "rpc": "POST this same URL (JSON-RPC is proxied to anvil)",
                        "chainId": state["chain_id"],
                        "vault": state["vault"],
                        "player_address": state["player"].address,
                        "player_private_key": state["player"].key.hex(),
                        "hint": "drain the Vault to 0, then GET /flag",
                    },
                )
                return
            if path == "/flag":
                w3 = Web3(Web3.HTTPProvider(RPC_INTERNAL))
                if is_solved(w3, state["vault"]):
                    self._json(200, {"flag": FLAG})
                else:
                    self._json(
                        200,
                        {
                            "solved": False,
                            "vault_balance_wei": w3.eth.get_balance(state["vault"]),
                        },
                    )
                return
            self._json(404, {"error": "not found"})

        def do_POST(self):
            # Proxy JSON-RPC to the internal anvil node.
            length = int(self.headers.get("Content-Length", "0") or "0")
            body = self.rfile.read(length) if length else b""
            try:
                req = urllib.request.Request(
                    RPC_INTERNAL,
                    data=body,
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as r:  # nosec B310
                    out = r.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)
            except Exception as e:  # noqa: BLE001
                self._json(502, {"error": "rpc proxy failed: {}".format(e)})

        def log_message(self, fmt, *args):
            pass

    return Handler


def main():
    solcx.set_solc_version(SOLC_VERSION)
    w3 = Web3(Web3.HTTPProvider(RPC_INTERNAL))
    vault_addr, _abi, player = setup_chain(w3)
    state = {
        "vault": vault_addr,
        "player": player,
        "chain_id": w3.eth.chain_id,
    }
    print("[oracle] vault deployed at {} (seeded)".format(vault_addr), flush=True)
    print("[oracle] player {} funded".format(player.address), flush=True)
    httpd = ThreadingHTTPServer(("0.0.0.0", PORT), _make_handler(state))  # nosec B104
    print("[oracle] launcher on 0.0.0.0:{}".format(PORT), flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
