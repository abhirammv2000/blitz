# Everything in this file is a no-op until var.domain_name is set - every
# resource is count-guarded on it. Buying the domain itself isn't something
# Terraform does (Route53 domain registration is a one-time purchase, not
# idempotent infrastructure) - that happens once via
# scripts/register-domain.sh, which also creates the hosted zone this file
# then reads.
#
# Layout once a domain exists:
#   app.<domain>  -> CloudFront (frontend)
#   api.<domain>  -> ALB (backend), HTTPS only, HTTP redirects to HTTPS

locals {
  has_domain = var.domain_name != ""
  app_host   = local.has_domain ? "app.${var.domain_name}" : null
  api_host   = local.has_domain ? "api.${var.domain_name}" : null
}

data "aws_route53_zone" "root" {
  count = local.has_domain ? 1 : 0
  name  = var.domain_name
}

# --- API cert (ALB, regional - must be in var.aws_region) -----------------

resource "aws_acm_certificate" "api" {
  count             = local.has_domain ? 1 : 0
  domain_name       = local.api_host
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "api_cert_validation" {
  for_each = local.has_domain ? {
    for dvo in aws_acm_certificate.api[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  } : {}

  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "api" {
  count                   = local.has_domain ? 1 : 0
  certificate_arn         = aws_acm_certificate.api[0].arn
  validation_record_fqdns = [for r in aws_route53_record.api_cert_validation : r.fqdn]
}

resource "aws_lb_listener" "https" {
  count             = local.has_domain ? 1 : 0
  load_balancer_arn = aws_lb.backend.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate_validation.api[0].certificate_arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}

resource "aws_route53_record" "api" {
  count   = local.has_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = local.api_host
  type    = "A"

  alias {
    name                   = aws_lb.backend.dns_name
    zone_id                = aws_lb.backend.zone_id
    evaluate_target_health = true
  }
}

# --- Frontend cert (CloudFront - must be us-east-1, provided by the aliased
# provider below regardless of var.aws_region) -----------------------------

provider "aws" {
  alias   = "us_east_1"
  region  = "us-east-1"
  profile = var.aws_profile
}

resource "aws_acm_certificate" "app" {
  count             = local.has_domain ? 1 : 0
  provider          = aws.us_east_1
  domain_name       = local.app_host
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_route53_record" "app_cert_validation" {
  for_each = local.has_domain ? {
    for dvo in aws_acm_certificate.app[0].domain_validation_options : dvo.domain_name => {
      name  = dvo.resource_record_name
      type  = dvo.resource_record_type
      value = dvo.resource_record_value
    }
  } : {}

  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = each.value.name
  type    = each.value.type
  records = [each.value.value]
  ttl     = 60
}

resource "aws_acm_certificate_validation" "app" {
  count                   = local.has_domain ? 1 : 0
  provider                = aws.us_east_1
  certificate_arn         = aws_acm_certificate.app[0].arn
  validation_record_fqdns = [for r in aws_route53_record.app_cert_validation : r.fqdn]
}

resource "aws_route53_record" "app" {
  count   = local.has_domain ? 1 : 0
  zone_id = data.aws_route53_zone.root[0].zone_id
  name    = local.app_host
  type    = "A"

  alias {
    name                   = aws_cloudfront_distribution.frontend.domain_name
    zone_id                = aws_cloudfront_distribution.frontend.hosted_zone_id
    evaluate_target_health = false
  }
}
