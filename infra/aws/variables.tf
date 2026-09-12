variable "aws_region" {
  description = "Region everything gets created in. us-east-1 specifically because an ACM cert used by CloudFront later must live there regardless of where the rest of the stack runs."
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "Local AWS CLI profile to build with. Points at a dedicated account so this never touches an unrelated project's resources."
  type        = string
  default     = "parlay"
}

variable "project" {
  description = "Prefix applied to every resource name, so this stack is identifiable and grep-able independent of the tags."
  type        = string
  default     = "blitz"
}

variable "vpc_cidr" {
  description = "CIDR for the dedicated VPC. Picked outside 172.31.0.0/16 (the account's default VPC) so the two are never mistaken for each other."
  type        = string
  default     = "10.42.0.0/16"
}

variable "backend_container_port" {
  description = "Port the FastAPI container listens on, matching the Dockerfile's EXPOSE and the README's uvicorn command."
  type        = number
  default     = 8001
}

variable "backend_cpu" {
  description = "Fargate task CPU units (256 = 0.25 vCPU). Sized for a low-traffic demo, not production load."
  type        = number
  default     = 512
}

variable "backend_memory" {
  description = "Fargate task memory in MiB. chromadb's embedding model is disabled in this app, so this doesn't need to be large."
  type        = number
  default     = 1024
}

variable "backend_desired_count" {
  description = "How many copies of the backend task run at once. 1 is enough for a demo and keeps the EFS-backed SQLite usage-cap file free of any need for cross-instance coordination."
  type        = number
  default     = 1
}

variable "domain_name" {
  description = "Root domain for the deployment, e.g. \"example.com\". Empty until one is registered - the ALB HTTPS listener, Route53 zone, and ACM cert are all conditioned on this being set, since a valid cert cannot be issued for the ALB's own AWS hostname."
  type        = string
  default     = ""
}
