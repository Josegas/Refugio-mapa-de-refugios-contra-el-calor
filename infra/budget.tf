# AWS Budgets: an email as soon as Refugio's services start to cost money.
#
# The account is on the AWS Free plan, so AWS doesn't charge a card: usage beyond the free tier
# is paid with the account's credits. If the credits run out the account closes and the live
# app goes down, so these alerts protect availability, not just money.
# Budgets with email alerts are free of charge.

resource "aws_budgets_budget" "refugio" {
  name         = "refugio-monthly"
  budget_type  = "COST"
  limit_amount = tostring(var.monthly_budget_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  # Only the services Refugio uses
  cost_filter {
    name   = "Service"
    values = ["Amazon Location Service", "AWS Amplify"]
  }

  # Measure usage BEFORE credits are applied. With credits included the cost would always look
  # like $0, and no alert would fire while the credits are being spent.
  cost_types {
    include_credit = false
    include_refund = false
  }

  # 1) The first cent: something went beyond the free tier
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 0.01
    threshold_type             = "ABSOLUTE_VALUE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # 2) Half of the monthly budget is already spent
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  # 3) AWS forecasts that the month will end above the budget
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
