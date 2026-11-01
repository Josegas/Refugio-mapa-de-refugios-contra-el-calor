# Inputs. Values that are personal (your email) go in terraform.tfvars, which git ignores.

variable "region" {
  description = "AWS region for everything in this project."
  type        = string
  default     = "us-west-2"
}

variable "github_oidc_subject_prefix" {
  description = <<-EOT
    Start of the "sub" claim in this repository's GitHub OIDC tokens. The repo uses GitHub's
    immutable subject format (owner@owner_id/repo@repo_id), so a deleted-and-recreated repo with
    the same name could never deploy. Read it with:
      gh api "repos/{owner}/{repo}/actions/oidc/customization/sub"
  EOT
  type        = string
  default     = "repo:Josegas@80491054/Refugio-mapa-de-refugios-contra-el-calor@1441297459"
}

variable "alert_email" {
  description = "Email address that receives the budget alerts."
  type        = string
}

variable "monthly_budget_usd" {
  description = "Monthly budget for the services Refugio uses, in USD."
  type        = number
  default     = 5
}

variable "key_expiry" {
  description = "When the browser API keys stop working (UTC). Judging ends Nov 13, 2026."
  type        = string
  default     = "2027-01-31T00:00:00.000Z"
}
