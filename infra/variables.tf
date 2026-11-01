# Inputs. Values that are personal (your email) go in terraform.tfvars, which git ignores.

variable "region" {
  description = "AWS region for everything in this project."
  type        = string
  default     = "us-west-2"
}

variable "github_repo" {
  description = "GitHub repository (owner/name) allowed to deploy through OIDC."
  type        = string
  default     = "Josegas/Refugio-mapa-de-refugios-contra-el-calor"
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
