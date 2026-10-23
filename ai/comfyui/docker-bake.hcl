variable "IMAGE_NAME" {
  type    = string
  default = "ghcr.io/delfianto/comfyui-app"
}

# Build this separately and load it before building ComfyUI.
variable "BASE_IMAGE" {
  type    = string
  default = "ghcr.io/delfianto/comfyui-cuda:13.4.2-base-ubuntu26.04"
}

variable "CUDA_IMAGE" {
  type    = string
  default = "nvidia/cuda:13.4.2-base-ubuntu26.04"
}

variable "TORCH_VERSION" {
  type    = string
  default = "2.11.0"
}

variable "TORCHVISION_VERSION" {
  type    = string
  default = "0.26.0"
}

variable "TORCHAUDIO_VERSION" {
  type    = string
  default = "2.11.0"
}

variable "TORCH_INDEX_URL" {
  type    = string
  default = "https://download.pytorch.org/whl/cu130"
}

variable "COMFYUI_REPOSITORY" {
  type    = string
  default = "https://github.com/Comfy-Org/ComfyUI.git"
}

variable "COMFYUI_REF" {
  type    = string
  default = "latest-stable"
}

group "default" {
  targets = ["comfyui"]
}

# Intentionally independent: --no-cache on ComfyUI must not rebuild this image.
target "base" {
  context    = "."
  dockerfile = "Dockerfile.base"
  platforms  = ["linux/amd64"]
  tags       = [BASE_IMAGE]
  args = {
    CUDA_IMAGE          = CUDA_IMAGE
    TORCH_VERSION       = TORCH_VERSION
    TORCHVISION_VERSION = TORCHVISION_VERSION
    TORCHAUDIO_VERSION  = TORCHAUDIO_VERSION
    TORCH_INDEX_URL     = TORCH_INDEX_URL
  }
  output = ["type=docker"]
}

target "comfyui" {
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = ["linux/amd64"]
  tags       = ["${IMAGE_NAME}:latest", "${IMAGE_NAME}:${COMFYUI_REF}"]
  args = {
    BASE_IMAGE         = BASE_IMAGE
    COMFYUI_REPOSITORY = COMFYUI_REPOSITORY
    COMFYUI_REF        = COMFYUI_REF
  }
  output = ["type=docker"]
}
