#!/usr/bin/env bash
# Builds the backend image, pushes it to ECR, and forces the ECS service to
# pick it up. The task definition always points at the :latest tag, which
# doesn't trigger a redeploy by itself - the --force-new-deployment is what
# makes the running task actually replace itself with the new image.
#
#   cd infra/aws
#   ./scripts/deploy-backend.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$SCRIPT_DIR/.."
BACKEND_DIR="$INFRA_DIR/../../backend"
AWS_PROFILE="${AWS_PROFILE:-parlay}"
AWS_REGION="${AWS_REGION:-us-east-1}"

ECR_URL="$(cd "$INFRA_DIR" && terraform output -raw ecr_repository_url)"
REGISTRY="${ECR_URL%%/*}"

aws ecr get-login-password --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  | docker login --username AWS --password-stdin "$REGISTRY"

docker build -t blitz-backend:latest "$BACKEND_DIR"
docker tag blitz-backend:latest "$ECR_URL:latest"
docker push "$ECR_URL:latest"

aws ecs update-service \
  --cluster blitz-cluster --service blitz-backend --force-new-deployment \
  --region "$AWS_REGION" --profile "$AWS_PROFILE" \
  --query "service.deployments[].{status:status,desired:desiredCount,running:runningCount}" \
  --output table

echo "Deployment triggered. Watch it stabilize with:"
echo "  aws ecs describe-services --cluster blitz-cluster --services blitz-backend --region $AWS_REGION --profile $AWS_PROFILE"
