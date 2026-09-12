# Durable storage for chroma_data/ and blitz.db (leads + the daily run
# count) - what makes the run-persistence feature and the daily cap actually
# survive a task restart or redeploy, instead of resetting every time Fargate
# replaces the container.

resource "aws_efs_file_system" "data" {
  encrypted = true

  tags = { Name = "${var.project}-data" }
}

resource "aws_efs_mount_target" "private_a" {
  file_system_id  = aws_efs_file_system.data.id
  subnet_id       = aws_subnet.private_a.id
  security_groups = [aws_security_group.efs.id]
}

resource "aws_efs_mount_target" "private_b" {
  file_system_id  = aws_efs_file_system.data.id
  subnet_id       = aws_subnet.private_b.id
  security_groups = [aws_security_group.efs.id]
}

# The container runs as root (the Dockerfile sets no USER), so the access
# point is owned by root too - anything else would need a matching USER
# directive in the image or every write to /data would fail permission checks.
resource "aws_efs_access_point" "data" {
  file_system_id = aws_efs_file_system.data.id

  posix_user {
    uid = 0
    gid = 0
  }

  root_directory {
    path = "/data"
    creation_info {
      owner_uid   = 0
      owner_gid   = 0
      permissions = "755"
    }
  }

  tags = { Name = "${var.project}-data-ap" }
}
