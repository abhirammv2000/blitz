# One JSON secret holding every credential the backend needs, so the task
# definition references one ARN with a per-key JSON pointer instead of eight
# separate secrets. Terraform only ever creates the container and a
# placeholder value - the real values are set out of band with
# scripts/push-secrets.sh so they never pass through a terraform plan/state
# diff or this repo.

resource "aws_secretsmanager_secret" "backend" {
  name        = "${var.project}/backend-secrets"
  description = "OPENAI_API_KEY, GEMINI_API_KEY, TAVILY_API_KEY, FIRECRAWL_API_KEY, ELEVENLABS_API_KEY, ELEVENLABS_AGENT_ID, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, ACCESS_KEY - real values set by scripts/push-secrets.sh, not Terraform"
}

resource "aws_secretsmanager_secret_version" "backend" {
  secret_id = aws_secretsmanager_secret.backend.id
  secret_string = jsonencode({
    OPENAI_API_KEY      = "REPLACE_ME"
    GEMINI_API_KEY      = "REPLACE_ME"
    TAVILY_API_KEY      = "REPLACE_ME"
    FIRECRAWL_API_KEY   = "REPLACE_ME"
    ELEVENLABS_API_KEY  = "REPLACE_ME"
    ELEVENLABS_AGENT_ID = "REPLACE_ME"
    LANGFUSE_PUBLIC_KEY = "REPLACE_ME"
    LANGFUSE_SECRET_KEY = "REPLACE_ME"
    ACCESS_KEY          = "REPLACE_ME"
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}
