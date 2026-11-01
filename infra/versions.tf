# Terraform and provider versions.
# Pinning versions makes `terraform init` reproducible: the exact provider builds that were
# downloaded are recorded in .terraform.lock.hcl, which IS committed to git.
terraform {
  required_version = ">= 1.15.0"

  required_providers {
    # The classic AWS provider: IAM, Amplify, Budgets...
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.71" # 6.23+ understands `aws login` credentials
    }
    # AWS Cloud Control provider: covers newer resource types, such as Amazon Location
    # API keys, that the classic provider doesn't have yet.
    awscc = {
      source  = "hashicorp/awscc"
      version = "~> 1.108"
    }
  }

  # No "backend" block: the state is kept in this folder (terraform.tfstate, git-ignored).
  # Free and simple for a one-person project. With a team, the next step is an S3 backend.
}

# Credentials come from the environment, never from this code:
#   export AWS_PROFILE=refugio   (the profile created with `aws login`)
provider "aws" {
  region = var.region

  # Every resource created by this provider gets these tags, so it's always clear what
  # belongs to Refugio.
  default_tags {
    tags = local.tags
  }
}

provider "awscc" {
  region = var.region
}
