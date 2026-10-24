variable "IMAGE_NAME" { default = "ghcr.io/delfianto/lychee" }
variable "LYCHEE_REPOSITORY" { default = "https://github.com/delfianto/lychee.git" }
variable "LYCHEE_REF" { default = "v0.1.0-beta.2" }
variable "LYCHEE_IMAGE_TAG" { default = "v0.1.0-beta.2" }
variable "LYCHEE_VERSION" { default = "0.1.0-beta.2" }
variable "PYTHON_IMAGE" { default = "python:3.14-slim-trixie" }
variable "NODE_IMAGE" { default = "node:24-trixie-slim" }
variable "BUN_IMAGE" { default = "oven/bun:1.4.4" }
variable "UV_IMAGE" { default = "ghcr.io/astral-sh/uv:latest" }

group "default" {
  targets = ["lychee"]
}

target "lychee" {
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = ["linux/amd64"]
  tags       = ["${IMAGE_NAME}:latest", "${IMAGE_NAME}:${LYCHEE_IMAGE_TAG}"]
  args = {
    LYCHEE_REPOSITORY = LYCHEE_REPOSITORY
    LYCHEE_REF        = LYCHEE_REF
    LYCHEE_VERSION    = LYCHEE_VERSION
    PYTHON_IMAGE     = PYTHON_IMAGE
    NODE_IMAGE       = NODE_IMAGE
    BUN_IMAGE        = BUN_IMAGE
    UV_IMAGE         = UV_IMAGE
  }
  output = ["type=docker"]
}
