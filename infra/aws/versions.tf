# State is kept local on purpose - this is a single-operator project, not a
# team one, so the usual reason for an S3 + DynamoDB remote backend (shared
# locking across multiple people applying at once) doesn't apply here. The
# state file itself is gitignored; losing it would mean re-importing
# resources by hand, which is an acceptable risk for a project this size.

terraform {
  required_version = ">= 1.9"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = {
      Project   = "blitz"
      ManagedBy = "terraform"
    }
  }
}
