# Shared values and a safety check.

locals {
  tags = {
    Project   = "refugio"
    ManagedBy = "terraform"
  }
}

# Who is running Terraform right now?
data "aws_caller_identity" "current" {}

# Safety guard: this laptop's default AWS credentials belong to another project. If Terraform
# isn't running as the refugio-dev user, stop at `terraform plan`, before anything changes.
resource "terraform_data" "identity_guard" {
  lifecycle {
    precondition {
      condition     = endswith(data.aws_caller_identity.current.arn, ":user/refugio-dev")
      error_message = "Terraform is running as ${data.aws_caller_identity.current.arn}, not refugio-dev. Run: export AWS_PROFILE=refugio"
    }
  }
}
