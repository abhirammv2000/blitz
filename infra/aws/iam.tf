# Execution role: what ECS itself uses to start the task - pull the image
# from ECR, write logs, and resolve the secrets referenced in the task
# definition. Distinct from a task role (what the *application code* would
# use to call other AWS services) - the app makes no AWS API calls of its
# own, so no task role is defined here.

data "aws_iam_policy_document" "ecs_tasks_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "execution" {
  name               = "${var.project}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_tasks_assume.json
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

data "aws_iam_policy_document" "read_backend_secret" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.backend.arn]
  }
}

resource "aws_iam_role_policy" "read_backend_secret" {
  name   = "${var.project}-read-backend-secret"
  role   = aws_iam_role.execution.id
  policy = data.aws_iam_policy_document.read_backend_secret.json
}
