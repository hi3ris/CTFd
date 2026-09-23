# ---------------------------------------------------------------------------
# Deploiement continu depuis GitHub Actions, sans cle AWS longue duree.
#
# GitHub signe un jeton OIDC par job ; AWS l'echange contre un role dont le
# perimetre est reduit a une seule chose : lancer `deploy/scripts/front-update.sh`
# sur le front via SSM Run Command (tag Name = <projet>-front). Le SSH admin
# reste ferme aux runners (admin_cidrs), et l'agent SSM est deja present sur le
# front (AmazonSSMManagedInstanceCore, cf. iam.tf).
#
# Cote GitHub : variables de depot AWS_DEPLOY_ROLE_ARN (sortie ci-dessous) et
# AWS_REGION ; workflow .github/workflows/nctf26-deploy.yml.
# ---------------------------------------------------------------------------

variable "github_repo" {
  description = "Depot GitHub autorise a deployer (owner/name)."
  type        = string
  default     = "hi3ris/CTFd"
}

variable "github_deploy_refs" {
  description = "Refs Git autorisees a assumer le role de deploiement."
  type        = list(string)
  default     = ["refs/heads/master", "refs/heads/claude/ctf-platform-free-ptiggj"]
}

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
  # AWS valide desormais le certificat GitHub par sa propre chaine de confiance ;
  # l'empreinte reste obligatoire dans l'API.
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_deploy" {
  name = "${var.project_name}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRoleWithWebIdentity"
      Principal = { Federated = aws_iam_openid_connect_provider.github.arn }
      Condition = {
        StringEquals = { "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com" }
        StringLike = {
          "token.actions.githubusercontent.com:sub" = [
            for r in var.github_deploy_refs : "repo:${var.github_repo}:ref:${r}"
          ]
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "github_deploy" {
  name = "ssm-run-front-update"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "FindFront"
        Effect   = "Allow"
        Action   = ["ec2:DescribeInstances", "ssm:DescribeInstanceInformation"]
        Resource = "*"
      },
      {
        Sid    = "RunShellOnFrontOnly"
        Effect = "Allow"
        Action = "ssm:SendCommand"
        Resource = [
          "arn:aws:ec2:${var.aws_region}:${data.aws_caller_identity.current.account_id}:instance/*",
        ]
        Condition = {
          StringEquals = { "ec2:ResourceTag/Name" = "${var.project_name}-front" }
        }
      },
      {
        Sid      = "RunShellDocument"
        Effect   = "Allow"
        Action   = "ssm:SendCommand"
        Resource = "arn:aws:ssm:${var.aws_region}::document/AWS-RunShellScript"
      },
      {
        Sid      = "ReadCommandResult"
        Effect   = "Allow"
        Action   = ["ssm:GetCommandInvocation", "ssm:ListCommandInvocations", "ssm:ListCommands"]
        Resource = "*"
      },
    ]
  })
}

output "github_deploy_role_arn" {
  description = "A mettre dans la variable de depot GitHub AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}
