# Lets GitHub Actions deploy the site WITHOUT storing any AWS key in GitHub (OIDC).
#
# How it works:
#  1. When the deploy job runs, GitHub gives it a short-lived signed token that says
#     "I am repository <owner@id/repo@id>, environment production".
#  2. AWS checks the token's signature with GitHub's identity provider, registered below.
#  3. If the token matches the trust policy, AWS returns temporary credentials for the role
#     (valid 1 hour) with only the permissions in deploy_permissions.

resource "aws_iam_openid_connect_provider" "github" {
  url            = "https://token.actions.githubusercontent.com"
  client_id_list = ["sts.amazonaws.com"]
}

# WHO can use the role: only jobs of this repository that deploy to its "production" environment
data "aws_iam_policy_document" "github_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]

    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }

    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }

    # Immutable subject: includes the owner and repository IDs, not only their names
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["${var.github_oidc_subject_prefix}:environment:production"]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  name                 = "refugio-github-deploy"
  description          = "Assumed by GitHub Actions (OIDC) to publish the Refugio site on Amplify"
  assume_role_policy   = data.aws_iam_policy_document.github_trust.json
  max_session_duration = 3600
}

# WHAT the role can do: the minimum needed to publish a new version of the site
data "aws_iam_policy_document" "deploy_permissions" {
  statement {
    sid       = "UploadNewVersion"
    actions   = ["amplify:CreateDeployment", "amplify:StartDeployment"]
    resources = [aws_amplify_branch.main.arn]
  }

  statement {
    sid       = "WatchTheDeployment"
    actions   = ["amplify:GetJob"]
    resources = ["${aws_amplify_branch.main.arn}/jobs/*"]
  }

  statement {
    sid       = "ReadProductionBrowserKey"
    actions   = ["geo:DescribeKey"]
    resources = [awscc_location_api_key.web["prod"].arn]
  }
}

resource "aws_iam_role_policy" "github_deploy" {
  name   = "publish-site"
  role   = aws_iam_role.github_deploy.id
  policy = data.aws_iam_policy_document.deploy_permissions.json
}
