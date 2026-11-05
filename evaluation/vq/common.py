"""Shared input and result handling for the three independent VQ scorers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}


def videos(input_root: Path):
    """Yield (relative key, path) for family/task/model/case videos."""
    if not input_root.is_dir():
        raise FileNotFoundError(f"Video directory does not exist: {input_root}")
    for path in sorted(input_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in VIDEO_SUFFIXES:
            continue
        rel = path.relative_to(input_root)
        if len(rel.parts) != 4:
            raise ValueError(f"Expected family/task/model/case.ext: {rel}")
        yield rel.as_posix(), path


def identity(key: str) -> dict:
    family, task, model, filename = Path(key).parts
    return {"path": key, "family": family, "task": task,
            "model": model, "case": Path(filename).stem}


def metadata(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {path}")
    data = {"width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "n_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            "fps": float(cap.get(cv2.CAP_PROP_FPS))}
    cap.release()
    if min(data["width"], data["height"], data["n_frames"]) <= 0:
        raise ValueError(f"Invalid video metadata: {path}: {data}")
    return data


def resize_frame(image, short_edge: int | None = None):
    """Resize a decoded RGB image, preserving aspect ratio and avoiding encoding."""
    if short_edge is None:
        return image
    if isinstance(short_edge, bool) or not isinstance(short_edge, int) or short_edge < 1:
        raise ValueError("short_edge must be a positive integer")
    from PIL import Image

    width, height = image.size
    if min(width, height) == short_edge:
        return image
    scale = short_edge / min(width, height)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, resample=Image.Resampling.LANCZOS)


def frame_resize_protocol(short_edge: int | None) -> dict:
    """Keep the native protocol unchanged so running native jobs can resume."""
    if short_edge is None:
        return {}
    if isinstance(short_edge, bool) or not isinstance(short_edge, int) or short_edge < 1:
        raise ValueError("short_edge must be a positive integer")
    return {"frame_resize": {"short_edge": short_edge, "keep_aspect_ratio": True,
                             "resample": "PIL.LANCZOS", "stage": "decoded_sampled_rgb_frames"}}


def frame_images(path: Path, count: int, *, short_edge: int | None = None):
    """Uniform frame sampling including first and last frames, in RGB order."""
    import numpy as np
    from PIL import Image

    info = metadata(path)
    indices = np.linspace(0, info["n_frames"] - 1,
                          min(count, info["n_frames"]), dtype=int).tolist()
    cap = cv2.VideoCapture(str(path))
    frames = []
    try:
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, bgr = cap.read()
            if not ok:
                raise ValueError(f"Frame {index} could not be decoded: {path}")
            frame = Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
            frames.append(resize_frame(frame, short_edge))
    finally:
        cap.release()
    return indices, frames, info


def seed_for(key: str, base_seed: int) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return (base_seed + int.from_bytes(digest[:4], "big")) % (2**32)


def completed(output: Path, protocol: dict) -> set[str]:
    if not output.exists():
        return set()
    # Directory aliases may change during a dataset move. Compare their resolved
    # roots while retaining strict equality for every scoring setting.
    protocol = dict(protocol)
    protocol["input_root"] = str(Path(protocol["input_root"]).resolve())
    done = set()
    with output.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            recorded_protocol = row.get("protocol")
            if isinstance(recorded_protocol, dict) and recorded_protocol.get("input_root"):
                recorded_protocol = {**recorded_protocol,
                                     "input_root": str(Path(recorded_protocol["input_root"]).resolve())}
            if recorded_protocol != protocol:
                raise ValueError(f"Existing output uses a different protocol: {output}. Use a new --output file.")
            if row.get("status") == "ok":
                done.add(row["path"])
    return done


def append_jsonl(output: Path, row: dict) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        stream.flush()
