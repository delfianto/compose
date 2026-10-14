"""Load local Krea 2 components and compatible community checkpoint repacks.

Imported by toolkit-local-models.pth. Stays lazy: torch is not loaded until
ai-toolkit imports the VAE / text-encoder modules.
"""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.machinery
import json
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


class FloatingTensor(Protocol):
    def __mul__(self, other: object) -> object: ...


class QuantizedTensor(Protocol):
    def float(self) -> FloatingTensor: ...
    def tolist(self) -> list[int]: ...


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


def _patch_krea(mod: ModuleType) -> None:
    cls = cast(LocalModelClass, mod.SingleStreamDiT)
    orig = cls.convert_state_dict_on_load.__func__

    def convert(c: type[object], state_dict: StateDict) -> StateDict:
        state_dict = orig(c, state_dict)
        # Some RAW repacks carry these auxiliary matrices (and quant markers).
        # Neither the official LastLayer nor ComfyUI uses them. The quantized
        # importer otherwise tries to attach them as nonexistent Linear layers.
        # Preserve every other key so the upstream strict load still checks
        # missing weights, shapes and unexpected tensors.
        skipped = {
            key for key in state_dict if key.startswith(("last.down.", "last.up."))
        }
        if skipped:
            print(
                f"Skipping {len(skipped)} auxiliary Krea2 last.down/last.up tensors",
                flush=True,
            )
        converted = {
            key: value for key, value in state_dict.items() if key not in skipped
        }
        # This 12 -> 1 layer is explicitly excluded from toolkit quantization,
        # but a repack may already quantize it. _int_mm cannot accept K=12.
        # Decode its plain per-row INT8 weights exactly; leave all large layers
        # in their encoded format. The checkpoint on disk remains unchanged.
        prefix = "txtfusion.projector"
        marker = prefix + ".comfy_quant"
        if marker in converted:
            quant_config = json.loads(
                bytes(cast(QuantizedTensor, converted[marker]).tolist()).decode()
            )
            if quant_config.get("format") != "int8_tensorwise" or quant_config.get(
                "convrot"
            ):
                raise ValueError(
                    "Unsupported quantization for Krea2's tiny text projector"
                )
            weight_key, scale_key = prefix + ".weight", prefix + ".weight_scale"
            converted[weight_key] = (
                cast(QuantizedTensor, converted[weight_key]).float()
                * converted[scale_key]
            )
            del converted[scale_key], converted[marker]
            print("Decoded tiny Krea2 text projector to floating point", flush=True)
        return converted

    cls.convert_state_dict_on_load = classmethod(convert)


_PATCHERS: dict[str, Callable[[ModuleType], None]] = {
    "toolkit.models.v2.vae.qwen_image": _patch_vae,
    "toolkit.models.v2.text_encoders.qwen3_vl": _patch_te,
    "extensions_built_in.diffusion_models.krea2.src.mmdit": _patch_krea,
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
