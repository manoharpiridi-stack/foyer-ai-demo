variable "aws_region" {
  description = "AWS region (Frankfurt, close to Luxembourg)"
  type        = string
  default     = "eu-central-1"
}

variable "image_tag" {
  description = "Tag of the Docker image in ECR to run; set by scripts/deploy.py"
  type        = string
}

variable "openai_api_key" {
  description = "OpenAI API key; deploy.py reads it from .env"
  type        = string
  sensitive   = true
}

variable "alert_email" {
  description = "Email that receives error alerts; set in terraform.tfvars (git-ignored)"
  type        = string
}

variable "openai_model" {
  description = "OpenAI chat model"
  type        = string
  default     = "gpt-4.1-mini"
}
