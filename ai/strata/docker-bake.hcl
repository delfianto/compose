variable "IMAGE_REPO" {
  type    = string
  default = "ghcr.io/delfianto/strata"
}

variable "STRATA_VERSION" {
  type    = string
  default = "v0.1.41"
  validation {
    condition     = can(regex("^v[0-9]+\\.[0-9]+\\.[0-9]+(\\.[0-9]+)?$", STRATA_VERSION))
    error_message = "STRATA_VERSION must be an upstream release tag, such as v0.1.41."
  }
}

variable "CUDA_ARCHITECTURES" {
  type    = string
  default = "86;89"
}

variable "BUILD_VISION" {
  type    = string
  default = "1"
}

group "default" {
  targets = ["strata"]
}

target "strata" {
  context    = "https://github.com/Niko1221/Strata.git#${STRATA_VERSION}"
  dockerfile = "Dockerfile"
  platforms  = ["linux/amd64"]
  tags       = ["${IMAGE_REPO}:${STRATA_VERSION}"]
  args = {
    CUDA_ARCHITECTURES = CUDA_ARCHITECTURES
    BUILD_VISION      = BUILD_VISION
  }
  labels = {
    "org.opencontainers.image.source"  = "https://github.com/Niko1221/Strata"
    "org.opencontainers.image.version" = STRATA_VERSION
  }
  output = ["type=docker"]
}
