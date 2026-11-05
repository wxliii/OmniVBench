"""Score physics through an upstream-deployed UnifiedReward Qwen3.5 service."""
from __future__ import annotations

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
import re
import tempfile
import time

import cv2
from PIL import Image
import requests

from common import ROOT, append_jsonl, completed, identity, metadata, videos


MODEL = "CodeGoat24/UnifiedReward-2.0-qwen35-9b"


PROMPT = (
    "You are presented with a generated video and its associated text caption. "
    "Your task is to analyze the video across multiple dimensions in relation to the caption. Specifically:\n"
    "Provide overall assessments for the video along the following axes (each rated from 1 to 5):\n"
    "- Alignment Score: How well the video matches the caption in terms of content.\n"
    "- Physics Score: How well the gravity, movements, collisions, and interactions make physical sense.\n"
    "- Style Score: How visually appealing the video looks, regardless of caption accuracy.\n\n"
    "Output your evaluation using the format below:\n\n"
    "Alignment Score (1-5): X\nPhysics Score (1-5): Y\nStyle Score (1-5): Z\n\n"
    "Your task is provided as follows:\nText Caption: []"
)


HTTP_FIELDS = {"model": "UnifiedReward", "do_sample": False, "max_tokens": 4096}


def parse_physics(text):
    match = re.search(r"Physics Score\s*\(1\s*[-–]\s*5\)\s*:\s*([0-9]+(?:\.[0-9]+)?)", text, re.I)
    if not match:
        # Accept only a missing/mistyped closing parenthesis on a complete score line.
        # The number must remain explicit and in range; do not infer or clamp scores.
        match = re.search(r'^\s*Physics Score[ \t]*\(1[ \t]*[-–][ \t]*5(?:\)|")?[ \t]*:[ \t]*([0-9]+(?:\.[0-9]+)?)[ \t]*$', text, re.I | re.M)
    if not match or not 1 <= float(match[1]) <= 5:
        raise ValueError(f"Invalid Physics Score: {text[:500]!r}")
    return float(match[1])


def extract_frames(path, directory):
    """Sequential OpenCV decode and default imwrite, following the upstream pipeline."""
    info = metadata(path)
    selected = [int(i * info["n_frames"] / 16) for i in range(16)]
    wanted = set(selected)
    indices, images = [], []
    cap = cv2.VideoCapture(str(path))
    index = 0
    try:
        while cap.isOpened():
            ok, frame = cap.read()
            if not ok:
                break
            if index in wanted:
                dest = Path(directory) / f"video_frame_{len(images):03d}.jpg"
                if not cv2.imwrite(str(dest), frame):
                    raise ValueError(f"Failed to write frame {index}")
                indices.append(index)
                images.append(str(dest))
            index += 1
            if len(images) >= 16:
                break
    finally:
        cap.release()
    if indices != sorted(wanted):
        raise ValueError(f"Incomplete frame decoding: expected {sorted(wanted)}, got {indices}")
    return images, indices, info


def build_messages(images):
    content = []
    for path in images:
        with Image.open(path) as source:
            buffer = BytesIO()
            source.convert("RGB").save(buffer, format="JPEG", quality=95)
        content.append({"type": "image_url", "image_url": {
            "url": "data:image/jpeg;base64," + base64.b64encode(buffer.getvalue()).decode("utf-8")}})
    content.append({"type": "text", "text": PROMPT})
    return [{"role": "user", "content": content}]


def request_score(api_url, messages, timeout):
    payload = {**HTTP_FIELDS, "messages": messages}
    response = requests.post(f"{api_url}/v1/chat/completions", json=payload, timeout=timeout)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text[:2000]}")
    return response.json()


def score_one(key, root, api_url, protocol, timeout):
    started = time.monotonic()
    row = {**identity(key), "metric": "physics", "checkpoint": MODEL,
           "protocol": protocol}
    try:
        with tempfile.TemporaryDirectory(prefix="vq-frames-") as directory:
            images, indices, info = extract_frames(root / key, directory)
            row.update(info)
            row.update(sampled_indices=indices, n_sampled=len(images))
            reply = request_score(api_url, build_messages(images), timeout)
            choice = reply["choices"][0]
            text = choice["message"]["content"]
            row.update(physics_response=text, api_response=reply)
            if choice.get("finish_reason") != "stop":
                raise ValueError(f"Incomplete response: {choice.get('finish_reason')}")
            row.update(physics_raw=parse_physics(text), status="ok")
    except Exception as exc:
        row.update(status="error", error=str(exc))
    row["elapsed_seconds"] = round(time.monotonic() - started, 3)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "results/physics.jsonl")
    parser.add_argument("--api-url", default="http://localhost:8080",
                        help="Base URL of the upstream UnifiedReward service")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=1800)
    args = parser.parse_args()
    protocol = {"metric": "physics", "input_root": str(args.input_root.resolve()),
                "checkpoint": MODEL, "frames": 16, "http_fields": HTTP_FIELDS}
    done = completed(args.output, protocol)
    pending = [key for key, _ in videos(args.input_root) if key not in done]
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        rows = executor.map(lambda key: score_one(key, args.input_root, args.api_url.rstrip("/"),
                                                 protocol, args.timeout), pending)
        for row in rows:
            append_jsonl(args.output, row)
            print(f"{row['status']} {row['path']}: {row.get('physics_raw', row.get('error'))}", flush=True)


if __name__ == "__main__":
    main()
