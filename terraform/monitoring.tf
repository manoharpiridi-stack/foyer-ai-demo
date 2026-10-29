# Observability, all inside the AWS free tier.
# backend/monitoring.py writes one JSON line per question; CloudWatch turns those lines into metrics,
# saved queries, a dashboard and an email alarm.

locals {
  log_group = aws_cloudwatch_log_group.lambda.name
  namespace = "FoyerAIDemo"
}

# Metrics extracted from the JSON log lines
resource "aws_cloudwatch_log_metric_filter" "questions" {
  name           = "questions"
  log_group_name = local.log_group
  pattern        = "{ $.status = \"ok\" || $.status = \"error\" }"
  metric_transformation {
    name      = "Questions"
    namespace = local.namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "errors" {
  name           = "question-errors"
  log_group_name = local.log_group
  pattern        = "{ $.status = \"error\" }"
  metric_transformation {
    name      = "QuestionErrors"
    namespace = local.namespace
    value     = "1"
  }
}

resource "aws_cloudwatch_log_metric_filter" "answer_time" {
  name           = "answer-time"
  log_group_name = local.log_group
  pattern        = "{ $.total_ms > 0 }"
  metric_transformation {
    name      = "AnswerTimeMs"
    namespace = local.namespace
    value     = "$.total_ms"
    unit      = "Milliseconds"
  }
}

resource "aws_cloudwatch_log_metric_filter" "cost" {
  name           = "openai-cost"
  log_group_name = local.log_group
  pattern        = "{ $.cost_usd >= 0 }"
  metric_transformation {
    name      = "OpenAICostUSD"
    namespace = local.namespace
    value     = "$.cost_usd"
  }
}

# Email alerts: AWS sends a confirmation email first; the link in it must be clicked once.
resource "aws_sns_topic" "alerts" {
  name = "${local.name}-alerts"
  tags = local.tags
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

resource "aws_cloudwatch_metric_alarm" "question_errors" {
  alarm_name          = "${local.name}-question-errors"
  alarm_description   = "A question failed (see the 'Errors' saved query in CloudWatch Logs Insights)"
  namespace           = local.namespace
  metric_name         = "QuestionErrors"
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  tags                = local.tags
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${local.name}-lambda-errors"
  alarm_description   = "The Lambda function itself failed (crash or timeout)"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.app.function_name }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  tags                = local.tags
}

# Saved queries: CloudWatch > Logs Insights > Saved queries > foyer-ai-demo
locals {
  saved_queries = {
    "Recent questions"     = "fields @timestamp, event, question, route, found, status, total_ms, cost_usd | filter ispresent(event) | sort @timestamp desc | limit 50"
    "Answer time by route" = "filter ispresent(total_ms) | stats count() as questions, pct(total_ms, 50) as median_ms, pct(total_ms, 95) as p95_ms by event, route"
    "Errors"               = "fields @timestamp, event, question, error | filter status = \"error\" | sort @timestamp desc"
    "OpenAI cost per day"  = "filter ispresent(cost_usd) | stats count() as questions, sum(cost_usd) as usd by bin(1d)"
    "Cold starts per hour" = "filter @type = \"REPORT\" and ispresent(@initDuration) | stats count() as cold_starts, avg(@initDuration) as avg_start_ms by bin(1h)"
  }
}

resource "aws_cloudwatch_query_definition" "saved" {
  for_each        = local.saved_queries
  name            = "${local.name}/${each.key}"
  log_group_names = [local.log_group]
  query_string    = each.value
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = local.name
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 8, height = 6
        properties = {
          title   = "Questions and errors (per 5 min)", region = var.aws_region, stat = "Sum", period = 300
          metrics = [[local.namespace, "Questions"], [local.namespace, "QuestionErrors", { color = "#d62728" }]]
        }
      },
      {
        type = "metric", x = 8, y = 0, width = 8, height = 6
        properties = {
          title   = "Answer time (ms)", region = var.aws_region, period = 300
          metrics = [[local.namespace, "AnswerTimeMs", { stat = "p50", label = "median" }], [local.namespace, "AnswerTimeMs", { stat = "p95", label = "slowest 5%" }]]
        }
      },
      {
        type = "metric", x = 16, y = 0, width = 8, height = 6
        properties = {
          title   = "Estimated OpenAI cost (USD per day)", region = var.aws_region, stat = "Sum", period = 86400
          metrics = [[local.namespace, "OpenAICostUSD"]]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title = "Lambda: requests, errors and copies running", region = var.aws_region, period = 300
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", local.name, { stat = "Sum" }],
            ["AWS/Lambda", "Errors", "FunctionName", local.name, { stat = "Sum", color = "#d62728" }],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", local.name, { stat = "Maximum" }],
          ]
        }
      },
      {
        type = "log", x = 12, y = 6, width = 12, height = 6
        properties = {
          title = "Latest questions", region = var.aws_region, view = "table"
          query = "SOURCE '${local.log_group}' | ${local.saved_queries["Recent questions"]}"
        }
      },
    ]
  })
}
