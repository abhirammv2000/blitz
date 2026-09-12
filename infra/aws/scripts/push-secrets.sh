#!/usr/bin/env bash
# Pushes backend/.env's provider credentials into the blitz/backend-secrets
# entry Terraform created. Terraform only ever writes a REPLACE_ME placeholder
# (see ../secrets.tf - a real value in a plan/state diff is a real value
# sitting in a state file) - this is what puts the actual values in.
#
# Reuses the existing ACCESS_KEY already in Secrets Manager if there is one,
# so re-running this after rotating a provider key doesn't also lock out
# everyone who has the current access key. Pass -r to roll a fresh one instead.
#
#   cd infra/aws
#   ./scripts/push-secrets.sh          # keep the current access key
#   ./scripts/push-secrets.sh -r       # roll a new access key too
set -euo pipefail

ROLL_ACCESS_KEY=false
if [[ "${1:-}" == "-r" ]]; then
  ROLL_ACCESS_KEY=true
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ENV="$SCRIPT_DIR/../../../backend/.env"
AWS_PROFILE="${AWS_PROFILE:-parlay}"
AWS_REGION="${AWS_REGION:-us-east-1}"
SECRET_ID="blitz/backend-secrets"

if [[ ! -f "$BACKEND_ENV" ]]; then
  echo "No backend/.env found at $BACKEND_ENV - nothing to push." >&2
  exit 1
fi

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

set -a
# shellcheck disable=SC1090
source "$BACKEND_ENV"
set +a

if [[ "$ROLL_ACCESS_KEY" == true ]]; then
  ACCESS_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  echo "Rolled a new access key."
else
  ACCESS_KEY="$(
    aws secretsmanager get-secret-value \
      --secret-id "$SECRET_ID" --region "$AWS_REGION" --profile "$AWS_PROFILE" \
      --query SecretString --output text 2>/dev/null \
      | python3 -c 'import json,sys
try:
    print(json.load(sys.stdin).get("ACCESS_KEY", ""))
except Exception:
    print("")' || true
  )"
  if [[ -z "$ACCESS_KEY" || "$ACCESS_KEY" == "REPLACE_ME" ]]; then
    ACCESS_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
    echo "No existing access key found - generated one."
  fi
fi
export ACCESS_KEY

python3 -c '
import json, os
keys = [
    "OPENAI_API_KEY", "GEMINI_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY",
    "ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY", "ACCESS_KEY",
]
data = {k: os.environ.get(k, "") for k in keys}
missing = [k for k, v in data.items() if not v and k != "ACCESS_KEY"]
if missing:
    print("Missing from backend/.env, pushing empty values for:", ", ".join(missing))
with open(os.environ["TMP_JSON"], "w") as f:
    json.dump(data, f)
'

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ID" --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --secret-string "file://$TMP_JSON" \
  --query "{ARN:ARN,VersionId:VersionId}" --output table

echo "Access key for the deployed app: $ACCESS_KEY"
echo "Restart the ECS service to pick up the change: aws ecs update-service --cluster blitz-cluster --service blitz-backend --force-new-deployment --region $AWS_REGION --profile $AWS_PROFILE"
