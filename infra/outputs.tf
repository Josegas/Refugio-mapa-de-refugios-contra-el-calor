# Values printed after `terraform apply` (and any time with `terraform output`).

output "site_url" {
  description = "Public address of the live site."
  value       = local.site_origin
}

output "amplify_app_id" {
  description = "Amplify app ID, used by the deploy workflow."
  value       = aws_amplify_app.refugio.id
}

output "deploy_role_arn" {
  description = "Role that GitHub Actions assumes. Goes in the repo variable AWS_DEPLOY_ROLE_ARN."
  value       = aws_iam_role.github_deploy.arn
}

output "api_key_names" {
  description = "Names of the browser keys. Read a key's value with `aws location describe-key`."
  value       = { for env, key in awscc_location_api_key.web : env => key.key_name }
}

output "running_as" {
  description = "Identity Terraform used. Should end in user/refugio-dev."
  value       = data.aws_caller_identity.current.arn
}

output "analytics_bucket" {
  description = "Bucket with the Iceberg table (pass it to pipeline/iceberg.py --bucket)"
  value       = aws_s3_bucket.analytics.bucket
}

output "athena_workgroup" {
  value = aws_athena_workgroup.refugio.name
}
