# ---------------------------------------------------------------------------
# Arena : Docker Swarm des instances de challenge + Ollama.
# N'existe que si arena_enabled = true. Le reste de l'annee, ces ressources
# ne sont pas creees du tout : facture 0 EUR.
# ---------------------------------------------------------------------------

data "aws_ami" "ubuntu_x86" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

resource "aws_instance" "arena" {
  count = local.arena_enabled ? 1 : 0

  ami                    = data.aws_ami.ubuntu_x86.id
  instance_type          = local.current.arena
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.arena.id]
  key_name               = aws_key_pair.admin.key_name

  dynamic "instance_market_options" {
    for_each = var.arena_use_spot ? [1] : []

    content {
      market_type = "spot"

      spot_options {
        # "stop" plutot que "terminate" : si AWS reprend l'instance, le disque
        # (images des challenges, modeles Ollama) n'est pas perdu.
        instance_interruption_behavior = "stop"
        spot_instance_type             = "persistent"
      }
    }
  }

  root_block_device {
    volume_type           = "gp3"
    volume_size           = 100
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/templates/arena-userdata.sh.tftpl", {
    front_private_ip = aws_instance.front[0].private_ip
    frp_bind_port    = 7000
    port_range_start = var.whale_port_range_start
    port_range_end   = var.whale_port_range_end
  })

  metadata_options {
    http_tokens = "required"
  }

  tags = { Name = "${var.project_name}-arena" }

  lifecycle {
    ignore_changes = [ami]
  }
}
