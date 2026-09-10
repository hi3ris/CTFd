variable "aws_region" {
  description = "Region AWS. eu-west-3 (Paris) est le plus proche pour la France."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefixe applique au nom de toutes les ressources."
  type        = string
  default     = "ctf"
}

# ---------------------------------------------------------------------------
# Front : allume toute l'annee. On vise le cout minimal.
# ---------------------------------------------------------------------------

variable "front_instance_type" {
  description = <<-EOT
    Instance du front CTFd (ARM Graviton, ~40% moins cher qu'un equivalent x86).
    t4g.small = 2 vCPU / 2 Go, suffisant pour CTFd + MariaDB + Redis hors evenement.
    Passer a t4g.medium le temps de l'evenement si le scoreboard rame.
  EOT
  type        = string
  default     = "t4g.small"
}

variable "front_volume_gb" {
  description = "Taille du disque du front (gp3). Contient la base et les uploads."
  type        = number
  default     = 20
}

# ---------------------------------------------------------------------------
# Arena : allumee UNIQUEMENT pendant l'evenement.
# ---------------------------------------------------------------------------

variable "arena_enabled" {
  description = <<-EOT
    false (defaut) = aucune instance arena n'existe, donc 0 EUR facture.
    true            = l'arena est creee pour l'evenement.
    Bascule via `make event-up` / `make event-down`.
  EOT
  type        = bool
  default     = false
}

variable "arena_instance_type" {
  description = <<-EOT
    Instance arena, obligatoirement x86-64 : les challenges pwn/reverse sont
    compiles pour x86 et Ollama tourne nettement mieux dessus.
    c6a.2xlarge = 8 vCPU / 16 Go, ~0.31 USD/h en eu-west-3.
  EOT
  type        = string
  default     = "c6a.2xlarge"
}

variable "arena_volume_gb" {
  description = "Disque de l'arena : images Docker des challenges + modeles Ollama (~5 Go par modele)."
  type        = number
  default     = 100
}

variable "arena_use_spot" {
  description = <<-EOT
    true = instance Spot (~70% moins chere) mais interruptible par AWS.
    A eviter le jour J : une interruption tue toutes les instances des equipes.
    Utile pour les repetitions et les tests.
  EOT
  type        = bool
  default     = false
}

# ---------------------------------------------------------------------------
# Acces
# ---------------------------------------------------------------------------

variable "ssh_public_key" {
  description = "Contenu de votre cle publique SSH (ex: contenu de ~/.ssh/id_ed25519.pub)."
  type        = string
}

variable "admin_cidrs" {
  description = <<-EOT
    IPs autorisees a se connecter en SSH et a l'admin CTFd.
    NE PAS laisser 0.0.0.0/0 : mettez l'IP publique de votre bureau/VPN.
  EOT
  type        = list(string)
}

variable "player_cidrs" {
  description = "IPs autorisees a atteindre le CTF (HTTP/HTTPS et instances de challenge). 0.0.0.0/0 = ouvert a tous."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "domain_name" {
  description = "Nom de domaine du CTF (ex: ctf.exemple.com). Laisser vide pour utiliser l'IP publique."
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Plage de ports des instances de challenge (ctfd-whale via frp)
# ---------------------------------------------------------------------------

variable "whale_port_range_start" {
  description = "Premier port TCP alloue aux instances de challenge par equipe."
  type        = number
  default     = 28000
}

variable "whale_port_range_end" {
  description = "Dernier port TCP alloue aux instances de challenge par equipe."
  type        = number
  default     = 28500
}
