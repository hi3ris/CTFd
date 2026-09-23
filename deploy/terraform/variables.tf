variable "aws_region" {
  description = "Region AWS. eu-west-3 (Paris) : latence minimale et instances GPU g4dn disponibles."
  type        = string
  default     = "eu-west-3"
}

variable "project_name" {
  description = "Prefixe applique au nom de toutes les ressources."
  type        = string
  default     = "ctf"
}

# ---------------------------------------------------------------------------
# Phase de l'evenement : c'est LE levier de cout.
# ---------------------------------------------------------------------------

variable "phase" {
  description = <<-EOT
    Etat courant du CTF. Determine quelles machines existent et leur taille.

      off           Hors evenement. Aucune instance EC2. Seules subsistent
                    les archives statiques sur S3 (site statique, ~0.50 USD/mois).
      setup         Front seul, petite taille. Pour preparer les challenges,
                    tester, ouvrir les inscriptions.
      preselection  Front + arena + noeud IA, dimensionnes pour ~300 joueurs.
      final         Front + arena + noeud IA, dimensionnes pour ~50 joueurs.

    Bascule via `make phase-<nom>`.
  EOT
  type        = string
  default     = "off"

  validation {
    condition     = contains(["off", "setup", "preselection", "final"], var.phase)
    error_message = "phase doit valoir off, setup, preselection ou final."
  }
}

variable "expected_players" {
  description = <<-EOT
    Nombre de joueurs attendus par phase. Sert uniquement a documenter le
    dimensionnement retenu dans locals.tf ; changez les types d'instance la-bas
    si ces chiffres bougent beaucoup.
  EOT
  type        = map(number)
  default = {
    preselection = 300
    final        = 50
  }
}

# ---------------------------------------------------------------------------
# Modele de langage des challenges IA
# ---------------------------------------------------------------------------

variable "ollama_model" {
  description = <<-EOT
    Modele servi par Ollama pour les challenges de type prompt injection.
    llama3.1:8b tient largement sur le GPU T4 16 Go d'une g4dn.xlarge.
  EOT
  type        = string
  default     = "llama3.1:8b"
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
    IPs autorisees en SSH. NE PAS laisser 0.0.0.0/0 : mettez l'IP publique de
    votre bureau ou de votre VPN.
  EOT
  type        = list(string)
}

variable "player_cidrs" {
  description = "IPs autorisees a atteindre le CTF. 0.0.0.0/0 = ouvert a tous."
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

# Ports web (80/443) du front. Derriere le proxy Cloudflare, on n'y laisse
# entrer QUE les plages Cloudflare (deploy/scripts/cloudflare-ips.sh) : sinon
# un joueur qui trouve l'IP contourne le WAF/anti-DDoS et les vraies IP
# clients (CF-Connecting-IP) ne sont plus fiables. Vide = player_cidrs.
# Les ports des instances (whale_port_range) restent sur player_cidrs.
variable "web_cidrs" {
  description = "IPs autorisees sur 80/443 du front. Vide = player_cidrs."
  type        = list(string)
  default     = []
}

variable "domain_name" {
  description = <<-EOT
    Nom de domaine du CTF (ex: ctf.exemple.com). Il pointe sur le front pendant
    l'evenement, et sur les archives statiques le reste de l'annee.
  EOT
  type        = string
  default     = ""
}

# ---------------------------------------------------------------------------
# Divers
# ---------------------------------------------------------------------------

variable "arena_use_spot" {
  description = <<-EOT
    true = instances Spot (~-70%) mais interruptibles par AWS.
    A garder sur false les 23-25 et 29-30 octobre : une interruption tuerait
    toutes les instances des equipes en cours de resolution.
  EOT
  type        = bool
  default     = false
}

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
