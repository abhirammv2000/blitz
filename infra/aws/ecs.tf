resource "aws_cloudwatch_log_group" "backend" {
  name              = "/ecs/${var.project}-backend"
  retention_in_days = 30
}

resource "aws_ecs_cluster" "main" {
  name = "${var.project}-cluster"
}

locals {
  secret_arn = aws_secretsmanager_secret.backend.arn

  # https:// origins the API accepts. The CloudFront default domain always
  # applies; the custom app subdomain (local.app_host, defined in domain.tf)
  # joins in once a domain is registered.
  cors_origins = join(",", compact([
    "https://${aws_cloudfront_distribution.frontend.domain_name}",
    local.has_domain ? "https://${local.app_host}" : "",
  ]))
}

resource "aws_ecs_task_definition" "backend" {
  family                   = "${var.project}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.backend_cpu
  memory                   = var.backend_memory
  execution_role_arn       = aws_iam_role.execution.arn

  volume {
    name = "data"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.data.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.data.id
        iam             = "DISABLED"
      }
    }
  }

  container_definitions = jsonencode([
    {
      name      = "backend"
      image     = "${aws_ecr_repository.backend.repository_url}:latest"
      essential = true

      portMappings = [
        { containerPort = var.backend_container_port, protocol = "tcp" }
      ]

      mountPoints = [
        { sourceVolume = "data", containerPath = "/data", readOnly = false }
      ]

      environment = [
        { name = "CORS_ORIGINS", value = local.cors_origins },
        { name = "DAILY_RUN_CAP", value = "20" },
        { name = "LOG_LEVEL", value = "INFO" },
      ]

      secrets = [
        for key in [
          "OPENAI_API_KEY", "GEMINI_API_KEY", "TAVILY_API_KEY", "FIRECRAWL_API_KEY",
          "ELEVENLABS_API_KEY", "ELEVENLABS_AGENT_ID", "LANGFUSE_PUBLIC_KEY",
          "LANGFUSE_SECRET_KEY", "ACCESS_KEY",
        ] : { name = key, valueFrom = "${local.secret_arn}:${key}::" }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.backend.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "backend"
        }
      }
    }
  ])
}

resource "aws_ecs_service" "backend" {
  name            = "${var.project}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = var.backend_desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = [aws_subnet.private_a.id, aws_subnet.private_b.id]
    security_groups  = [aws_security_group.backend.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = var.backend_container_port
  }

  # The task definition's :latest image tag doesn't trigger a redeploy on its
  # own - scripts/deploy.sh pushes the image and then forces one explicitly.
  depends_on = [aws_lb_listener.http, aws_iam_role_policy.read_backend_secret]
}
