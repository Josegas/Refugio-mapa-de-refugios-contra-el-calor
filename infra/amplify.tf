# AWS Amplify Hosting: serves the static site (the web/ folder) over HTTPS through a global CDN.
#
# The app is NOT connected to GitHub. Instead, GitHub Actions uploads each new version only
# after the tests pass (.github/workflows/), so a broken change never reaches the live site.

resource "aws_amplify_app" "refugio" {
  name        = "refugio"
  description = "Refugio: walking distance to cool places in Culiacan's heat"
  platform    = "WEB"

  # Security headers on every response. Referrer-Policy matters for this app: the Amazon
  # Location key only works if the browser tells AWS which site the request comes from.
  # Written exactly as Amplify stores it (compact JSON, "pattern" before "headers"). Any other
  # spelling of the same headers makes `terraform plan` report a false change on every run.
  custom_headers = chomp(<<-JSON
    [{"pattern":"**/*","headers":[{"key":"Strict-Transport-Security","value":"max-age=31536000"},{"key":"X-Content-Type-Options","value":"nosniff"},{"key":"Referrer-Policy","value":"strict-origin-when-cross-origin"}]}]
  JSON
  )
}

# The production branch. Its public address is https://main.<app default domain>
resource "aws_amplify_branch" "main" {
  app_id      = aws_amplify_app.refugio.id
  branch_name = "main"
  stage       = "PRODUCTION"
}
