"""Prefer ComfyUI-local Krea 2 extras over Hugging Face weight downloads.

Imported by toolkit-local-models.pth. Stays lazy: torch is not loaded until
ai-toolkit imports the VAE / text-encoder modules.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import sys
from collections.abc import Callable, Sequence
from types import ModuleType
from typing import Protocol, cast

from typing_extensions import override

StateDict = dict[str, object]
WeightCandidates = dict[str | tuple[str, str], list[str]]


class BoundConverter(Protocol):
    @property
    def __func__(self) -> Callable[[type[object], StateDict], StateDict]: ...


class LocalModelClass(Protocol):
    aitk_comfy_repo: str | None
    aitk_comfy_weight_names: WeightCandidates
    convert_state_dict_on_load: BoundConverter


class ExecutableLoader(Protocol):
    exec_module: Callable[[ModuleType], None]


def _patch_vae(mod: ModuleType) -> None:
    cls = cast(LocalModelClass, mod.QwenImageVAE)
    files = ["vae/qwen-image-vae-bf16.safetensors"]
    cls.aitk_comfy_repo = "local"
    cls.aitk_comfy_weight_names = {
        "Qwen/Qwen-Image": files,
        ("Qwen/Qwen-Image", "vae"): files,
    }
    orig = cls.convert_state_dict_on_load.__func__

    def convert(c: type[object], state_dict: StateDict) -> StateDict:
        if any(
            k == "conv1.weight" or k.startswith("decoder.middle") for k in state_dict
        ):
            # This dependency exists in the toolkit container, not on the host.
            module = importlib.import_module("diffusers.loaders.single_file_utils")
            converter = cast(
                Callable[[StateDict], StateDict],
                module.convert_wan_vae_to_diffusers,
            )
            return converter(state_dict)
        return orig(c, state_dict)

    cls.convert_state_dict_on_load = classmethod(convert)


def _patch_te(mod: ModuleType) -> None:
    cls = cast(LocalModelClass, mod.Qwen3VLTextEncoder)
    cls.aitk_comfy_repo = "local"
    cls.aitk_comfy_weight_names = {
        "Qwen/Qwen3-VL-4B-Instruct": ["clip/qwen3-vl-4b-fp8-scaled.safetensors"],
    }


_PATCHERS: dict[str, Callable[[ModuleType], None]] = {
    "toolkit.models.v2.vae.qwen_image": _patch_vae,
    "toolkit.models.v2.text_encoders.qwen3_vl": _patch_te,
}


class _Finder(importlib.abc.MetaPathFinder):
    @override
    def find_spec(
        self,
        fullname: str,
        path: Sequence[str] | None,
        target: ModuleType | None = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname not in _PATCHERS:
            return None
        spec = importlib.machinery.PathFinder.find_spec(fullname, path, target)
        if spec is None or spec.loader is None:
            return None
        loader = cast(ExecutableLoader, spec.loader)
        orig_exec = loader.exec_module
        patch = _PATCHERS[fullname]

        def exec_module(module: ModuleType) -> None:
            orig_exec(module)
            patch(module)

        loader.exec_module = exec_module
        return spec


sys.meta_path.insert(0, _Finder())
