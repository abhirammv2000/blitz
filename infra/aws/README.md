# Blitz infrastructure

Terraform for a dedicated deployment of Blitz, isolated in its own VPC and
resource namespace (everything prefixed `blitz-`) so it never touches
anything else in the AWS account it runs in.

## Layout

- Backend: FastAPI in a container on ECS Fargate, behind an ALB, private
  subnets with NAT egress for calling OpenAI/Tavily/Firecrawl/Gemini/
  ElevenLabs/Langfuse. Chroma and the leads/usage sqlite db live on an EFS
  volume mounted at `/data`, so they survive a task restart or redeploy.
- Frontend: the Vite build in a private S3 bucket, served through
  CloudFront (HTTPS on its default `*.cloudfront.net` domain - no custom
  domain required for this half).
- Secrets: one JSON secret in Secrets Manager holding every provider key
  plus the access key that gates the API. Terraform creates the container
  with placeholder values; `scripts/push-secrets.sh` puts the real ones in.
- `domain.tf` is entirely a no-op until `domain_name` is set - see below for
  why the backend needs one and the frontend doesn't.

## Why the backend needs a domain and the frontend doesn't

SSE pipeline runs stream for minutes. A CDN in front of the ALB would need
an origin timeout longer than any CDN reasonably offers, so the backend's
TLS has to terminate directly at the ALB - which needs a real ACM
certificate, which needs a domain to be issued for. CloudFront in front of
the S3 frontend has no such problem (it's serving static files, not a
minutes-long stream) and gets free HTTPS on its own default domain with
nothing to register.

Until a domain exists, the frontend is reachable and will load, but pipeline
runs will fail - a browser on the HTTPS CloudFront domain refuses to call a
plain `http://` API (mixed content).

## First-time setup

```
cd infra/aws
terraform init
terraform plan
terraform apply
```

This creates everything except the domain-gated resources. Then:

```
./scripts/push-secrets.sh          # put real provider keys + an access key in Secrets Manager
./scripts/deploy-backend.sh        # build, push to ECR, force the ECS service to pick it up
./scripts/deploy-frontend.sh       # build the frontend, sync to S3, invalidate CloudFront
```

## Adding the domain

```
cp scripts/contact.example.json scripts/contact.json   # fill in real registrant details
./scripts/register-domain.sh example.com
# edit terraform.tfvars: domain_name = "example.com"
terraform apply
./scripts/deploy-frontend.sh   # rebuild against the real https://api.<domain> URL
```

`terraform apply` at that point issues ACM certs (DNS-validated against the
hosted zone Route53 created during registration), adds the ALB's HTTPS
listener, flips the HTTP listener to redirect instead of forward, and points
`app.<domain>` / `api.<domain>` at CloudFront / the ALB.

## Redeploying after a code change

```
./scripts/deploy-backend.sh    # backend code changed
./scripts/deploy-frontend.sh   # frontend code changed
```

## State

Kept local (gitignored), not in an S3 backend - this is a single-operator
project, so the usual reason for remote state (locking across a team
applying concurrently) doesn't apply. Losing `terraform.tfstate` would mean
re-importing resources by hand; an acceptable risk at this scale.

## Cost shape

Roughly fixed-cost regardless of traffic: one NAT gateway, one ALB, one
always-on Fargate task, EFS, S3, and CloudFront. Nothing here scales with
usage except the LLM/search/scrape API spend the app itself makes per
pipeline run, which is capped by the access key and the daily run cap (see
backend's `ACCESS_KEY` / `DAILY_RUN_CAP`), not by anything in this stack.
