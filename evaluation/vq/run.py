"""Run one OmniVBench VQ component on the supplied video tree."""

from __future__ import annotations

import argparse
import hashlib
import math
import random
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import torch

from common import ROOT, append_jsonl, completed, frame_images, frame_resize_protocol, identity, metadata, seed_for, videos

WEIGHTS = ROOT / "weights"
UPSTREAM = ROOT / "upstream"

# Official dover.yml technical view (val-l1080p).
DEFAULT_TECHNICAL_OPTIONS = {
    "fragments_h": 7, "fragments_w": 7, "fsize_h": 32, "fsize_w": 32,
    "aligned": 32, "clip_len": 32, "frame_interval": 2, "num_clips": 3,
}


def uniform_frame_indices(total_frames: int, clip_len: int, num_clips: int) -> np.ndarray:
    """Sample the complete video uniformly, retaining repeats for short videos."""
    if total_frames < 1 or clip_len < 1 or num_clips < 1:
        raise ValueError("Frame and clip counts must be positive")
    return np.linspace(0, total_frames - 1, clip_len * num_clips, dtype=int)


def make_technical(
    device: str,
    technical_options: dict | None = None,
    temporal_policy: str = "official",
    *,
    decoder_threads: int | None = None,
    target_fps: float | None = None,
):
    """Build DOVER++ technical scoring with optional preprocessing ablations.

    The default follows the author's technical view unchanged. Callers seed
    Python, NumPy and PyTorch before scoring, as in ``main`` below.
    ``upsample`` sets the short edge through the author's decoded-frame resize.
    """
    allowed = {"clip_len", "num_clips", "frame_interval", "aligned", "upsample",
               "fragments_h", "fragments_w", "fsize_h", "fsize_w"}
    overrides = dict(technical_options or {})
    unknown = overrides.keys() - allowed
    if unknown:
        raise ValueError(f"Unknown technical options: {sorted(unknown)}")
    if temporal_policy not in {"official", "uniform"}:
        raise ValueError(f"Unknown temporal policy: {temporal_policy!r}")
    for name, value in overrides.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"{name} must be an integer")
        if value <= 0 and not (name == "upsample" and value == -1):
            raise ValueError(f"{name} must be positive (or -1 for native upsample)")
    if decoder_threads is not None and (
        isinstance(decoder_threads, bool) or not isinstance(decoder_threads, int)
        or decoder_threads < 1
    ):
        raise ValueError("decoder_threads must be a positive integer or None")
    if target_fps is not None and (
        isinstance(target_fps, bool) or not isinstance(target_fps, (int, float))
        or not math.isfinite(target_fps) or target_fps <= 0
    ):
        raise ValueError("target_fps must be finite and positive or None")
    import yaml

    dover_root = UPSTREAM / "DOVER"
    sys.path.insert(0, str(dover_root))
    from dover.datasets import UnifiedFrameSampler, spatial_temporal_view_decomposition
    from dover.models import DOVER
    from dover.models import evaluator as dover_evaluator

    # DOVER's constructor fetches ImageNet ConvNeXt weights even though the
    # complete DOVER checkpoint immediately replaces every parameter. Suppress
    # that redundant fetch so all required assets stay under VQ/weights.
    original_convnext = dover_evaluator.convnext_3d_tiny
    def local_convnext(**kwargs):
        kwargs["pretrained"] = False
        return original_convnext(**kwargs)
    with (dover_root / "dover.yml").open() as stream:
        options = yaml.safe_load(stream)
    opt = dict(options["data"]["val-l1080p"]["args"]["sample_types"]["technical"])
    opt.update(overrides)
    if opt["clip_len"] % opt["aligned"]:
        raise ValueError("clip_len must be divisible by aligned")
    dover_evaluator.convnext_3d_tiny = local_convnext
    try:
        model = DOVER(**options["model"]["args"])
    finally:
        dover_evaluator.convnext_3d_tiny = original_convnext
    checkpoint = WEIGHTS / "DOVER_plus_plus.pth"
    # The author's checkpoint embeds NumPy scalars, which PyTorch's restricted
    # loader rejects; load the complete checkpoint from the local weights folder.
    bundle = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model.load_state_dict(bundle["state_dict"], strict=True)
    model = model.to(device).eval()
    sample_types = {"technical": opt}
    if temporal_policy == "official":
        sampler = UnifiedFrameSampler(opt["clip_len"], opt["num_clips"], opt["frame_interval"])
    else:
        def sampler(total_frames, train=False):
            return uniform_frame_indices(total_frames, opt["clip_len"], opt["num_clips"])
    mean = torch.tensor([123.675, 116.28, 103.53])
    std = torch.tensor([58.395, 57.12, 57.375])

    def score(path: Path, _: int) -> dict:
        fps_metadata = {}
        if target_fps is not None and str(path).endswith(".yuv"):
            raise ValueError("target_fps requires a video container with FPS metadata")
        if target_fps is None and (decoder_threads is None or str(path).endswith(".yuv")):
            views, indices = spatial_temporal_view_decomposition(
                str(path), sample_types, {"technical": sampler})
            view = views["technical"]
        else:
            # Match the official unique-frame decoding and spatial transform,
            # with an explicit per-worker thread limit for parallel ablations.
            import decord
            from dover.datasets.dover_datasets import get_spatial_fragments

            decord.bridge.set_bridge("torch")
            reader_options = {"num_threads": decoder_threads} if decoder_threads is not None else {}
            reader = decord.VideoReader(str(path), **reader_options)
            if target_fps is None:
                frame_indices = sampler(len(reader), False)
            else:
                source_fps = float(reader.get_avg_fps())
                if not math.isfinite(source_fps) or source_fps <= 0:
                    raise ValueError(f"Invalid source FPS: {source_fps}")
                virtual_count = max(1, round(len(reader) * target_fps / source_fps))
                virtual_indices = sampler(virtual_count, False)
                frame_indices = np.floor(virtual_indices * source_fps / target_fps).astype(np.int64)
                frame_indices = np.clip(frame_indices, 0, len(reader) - 1)
                fps_metadata = {"source_fps": source_fps, "target_fps": target_fps,
                                "virtual_frame_count": virtual_count,
                                "virtual_sampled_indices": virtual_indices.tolist()}
            frames = {index: reader[index] for index in np.unique(frame_indices)}
            video = torch.stack([frames[index] for index in frame_indices], 0).permute(3, 0, 1, 2)
            view = get_spatial_fragments(video, **opt)
            indices = {"technical": frame_indices}
        clips = opt["num_clips"]
        view = ((view.permute(1, 2, 3, 0) - mean) / std).permute(3, 0, 1, 2)
        view = view.reshape(view.shape[0], clips, -1, *view.shape[2:]).transpose(0, 1).to(device)
        with torch.inference_mode():
            raw = float(model({"technical": view})[0].mean().item())
        if not math.isfinite(raw):
            raise ValueError("DOVER++ returned a non-finite score")
        return {"technical_raw": raw, "sampled_indices": indices["technical"].tolist(),
                "checkpoint": "DOVER++ (teowu/DOVER), technical branch", **fps_metadata}

    return score


def make_aesthetic(device: str, dtype: str, n_frames: int, short_edge: int | None = None):
    sys.path.insert(0, str(UPSTREAM / "aesthetic-predictor-v2-5" / "src"))
    from aesthetic_predictor_v2_5 import convert_v2_5_from_siglip

    model, processor = convert_v2_5_from_siglip(
        predictor_name_or_path=WEIGHTS / "aesthetic_predictor_v2_5.pth",
        encoder_model_name=str(WEIGHTS / "siglip-so400m-patch14-384"),
        local_files_only=True,
    )
    torch_dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float32
    model = model.to(device=device, dtype=torch_dtype).eval()

    def score(path: Path, _: int) -> dict:
        indices, frames, _ = frame_images(path, n_frames, short_edge=short_edge)
        batch = processor(images=frames, return_tensors="pt").pixel_values.to(device=device, dtype=torch_dtype)
        with torch.inference_mode():
            values = model(batch).logits.flatten().float().cpu().tolist()
        if not all(math.isfinite(v) for v in values):
            raise ValueError("Aesthetic Predictor returned a non-finite score")
        return {"aes_v25_mean": float(np.mean(values)),
                "aes_v25_median": float(np.median(values)),
                "aes_v25_std": float(np.std(values)),
                "aes_v25_min": float(min(values)), "aes_v25_max": float(max(values)),
                "n_sampled": len(values), "sampled_indices": indices,
                "checkpoint": "Aesthetic Predictor V2.5 + SigLIP-so400m-patch14-384",
                **({"sampled_width": frames[0].width, "sampled_height": frames[0].height}
                   if short_edge is not None else {})}

    return score


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metric", choices=["technical", "aesthetic"])
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--device", default="cuda:0" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--dtype", choices=["bfloat16", "float32"], default="bfloat16")
    parser.add_argument("--frames", type=int, help="Number of aesthetic frames (default: 8)")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--num-shards", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--short-edge", type=int,
                        help="Resize sampled RGB frames before model preprocessing; aesthetic only")
    args = parser.parse_args()
    if args.num_shards < 1 or not 0 <= args.shard_index < args.num_shards:
        parser.error("Require --num-shards >= 1 and 0 <= --shard-index < --num-shards")
    if not args.input_root.is_dir():
        parser.error(f"Input directory does not exist: {args.input_root}")
    if args.frames is not None and args.frames < 1:
        parser.error("--frames must be positive")
    if args.short_edge is not None and (args.short_edge < 1 or args.metric == "technical"):
        parser.error("--short-edge must be positive and is supported for aesthetic only")
    output = args.output or ROOT / "results" / f"{args.metric}.jsonl"
    protocol = {"metric": args.metric,
                "input_root": str(args.input_root.resolve()),
                "seed": args.seed, "frames": args.frames or (8 if args.metric == "aesthetic" else 0),
                "dtype": args.dtype if args.metric == "aesthetic" else None,
                "max_pixels": None, "max_new_tokens": None,
                **frame_resize_protocol(args.short_edge)}
    done = completed(output, protocol)
    if args.metric == "technical":
        scorer = make_technical(args.device)
    else:
        scorer = make_aesthetic(args.device, args.dtype, args.frames or 8, args.short_edge)
    count = 0
    for index, (key, path) in enumerate(videos(args.input_root)):
        if index % args.num_shards != args.shard_index:
            continue
        if key in done:
            continue
        if args.limit is not None and count >= args.limit:
            break
        count += 1
        row = identity(key)
        row["protocol"] = protocol
        started = time.perf_counter()
        try:
            info = metadata(path)
            row.update(info)
            with path.open("rb") as stream:
                row["input_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
            seed = seed_for(key, args.seed)
            random.seed(seed)
            np.random.seed(seed)
            torch.manual_seed(seed)
            row.update(scorer(path, seed))
            row.update({"status": "ok", "seed": seed, "metric": args.metric})
            print(f"OK {args.metric}: {key}", flush=True)
        except Exception as exc:
            row.update({"status": "error", "error": str(exc),
                        "traceback": traceback.format_exc(limit=5), "metric": args.metric})
            print(f"ERROR {args.metric}: {key}: {exc}", file=sys.stderr, flush=True)
        row["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        append_jsonl(output, row)


if __name__ == "__main__":
    main()
