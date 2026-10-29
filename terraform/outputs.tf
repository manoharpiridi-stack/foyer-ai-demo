output "app_url" {
  description = "Public URL of the app"
  value       = aws_lambda_function_url.app.function_url
}

output "ecr_repository_url" {
  value = aws_ecr_repository.app.repository_url
}
