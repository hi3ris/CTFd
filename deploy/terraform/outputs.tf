output "front_public_ip" {
  description = "IP publique fixe du front CTFd. C'est elle qui doit etre dans le DNS."
  value       = aws_eip.front.public_ip
}

output "front_ssh" {
  description = "Commande de connexion au front."
  value       = "ssh ubuntu@${aws_eip.front.public_ip}"
}

output "front_private_ip" {
  description = "IP privee du front (utilisee par frpc sur l'arena)."
  value       = aws_instance.front.private_ip
}

output "arena_private_ip" {
  description = "IP privee de l'arena. Vide si l'arena est eteinte."
  value       = var.arena_enabled ? aws_instance.arena[0].private_ip : ""
}

output "arena_public_ip" {
  description = "IP publique de l'arena (SSH admin uniquement). Vide si l'arena est eteinte."
  value       = var.arena_enabled ? aws_instance.arena[0].public_ip : ""
}

output "ctf_url" {
  description = "URL du CTF."
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "http://${aws_eip.front.public_ip}"
}

output "cost_note" {
  description = "Rappel de ce qui est facture en ce moment."
  value = var.arena_enabled ? join("", [
    "ARENA ALLUMEE (${var.arena_instance_type}). ",
    "Pensez a `make event-down` des la fin de l'evenement.",
    ]) : join("", [
    "Arena eteinte. Seul le front (${var.front_instance_type}) ",
    "+ son disque + son IPv4 sont factures.",
  ])
}
