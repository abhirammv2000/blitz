resource "aws_lb" "backend" {
  name               = "${var.project}-backend"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = [aws_subnet.public_a.id, aws_subnet.public_b.id]

  # SSE streams run for minutes - the default 60s idle timeout would cut a
  # pipeline run off mid-stream. 4000s (the ALB max) comfortably covers even
  # a run that hangs near every per-agent timeout at once.
  idle_timeout = 4000
}

resource "aws_lb_target_group" "backend" {
  name        = "${var.project}-backend"
  port        = var.backend_container_port
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # required for awsvpc-mode Fargate tasks

  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.backend.arn
  port              = 80
  protocol          = "HTTP"

  # Forwards directly until a domain exists (local.has_domain, defined in
  # domain.tf) since there's no cert yet to redirect to; once one does,
  # domain.tf's HTTPS listener takes over and this flips to a 301 redirect
  # instead. Exactly one of these two blocks ever renders - a plain
  # non-dynamic default_action here as well as a second listener resource in
  # domain.tf would both bind port 80 and collide.
  dynamic "default_action" {
    for_each = local.has_domain ? [] : [1]
    content {
      type             = "forward"
      target_group_arn = aws_lb_target_group.backend.arn
    }
  }

  dynamic "default_action" {
    for_each = local.has_domain ? [1] : []
    content {
      type = "redirect"
      redirect {
        port        = "443"
        protocol    = "HTTPS"
        status_code = "HTTP_301"
      }
    }
  }
}
