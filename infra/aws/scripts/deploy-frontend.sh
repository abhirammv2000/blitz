#!/usr/bin/env bash
# Builds the frontend against whichever API URL is live right now - the real
# https://api.<domain> once one is registered, otherwise the plain ALB
# hostname (which a browser on the HTTPS CloudFront domain cannot actually
# call - mixed content - so the app will load but pipeline runs will fail
# until a domain exists). Syncs the build to S3 and invalidates CloudFront so
# viewers don't keep seeing the previous build from cache.
#
#   cd infra/aws
#   ./scripts/deploy-frontend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/.."
FRONTEND_DIR="$INFRA_DIR/../../frontend"
AWS_PROFILE="${AWS_PROFILE:-parlay}"
AWS_REGION="${AWS_REGION:-us-east-1}"

cd "$INFRA_DIR"
API_URL="$(terraform output -raw api_url 2>/dev/null || true)"
if [[ -z "$API_URL" || "$API_URL" == "null" ]]; then
  API_URL="http://$(terraform output -raw alb_dns_name)"
  echo "No domain configured yet - building against $API_URL."
  echo "A browser on the HTTPS frontend cannot call a plain http:// API (mixed content), so pipeline runs will fail until a domain is registered."
fi
BUCKET="$(terraform output -raw frontend_bucket_name)"
DIST_ID="$(terraform output -raw cloudfront_distribution_id)"

cd "$FRONTEND_DIR"
VITE_API_URL="$API_URL" npm run build

aws s3 sync dist/ "s3://$BUCKET/" --region "$AWS_REGION" --profile "$AWS_PROFILE" --delete
aws cloudfront create-invalidation \
  --distribution-id "$DIST_ID" --paths "/*" \
  --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --query "Invalidation.{Id:Id,Status:Status}" --output table

cd "$INFRA_DIR"
echo "Live at: https://$(terraform output -raw cloudfront_domain_name)"
