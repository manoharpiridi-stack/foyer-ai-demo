terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  name = "foyer-ai-demo"
  tags = {
    Project   = "foyer-ai-demo"
    ManagedBy = "terraform"
  }
}

# Docker image registry
resource "aws_ecr_repository" "app" {
  name                 = local.name
  image_tag_mutability = "MUTABLE"
  force_delete         = true
  tags                 = local.tags
}

resource "aws_ecr_lifecycle_policy" "app" {
  repository = aws_ecr_repository.app.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the last 3 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 3 }
      action       = { type = "expire" }
    }]
  })
}

# Permissions: the function may only write its own logs
resource "aws_iam_role" "lambda" {
  name = "${local.name}-lambda"
  tags = local.tags
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "lambda.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${local.name}"
  retention_in_days = 7
  tags              = local.tags
}

# The app: the same Docker image that runs locally
resource "aws_lambda_function" "app" {
  function_name = local.name
  package_type  = "Image"
  image_uri     = "${aws_ecr_repository.app.repository_url}:${var.image_tag}"
  role          = aws_iam_role.lambda.arn
  architectures = ["x86_64"]
  memory_size   = 2048
  timeout       = 60
  tags          = local.tags

  ephemeral_storage {
    size = 1024 # /tmp holds a copy of the Chroma index (~240 MB)
  }

  environment {
    variables = {
      OPENAI_API_KEY      = var.openai_api_key
      OPENAI_MODEL        = var.openai_model
      HOME                = "/tmp"
      AWS_LWA_INVOKE_MODE = "response_stream"
    }
  }

  depends_on = [aws_iam_role_policy_attachment.lambda_logs, aws_cloudwatch_log_group.lambda]
}

# Public HTTPS URL. Streaming mode allows responses above 6 MB (the Excel download).
resource "aws_lambda_function_url" "app" {
  function_name      = aws_lambda_function.app.function_name
  authorization_type = "NONE"
  invoke_mode        = "RESPONSE_STREAM"
}

resource "aws_lambda_permission" "public_url" {
  statement_id           = "AllowPublicFunctionUrl"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.app.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

# Keep-warm: every 5 minutes, EventBridge calls the function (the Web Adapter routes it to /api/warmup),
# so one instance stays loaded and visitors rarely wait for a cold start.
resource "aws_iam_role" "scheduler" {
  name = "${local.name}-scheduler"
  tags = local.tags
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "sts:AssumeRole", Principal = { Service = "scheduler.amazonaws.com" } }]
  })
}

resource "aws_iam_role_policy" "scheduler_invoke" {
  name = "invoke-app"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "lambda:InvokeFunction", Resource = aws_lambda_function.app.arn }]
  })
}

resource "aws_scheduler_schedule" "warmup" {
  name                = "${local.name}-warmup"
  schedule_expression = "rate(5 minutes)"

  flexible_time_window {
    mode = "OFF"
  }

  target {
    arn      = aws_lambda_function.app.arn
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ source = "warmup" })
  }
}

resource "aws_lambda_permission" "public_invoke" {
  statement_id             = "AllowPublicInvokeViaUrl"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.app.function_name
  principal                = "*"
  invoked_via_function_url = true
}
