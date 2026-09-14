terraform {
  required_providers {
    random = { source = "hashicorp/random" }
    local  = { source = "hashicorp/local" }
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

# Writes the encrypted secrets blob using the generated passphrase.
resource "local_file" "vault" {
  filename       = "${path.module}/vault.enc"
  content_base64 = base64encode(data.external.encrypt.result["blob"])
}
