# ---------------------------------------------------------------------------
# Groupes de securite
# ---------------------------------------------------------------------------

resource "aws_security_group" "front" {
  name        = "${var.project_name}-front"
  description = "CTFd front : web public, SSH admin, tunnel frp depuis l'arena"
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-front" }
}

resource "aws_vpc_security_group_ingress_rule" "front_ssh" {
  for_each = toset(var.admin_cidrs)

  security_group_id = aws_security_group.front.id
  description       = "SSH admin"
  cidr_ipv4         = each.value
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "front_http" {
  for_each = toset(var.player_cidrs)

  security_group_id = aws_security_group.front.id
  description       = "HTTP (redirige vers HTTPS, et challenge ACME Let's Encrypt)"
  cidr_ipv4         = each.value
  from_port         = 80
  to_port           = 80
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "front_https" {
  for_each = toset(var.player_cidrs)

  security_group_id = aws_security_group.front.id
  description       = "HTTPS"
  cidr_ipv4         = each.value
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
}

# Les instances de challenge tournent sur l'arena mais sont exposees au public
# par le front via frp : c'est donc le front qui ouvre la plage de ports.
resource "aws_vpc_security_group_ingress_rule" "front_whale_ports" {
  for_each = toset(var.player_cidrs)

  security_group_id = aws_security_group.front.id
  description       = "Instances de challenge par equipe (frp)"
  cidr_ipv4         = each.value
  from_port         = var.whale_port_range_start
  to_port           = var.whale_port_range_end
  ip_protocol       = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "front_all" {
  security_group_id = aws_security_group.front.id
  description       = "Sortie libre"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# ---------------------------------------------------------------------------

resource "aws_security_group" "arena" {
  name        = "${var.project_name}-arena"
  description = "Swarm des challenges + Ollama. Aucune entree publique."
  vpc_id      = aws_vpc.main.id

  tags = { Name = "${var.project_name}-arena" }
}

resource "aws_vpc_security_group_ingress_rule" "arena_ssh_admin" {
  for_each = toset(var.admin_cidrs)

  security_group_id = aws_security_group.arena.id
  description       = "SSH admin"
  cidr_ipv4         = each.value
  from_port         = 22
  to_port           = 22
  ip_protocol       = "tcp"
}

# CTFd pilote le Docker de l'arena via SSH (docker context ssh://), pas via
# un port 2375/2376 expose : moins de surface d'attaque, pas de PKI a gerer.
resource "aws_vpc_security_group_ingress_rule" "arena_ssh_from_front" {
  security_group_id            = aws_security_group.arena.id
  description                  = "API Docker via SSH depuis le front"
  referenced_security_group_id = aws_security_group.front.id
  from_port                    = 22
  to_port                      = 22
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_ingress_rule" "arena_ollama_from_front" {
  security_group_id            = aws_security_group.arena.id
  description                  = "Ollama : challenges IA appeles par le plugin CTFd"
  referenced_security_group_id = aws_security_group.front.id
  from_port                    = 11434
  to_port                      = 11434
  ip_protocol                  = "tcp"
}

resource "aws_vpc_security_group_egress_rule" "arena_all" {
  security_group_id = aws_security_group.arena.id
  description       = "Sortie libre (pull des images, frpc vers le front)"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "-1"
}

# L'arena ouvre le tunnel vers le front : c'est une connexion sortante cote
# arena, donc c'est le front qui doit accepter l'entree sur le port frps.
resource "aws_vpc_security_group_ingress_rule" "front_frp_bind" {
  security_group_id            = aws_security_group.front.id
  description                  = "Tunnel frp depuis l'arena"
  referenced_security_group_id = aws_security_group.arena.id
  from_port                    = 7000
  to_port                      = 7000
  ip_protocol                  = "tcp"
}
