# ---------------------------------------------------------------------------
# DNS
#
# L'IP publique du front change a chaque cycle season-down / phase-up, puisque
# l'instance et son EIP sont detruites. Sans automatisation, quelqu'un doit
# repointer le domaine a la main le matin du 23 octobre, et attendre le TTL.
#
# On automatise donc l'enregistrement, avec un TTL court pendant l'evenement.
# Si vous ne gerez pas le domaine dans Route53, laissez route53_zone_id vide :
# Terraform n'y touchera pas et le README decrit alors la manoeuvre manuelle.
# ---------------------------------------------------------------------------

variable "route53_zone_id" {
  description = <<-EOT
    Zone hebergee Route53 contenant domain_name. Vide = pas de gestion DNS par
    Terraform (il faudra repointer le domaine a la main a chaque phase).
  EOT
  type        = string
  default     = ""
}

locals {
  manage_dns = var.route53_zone_id != "" && var.domain_name != ""
}

resource "aws_route53_record" "ctf" {
  count = local.manage_dns && local.front_enabled ? 1 : 0

  zone_id = var.route53_zone_id
  name    = var.domain_name
  type    = "A"

  # 60 s : entre deux phases l'IP change, et un TTL long laisserait des joueurs
  # sur une adresse morte le matin de l'epreuve.
  ttl     = 60
  records = [aws_eip.front[0].public_ip]
}
