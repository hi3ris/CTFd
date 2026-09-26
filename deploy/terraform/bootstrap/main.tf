# ---------------------------------------------------------------------------
# Bootstrap de l'etat distant Terraform (S3 + verrou DynamoDB).
#
# Probleme d'oeuf et de poule : le backend S3 de la config principale a besoin
# d'un bucket et d'une table de verrou qui existent AVANT `terraform init`. On
# ne peut donc pas les creer dans la config principale elle-meme. Ce mini-module
# les cree avec un etat LOCAL (le seul etat local qui subsiste), une fois.
#
# A lancer une seule fois, avant d'activer le backend distant :
#     cd deploy/terraform/bootstrap
#     terraform init && terraform apply
# ou, depuis deploy/ :  make state-bootstrap
#
# Ensuite : copier ../backend.tf.example -> ../backend.tf, renseigner
# ../backend.hcl, et `make init` (Terraform proposera de migrer l'etat local
# existant vers S3 : repondre oui).
#
# Pourquoi : un `make phase-preselection` a moitie applique le matin du 23,
# avec un etat local sur le portable de l'operateur, n'est pas reprenable
# ailleurs et peut etre corrompu si deux personnes appliquent. L'etat distant
# verrouille rend l'apply reprenable et empeche les applies concurrents.
# ---------------------------------------------------------------------------

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

variable "aws_region" {
  description = "Region AWS. Doit etre la meme que la config principale."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefixe applique au nom des ressources. Doit etre le meme que la config principale."
  type        = string
  default     = "ctf"
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project   = var.project_name
      ManagedBy = "terraform-bootstrap"
    }
  }
}

data "aws_caller_identity" "current" {}

# Bucket qui porte l'etat Terraform. Versionne (on peut revenir a un etat
# anterieur si un apply corrompt le fichier), chiffre, ferme au public.
resource "aws_s3_bucket" "state" {
  bucket = "${var.project_name}-tfstate-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "${var.project_name}-tfstate" }

  lifecycle {
    # Detruire ce bucket = perdre l'etat de toute l'infra. Jamais par accident.
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "state" {
  bucket = aws_s3_bucket.state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "state" {
  bucket = aws_s3_bucket.state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Nettoie les versions non courantes pour ne pas accumuler indefiniment.
resource "aws_s3_bucket_lifecycle_configuration" "state" {
  bucket = aws_s3_bucket.state.id

  rule {
    id     = "expire-noncurrent-state"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

# Table de verrou : empeche deux `terraform apply` concurrents de se marcher
# dessus (le matin du jour J, deux operateurs). Cle sur "LockID", facturation
# a la demande (cout quasi nul hors apply).
resource "aws_dynamodb_table" "lock" {
  name         = "${var.project_name}-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = { Name = "${var.project_name}-tflock" }
}

output "state_bucket" {
  description = "Nom du bucket d'etat -- a reporter dans backend.hcl (key: bucket)."
  value       = aws_s3_bucket.state.id
}

output "lock_table" {
  description = "Nom de la table de verrou -- a reporter dans backend.hcl (key: dynamodb_table)."
  value       = aws_dynamodb_table.lock.name
}

output "region" {
  description = "Region -- a reporter dans backend.hcl (key: region)."
  value       = var.aws_region
}

output "backend_hcl" {
  description = "Contenu pret a coller dans ../backend.hcl."
  value       = <<-EOT
    bucket         = "${aws_s3_bucket.state.id}"
    key            = "ctf/terraform.tfstate"
    region         = "${var.aws_region}"
    dynamodb_table = "${aws_dynamodb_table.lock.name}"
    encrypt        = true
  EOT
}
