output "phase" {
  description = "Phase courante du CTF."
  value       = var.phase
}

output "front_public_ip" {
  description = "IP publique du front. Vide hors evenement."
  value       = local.front_enabled ? aws_eip.front[0].public_ip : ""
}

output "front_private_ip" {
  description = "IP privee du front (utilisee par frpc sur l'arena)."
  value       = local.front_enabled ? aws_instance.front[0].private_ip : ""
}

output "arena_public_ip" {
  description = "IP publique de l'arena (SSH admin uniquement)."
  value       = local.arena_enabled ? aws_instance.arena[0].public_ip : ""
}

output "arena_private_ip" {
  description = "IP privee de l'arena."
  value       = local.arena_enabled ? aws_instance.arena[0].private_ip : ""
}

output "ai_public_ip" {
  description = "IP publique du noeud IA (SSH admin uniquement)."
  value       = local.ai_enabled ? aws_instance.ai[0].public_ip : ""
}

output "ai_private_ip" {
  description = "IP privee du noeud IA."
  value       = local.ai_enabled ? aws_instance.ai[0].private_ip : ""
}

output "ctf_url" {
  description = "URL du CTF pendant l'evenement."
  value = local.front_enabled ? (
    var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_eip.front[0].public_ip}"
  ) : ""
}

output "archive_bucket" {
  description = "Bucket S3 des archives et des sauvegardes."
  value       = aws_s3_bucket.archive.id
}

output "archive_site_url" {
  description = "Site statique des editions passees, en ligne toute l'annee."
  value       = "http://${aws_s3_bucket_website_configuration.archive.website_endpoint}"
}

output "cost_note" {
  description = "Ce qui est facture en ce moment, et le rappel qui va avec."
  value = var.phase == "off" ? join("", [
    "Phase off : aucune instance EC2. Seules les archives S3 sont facturees ",
    "(~0.50 USD/mois).",
    ]) : join("", [
    "Phase ${var.phase} : ~",
    format("%.2f", local.hourly_estimate_usd[var.phase]),
    " USD/h, soit ~",
    format("%.0f", local.hourly_estimate_usd[var.phase] * 24),
    " USD par jour. Lancez `make season-down` des la fin de la phase.",
  ])
}
