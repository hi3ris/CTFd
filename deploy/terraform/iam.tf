# ---------------------------------------------------------------------------
# Role IAM de l'arena : lecture seule des images de challenge dans le bucket
# d'archives.
#
# Le perimetre est volontairement etroit. Un challenge pwn donne par
# construction l'execution de code sur l'arena ; si ce role pouvait ecrire dans
# le bucket ou lire le prefixe backups/, un joueur pourrait respectivement
# empoisonner les images de l'edition suivante et exfiltrer la base de donnees.
# ---------------------------------------------------------------------------

resource "aws_iam_role" "arena" {
  name = "${var.project_name}-arena"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "arena_images" {
  name = "read-challenge-images"
  role = aws_iam_role.arena.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "ListImagesPrefixOnly"
        Effect   = "Allow"
        Action   = "s3:ListBucket"
        Resource = aws_s3_bucket.archive.arn
        Condition = {
          StringLike = { "s3:prefix" = ["images/*", "images"] }
        }
      },
      {
        Sid      = "ReadImagesOnly"
        Effect   = "Allow"
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.archive.arn}/images/*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "arena" {
  name = "${var.project_name}-arena"
  role = aws_iam_role.arena.name
}
