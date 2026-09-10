# ---------------------------------------------------------------------------
# Noeud IA : Ollama sur GPU, pour les challenges de type prompt injection.
#
# Pourquoi une machine dediee avec GPU plutot que de faire tourner Ollama sur
# l'arena : en preselection, ~300 joueurs peuvent discuter avec le modele en
# meme temps. Sur CPU, un modele 8B sert quelques tokens par seconde et
# s'effondre des la dizaine de requetes paralleles. Le GPU T4 d'une
# g4dn.xlarge absorbe la charge pour ~0.60 USD/h, soit ~29 USD pour 48 h.
#
# ATTENTION : sur un compte AWS neuf, le quota "Running On-Demand G and VT
# instances" est souvent a 0. La demande d'augmentation peut prendre plusieurs
# jours ouvres. A verifier des maintenant : `make check-gpu-quota`.
# ---------------------------------------------------------------------------

resource "aws_instance" "ai" {
  count = local.ai_enabled ? 1 : 0

  ami                    = data.aws_ami.ubuntu_x86.id
  instance_type          = local.current.ai
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ai.id]
  key_name               = aws_key_pair.admin.key_name

  root_block_device {
    volume_type = "gp3"
    # Les pilotes NVIDIA/CUDA et les poids du modele occupent une place
    # significative : 60 Go evite toute mauvaise surprise le jour J.
    volume_size           = 60
    encrypted             = true
    delete_on_termination = true
  }

  user_data = templatefile("${path.module}/templates/ai-userdata.sh.tftpl", {
    ollama_model = var.ollama_model
  })

  metadata_options {
    http_tokens = "required"
  }

  tags = { Name = "${var.project_name}-ai" }

  lifecycle {
    ignore_changes = [ami]
  }
}
