# ---------------------------------------------------------------------------
# Front CTFd : allume 365 jours/an, donc dimensionne au plus juste.
# ARM (Graviton) car l'image CTFd est construite depuis python:3.11-slim,
# qui est multi-arch : aucune adherence x86 cote front.
# ---------------------------------------------------------------------------

data "aws_ami" "ubuntu_arm64" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-arm64-server-*"]
  }
}

resource "aws_key_pair" "admin" {
  key_name   = "${var.project_name}-admin"
  public_key = var.ssh_public_key
}

resource "aws_instance" "front" {
  count = local.front_enabled ? 1 : 0

  ami                    = data.aws_ami.ubuntu_arm64.id
  instance_type          = local.current.front
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.front.id]
  key_name               = aws_key_pair.admin.key_name

  root_block_device {
    volume_type = "gp3"
    volume_size = 30
    encrypted   = true

    # Le front est detruit apres chaque edition : la persistance ne repose
    # pas sur ce disque mais sur les sauvegardes envoyees dans S3 par
    # `make season-down`.
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/templates/front-userdata.sh.tftpl", {
    frp_bind_port = 7000
  })

  # Un changement de user_data ne doit pas recreer le front (il porte la base).
  user_data_replace_on_change = false

  metadata_options {
    http_tokens = "required" # IMDSv2 obligatoire
  }

  tags = { Name = "${var.project_name}-front" }

  lifecycle {
    ignore_changes = [ami]
  }
}

# IP fixe : indispensable pour que le DNS du CTF pointe au meme endroit toute
# l'annee. Cout ~3.60 USD/mois (AWS facture toutes les IPv4 publiques depuis
# fevrier 2024, attachees ou non).
resource "aws_eip" "front" {
  count = local.front_enabled ? 1 : 0

  instance = aws_instance.front[0].id
  domain   = "vpc"

  tags = { Name = "${var.project_name}-front" }
}
