resource "aws_security_group" "alb" {
  name        = "${var.project}-alb"
  description = "Public entry point - open to the internet on 80/443 only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP (redirects to HTTPS once a cert exists)"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-alb-sg" }
}

resource "aws_security_group" "backend" {
  name        = "${var.project}-backend"
  description = "Fargate task - only reachable from the ALB, reaches out to the model/search/scrape providers"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "From the ALB only"
    from_port       = var.backend_container_port
    to_port         = var.backend_container_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-backend-sg" }
}

resource "aws_security_group" "efs" {
  name        = "${var.project}-efs"
  description = "Chroma/sqlite persistent volume - only reachable from the backend task"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from the backend task only"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.backend.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project}-efs-sg" }
}
