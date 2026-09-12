#!/usr/bin/env bash
# Registers a domain through Route53 Domains and waits for it to complete.
# This is a real, one-time purchase (not idempotent infrastructure), which is
# why it's a script and not a Terraform resource - the AWS provider has no
# "buy a new domain" resource on purpose, since re-running terraform apply is
# never supposed to spend money on its own.
#
# Registration needs a registrant/admin/tech contact (real name, address,
# phone, email - what the registry puts on file for the domain). Copy
# contact.example.json to contact.json (gitignored) and fill it in first.
#
#   cd infra/aws
#   ./scripts/register-domain.sh example.com
set -euo pipefail

DOMAIN="${1:?Usage: register-domain.sh <domain>}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONTACT_FILE="$SCRIPT_DIR/contact.json"
AWS_PROFILE="${AWS_PROFILE:-parlay}"
# Route53 Domains is a us-east-1-only API regardless of where the rest of
# the stack runs.
AWS_REGION="us-east-1"

if [[ ! -f "$CONTACT_FILE" ]]; then
  echo "Missing $CONTACT_FILE - copy contact.example.json to contact.json and fill in real registrant details first." >&2
  exit 1
fi

echo "Checking availability for $DOMAIN..."
AVAILABLE="$(aws route53domains check-domain-availability --domain-name "$DOMAIN" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query Availability --output text)"
if [[ "$AVAILABLE" != "AVAILABLE" ]]; then
  echo "$DOMAIN is not available (status: $AVAILABLE)." >&2
  exit 1
fi

echo "Estimated price:"
aws route53domains list-prices --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --query "Prices[?Name=='${DOMAIN##*.}'].RegistrationPrice" --output table || true

read -r -p "Register $DOMAIN now? This charges the account on file. [y/N] " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo "Cancelled."
  exit 0
fi

OPERATION_ID="$(
  aws route53domains register-domain \
    --domain-name "$DOMAIN" \
    --duration-in-years 1 \
    --auto-renew \
    --admin-contact "file://$CONTACT_FILE" \
    --registrant-contact "file://$CONTACT_FILE" \
    --tech-contact "file://$CONTACT_FILE" \
    --region "$AWS_REGION" --profile "$AWS_PROFILE" \
    --query OperationId --output text
)"

echo "Registration submitted (operation $OPERATION_ID). This typically takes a few minutes."
echo "Watching status..."
while true; do
  STATUS="$(aws route53domains get-operation-detail --operation-id "$OPERATION_ID" --region "$AWS_REGION" --profile "$AWS_PROFILE" --query Status --output text)"
  echo "  $STATUS"
  case "$STATUS" in
    SUCCESSFUL) break ;;
    FAILED|ERROR) echo "Registration failed." >&2; exit 1 ;;
  esac
  sleep 15
done

echo
echo "Registered. Route53 auto-created a hosted zone for $DOMAIN."
echo "Next: set domain_name = \"$DOMAIN\" in terraform.tfvars, then:"
echo "  terraform apply"
echo "  ./scripts/deploy-frontend.sh   # rebuild against the real https:// API URL"
