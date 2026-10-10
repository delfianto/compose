variable "IMAGE_NAME" {
  type    = string
  default = "ghcr.io/delfianto/comfyui-nvidia-cuda"
}

variable "IMAGE_TAG" {
  type    = string
  default = "latest"
}

variable "CUDA_IMAGE" {
  type    = string
  default = "nvidia/cuda:13.4.2-base-ubuntu24.04"
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

target "comfyui" {
  context    = "."
  dockerfile = "Dockerfile"
  platforms  = ["linux/amd64"]
  tags       = ["${IMAGE_NAME}:${IMAGE_TAG}"]
  args = {
    CUDA_IMAGE                   = CUDA_IMAGE
    TORCH_VERSION                = TORCH_VERSION
    TORCHVISION_VERSION          = TORCHVISION_VERSION
    TORCHAUDIO_VERSION           = TORCHAUDIO_VERSION
    TORCH_INDEX_URL              = TORCH_INDEX_URL
    COMFYUI_REPOSITORY           = COMFYUI_REPOSITORY
    COMFYUI_REF                  = COMFYUI_REF
  }
  output = ["type=docker"]
}
