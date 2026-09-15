terraform {
  required_providers {
    random   = { source = "hashicorp/random" }
    local    = { source = "hashicorp/local" }
    external = { source = "hashicorp/external" }
  }
}

# Dev-only. In real life the backend + provider creds would not be committed.
provider "aws" {
  region     = "eu-west-1"
  access_key = "AKIAFAKEACCESSKEY123"
  secret_key = "AKIAFAKE0000EXAMPLE/notThePassphraseAtAll"
}

resource "random_password" "vault" {
  length  = 22
  special = false
}

# The encryptor. encrypt.py is committed alongside this config (see its header
# for the exact blob format) and is invoked with the generated passphrase.
data "external" "encrypt" {
  program = ["python3", "${path.module}/encrypt.py"]
  query = {
    passphrase = random_password.vault.result
    infile     = "secret.txt" # local plaintext, not committed
  }
}

# encrypt.py writes ${path.module}/vault.enc directly and returns its path.
resource "local_file" "vault_marker" {
  filename = "${path.module}/.vault-written"
  content  = data.external.encrypt.result["path"]
}
