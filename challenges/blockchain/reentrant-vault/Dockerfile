# ctf-reentrant-vault:latest -- per-team EVM reentrancy challenge.
#
# Runs a local anvil (Foundry) node plus a launcher/oracle. The launcher deploys
# and seeds the vulnerable Vault, funds a player account, proxies JSON-RPC on the
# single exposed port, and reveals the team flag only once the vault is drained.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates git \
 && rm -rf /var/lib/apt/lists/*

# Foundry (anvil). Pin via foundryup; anvil provides the JSON-RPC node.
RUN curl -L https://foundry.paradigm.xyz | bash \
 && /root/.foundry/bin/foundryup
ENV PATH="/root/.foundry/bin:${PATH}"

# Python EVM tooling; bake the solc binary into the image so no download is
# needed at runtime.
RUN pip install --no-cache-dir "web3==8.0.0" "py-solc-x" "eth-account" \
 && python -c "import solcx; solcx.install_solc('0.8.20')"

RUN mkdir -p /opt/chall/src /opt/chall/contracts
COPY src/oracle.py /opt/chall/src/oracle.py
COPY flag.py /opt/chall/src/flag.py
COPY contracts/Vault.sol /opt/chall/contracts/Vault.sol
COPY entrypoint.sh /opt/entrypoint.sh
RUN chmod 0755 /opt/entrypoint.sh

WORKDIR /opt/chall
EXPOSE 8080
ENV PORT=8080 RPC_INTERNAL=http://127.0.0.1:8545 \
    VAULT_SOL=/opt/chall/contracts/Vault.sol
ENTRYPOINT ["/opt/entrypoint.sh"]
