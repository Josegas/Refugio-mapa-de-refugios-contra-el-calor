# Browser API keys for Amazon Location Service (maps, address search and walking routes).
#
# A browser key is public by design: anyone can read it in the page source. What protects it:
#   - allow_actions:  only the 5 calls the app makes (least privilege)
#   - allow_referers: browsers only accept it on our own site (or on localhost for the dev key)
#   - expire_time:    it stops working by itself after judging
#   - the alerts in budget.tf
# A Referer header can be faked outside a browser (e.g. with curl), so these restrictions
# reduce abuse but don't make the key secret.

locals {
  site_origin = "https://main.${aws_amplify_app.refugio.default_domain}"

  api_keys = {
    # Production key: only works from the live site
    prod = {
      description = "Refugio live site"
      referers    = ["${local.site_origin}/*"]
    }
    # Development key: only works from your laptop (http://localhost:<any port>)
    local = {
      description = "Refugio local development"
      referers    = ["http://localhost:*", "http://127.0.0.1:*"]
    }
  }
}

resource "awscc_location_api_key" "web" {
  for_each = local.api_keys # one key per entry: refugio-web-prod and refugio-web-local

  key_name    = "refugio-web-${each.key}"
  description = each.value.description
  expire_time = var.key_expiry

  # Restrictions of a key that was used in the last 7 days can only be changed with this flag.
  # (Deleting such a key is still blocked: a safety net for the live key during judging.)
  force_update = true

  restrictions = {
    allow_actions = [
      "geo-maps:GetTile",             # base map tiles
      "geo-places:Geocode",           # address -> coordinates
      "geo-places:SearchNearby",      # cool places near the person
      "geo-routes:CalculateRoutes",   # walking route to the nearest refuge
      "geo-routes:CalculateIsolines", # area reachable on foot in 5, 10 and 15 minutes
    ]
    allow_resources = [
      "arn:aws:geo-maps:${var.region}::provider/default",
      "arn:aws:geo-places:${var.region}::provider/default",
      "arn:aws:geo-routes:${var.region}::provider/default",
    ]
    allow_referers = each.value.referers
  }

  # awscc takes tags as a list of {key, value}
  tags = [for k, v in local.tags : { key = k, value = v }]
}
