# Analytics: the pipeline's results as an Apache Iceberg table on Amazon S3, queried with
# Amazon Athena. The live app doesn't use any of this; it's for SQL questions about the results.

# 1) Bucket for the Iceberg table files and Athena's query results.
#    The account ID In the name makes it unique worldwide (bucket name are global).
resource "aws_s3_bucket" "analytics" {
  bucket        = "refugio-analytics-${data.aws_caller_identity.current.account_id}"
  force_destroy = true # lets `terraform destroy` delete it eve if it has files
}
# Nobody on the internet can read it: only users of this account with permissions
resource "aws_s3_bucket_public_access_block" "analytics" {
  bucket                  = aws_s3_bucket.analytics.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Athena saves a copy of every result; delete those copies after 7 days
resource "aws_s3_bucket_lifecycle_configuration" "analytics" {
  bucket = aws_s3_bucket.analytics.id

  rule {
    id     = "expire-athena-results"
    status = "Enabled"
    filter {
      prefix = "athena-results/"
    }
    expiration {
      days = 7
    }
  }
}

# 2) Catalog: a Glue database lists the tables and where their files are (like a schema in SQL)
resource "aws_glue_catalog_database" "refugio" {
  name        = "refugio"
  description = "Refugio walking-access results (Apache Iceberg tables on S3)"
}

# 3) Athena workgroup: where results go, and a spending cap per query
resource "aws_athena_workgroup" "refugio" {
  name          = "refugio"
  force_destroy = true

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = false
    bytes_scanned_cutoff_per_query     = 1073741824 # 1 GB: a bigger query is cancelled (max ~$0.005)

    engine_version {
      selected_engine_version = "Athena engine version 3" # the version that supports Iceberg
    }

    result_configuration {
      output_location = "s3://${aws_s3_bucket.analytics.bucket}/athena-results/"
    }
  }
}
