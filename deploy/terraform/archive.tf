# ---------------------------------------------------------------------------
# Archives : la seule chose qui existe toute l'annee.
#
# Les comptes joueurs sont supprimes entre deux editions (nouvelles equipes,
# nouveaux participants), donc rien ne justifie de garder CTFd allume. On
# conserve uniquement, sur S3 :
#   - le site statique des editions passees (scoreboards figes, write-ups) ;
#   - les sauvegardes de la base, pour pouvoir reconstituer une edition.
#
# Cout : quelques dizaines de centimes par mois.
# ---------------------------------------------------------------------------

resource "aws_s3_bucket" "archive" {
  bucket = "${var.project_name}-archive-${data.aws_caller_identity.current.account_id}"

  tags = { Name = "${var.project_name}-archive" }

  lifecycle {
    # Ce bucket porte l'historique de toutes les editions : on ne le detruit
    # jamais par accident depuis Terraform.
    prevent_destroy = true
  }
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "archive" {
  bucket = aws_s3_bucket.archive.id

  block_public_acls       = true
  block_public_policy     = false
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket_versioning" "archive" {
  bucket = aws_s3_bucket.archive.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id

  # Les dumps de base sont volumineux et rarement relus : on les bascule en
  # stockage froid au bout d'un mois plutot que de les payer au tarif standard.
  rule {
    id     = "backups-to-glacier"
    status = "Enabled"

    filter {
      prefix = "backups/"
    }

    transition {
      days          = 30
      storage_class = "GLACIER_IR"
    }
  }

  rule {
    id     = "expire-old-versions"
    status = "Enabled"

    filter {}

    noncurrent_version_expiration {
      noncurrent_days = 90
    }
  }
}

resource "aws_s3_bucket_website_configuration" "archive" {
  bucket = aws_s3_bucket.archive.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Seul le prefixe site/ est lisible publiquement. Les sauvegardes de base
# restent privees.
resource "aws_s3_bucket_policy" "archive_site" {
  bucket = aws_s3_bucket.archive.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadSiteOnly"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.archive.arn}/site/*"
    }]
  })

  depends_on = [aws_s3_bucket_public_access_block.archive]
}
