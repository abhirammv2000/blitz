output "ecr_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "alb_dns_name" {
  description = "The API's address before a domain exists. Use with http://, since no cert is issued for this hostname."
  value       = aws_lb.backend.dns_name
}

output "cloudfront_domain_name" {
  description = "The frontend's address - already valid HTTPS with no domain needed."
  value       = aws_cloudfront_distribution.frontend.domain_name
}

output "cloudfront_distribution_id" {
  description = "Used by scripts/deploy-frontend.sh to invalidate the cache after a redeploy."
  value       = aws_cloudfront_distribution.frontend.id
}

output "frontend_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}

output "secrets_arn" {
  value = aws_secretsmanager_secret.backend.arn
}

output "api_url" {
  description = "Null until a domain is set - the real API URL once it is."
  value       = local.has_domain ? "https://${local.api_host}" : null
}

output "app_url" {
  description = "Null until a domain is set - the real frontend URL once it is."
  value       = local.has_domain ? "https://${local.app_host}" : null
}
