from __future__ import annotations

import base64
import io
import hashlib
import math
import json
import subprocess
import tempfile
import threading
from collections import OrderedDict
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageOps

from core import ROOT, reference_roles, sha256

cv2.setNumThreads(1)

# Reuse the same encoded reference frames across generated models in this run.
_REFERENCE_FRAMES = OrderedDict()
_REFERENCE_LOCK = threading.RLock()
_REFERENCE_CACHE_SIZE = 64

ALIGNED = {'action_reference', 'camera_reference', 'greybox', 'lineart',
           'mr2v_content_motion', 'multi_reference_lineart'}
ROUGH = {'rough_storyboard', 'multi_reference_storyboard'}
DEFAULT_ANCHORS_DIR = ROOT / 'storyboard_anchors'


class VideoDecodeError(ValueError):
    """The fast decoder could not provide trustworthy frames and times."""


def presentation_timeline(path: Path) -> dict:
    """Count display frames and retain their actual times, including variable-rate clips."""
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height:frame=best_effort_timestamp_time',
        '-of', 'json', str(path)], capture_output=True, text=True, timeout=120, check=True)
    data = json.loads(probe.stdout)
    frames = data.get('frames', [])
    if not frames or any('best_effort_timestamp_time' not in f for f in frames):
        raise VideoDecodeError(f'Missing display timestamps: {path}')
    pts = [float(f['best_effort_timestamp_time']) for f in frames]
    if not all(math.isfinite(t) for t in pts) or any(b <= a for a, b in zip(pts, pts[1:])):
        raise VideoDecodeError(f'Invalid display timestamp order: {path}')
    stream = data['streams'][0]
    times = [t - pts[0] for t in pts]
    step = float(np.median(np.diff(pts))) if len(pts) > 1 else 0
    if step <= 0:
        raise VideoDecodeError(f'Insufficient display timeline: {path}')
    return {'frames': len(pts), 'fps': 1 / step, 'duration': times[-1] + step,
            'width': int(stream['width']), 'height': int(stream['height']),
            'times': times, 'presentation_origin_seconds': pts[0]}


def temporal_positions(timeline: dict, count: int) -> list[int]:
    times = np.asarray(timeline['times'])
    targets = np.linspace(0, times[-1], min(count, len(times)))
    return sorted(set(int(np.argmin(np.abs(times - t))) for t in targets))


def extract_display_frames(path: Path, indices: list[int], max_side: int, timeline: dict):
    """Decode the selected display indices losslessly before the usual JPEG encoding."""
    if not indices or indices != sorted(set(indices)) or any(not 0 <= i < timeline['frames'] for i in indices):
        raise ValueError(f'Invalid display indices: {path}')
    select = '+'.join(f'eq(n\\,{i})' for i in indices)
    with tempfile.TemporaryDirectory(prefix='rfir-frames-') as directory:
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-threads', '1', '-i', str(path),
            '-map', '0:v:0', '-vf', 'select=' + select, '-vsync', '0', '-threads', '1',
            str(Path(directory) / '%04d.png')], capture_output=True, timeout=120, check=True)
        paths = sorted(Path(directory).glob('*.png'))
        if len(paths) != len(indices):
            raise VideoDecodeError(f'Missing selected display frames: {path}')
        frames = []
        for index, image_path in zip(indices, paths):
            with Image.open(image_path) as im:
                part, encoding = image_part(im, max_side)
            timestamp = timeline['times'][index]
            frames.append((part, {'frame_index': index, 'timestamp_seconds': timestamp,
                'normalized_position': timestamp / timeline['times'][-1], **encoding,
                'decoder_mode': 'ffmpeg_display_timeline',
                'presentation_origin_seconds': timeline['presentation_origin_seconds']}))
        return frames


def positions(n: int, count: int) -> list[int]:
    if n < 1 or count < 1:
        raise ValueError('Positive video length and frame count required')
    return sorted(set(int(round(x)) for x in np.linspace(0, n - 1, min(n, count))))


def video_info(path: Path) -> dict:
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    try:
        if not cap.isOpened():
            raise ValueError(f'Cannot open video: {path}')
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = float(cap.get(cv2.CAP_PROP_FPS))
        w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if min(n, w, h) <= 0 or not math.isfinite(fps) or fps <= 0:
            raise ValueError(f'Invalid video metadata: {path}')
        return {'frames': n, 'fps': fps, 'duration': n / fps, 'width': w, 'height': h}
    finally:
        cap.release()


def ordinary_count(info: dict) -> int:
    return min(20, max(8, math.ceil(info['duration'] * 2)))


def image_part(im: Image.Image, max_side: int) -> tuple[dict, dict]:
    im = ImageOps.exif_transpose(im).convert('RGB')
    source_size = im.size
    if max_side > 0:
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    f = io.BytesIO()
    im.save(f, format='JPEG', quality=90)
    data = f.getvalue()
    info = {'source_size': list(source_size), 'encoded_size': list(im.size),
            'jpeg_sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' +
            base64.b64encode(data).decode('ascii')}}, info


def _extract_seek(path: Path, indices: list[int], max_side: int) -> list[tuple[dict, dict]]:
    info = video_info(path)
    if not indices or indices != sorted(set(indices)) or any(type(i) is not int or not 0 <= i < info['frames'] for i in indices):
        raise ValueError(f'Invalid frame indices: {path}: {indices}')
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    frames = []
    try:
        for index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f'Failed decoding {path}, frame {index}')
            actual = int(round(cap.get(cv2.CAP_PROP_POS_FRAMES))) - 1
            if actual != index:
                raise ValueError(f'Inexact seek {path}: {index} -> {actual}')
            part, encoding = image_part(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), max_side)
            frames.append((part, {'frame_index': index, 'timestamp_seconds': cap.get(cv2.CAP_PROP_POS_MSEC) / 1000,
                                  'normalized_position': index / max(1, info['frames'] - 1), **encoding}))
            timestamp = frames[-1][1]['timestamp_seconds']
            if not math.isfinite(timestamp) or abs(timestamp - index / info['fps']) > max(.02, .75 / info['fps']):
                raise ValueError(f'Variable/invalid frame timestamps need temporal resampling: {path}, frame {index}')
    finally:
        cap.release()
    return frames


def _extract_sequential(path: Path, indices: list[int], max_side: int):
    """Recover B-frame timestamp/seek problems using display PTS and sequential decoding."""
    info = video_info(path)
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0',
        '-read_intervals', '%+#3', '-show_entries', 'frame=best_effort_timestamp_time',
        '-of', 'json', str(path)], capture_output=True, text=True, timeout=30, check=True)
    pts = json.loads(probe.stdout)['frames']
    origin = float(pts[0]['best_effort_timestamp_time'])
    if not math.isfinite(origin): raise ValueError(f'Invalid presentation origin: {path}')
    cap = cv2.VideoCapture(str(path), cv2.CAP_FFMPEG, [cv2.CAP_PROP_N_THREADS, 1])
    wanted, frames = set(indices), []
    try:
        for index in range(indices[-1] + 1):
            ok, frame = cap.read()
            if not ok: raise ValueError(f'Incomplete sequential decode: {path}, frame {index}')
            if index not in wanted: continue
            raw = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            # OpenCV can expose the first packet's DTS instead of its display PTS.
            timestamp = 0.0 if index == 0 else raw - origin
            if not math.isfinite(timestamp) or abs(timestamp - index / info['fps']) > max(.02, .75 / info['fps']):
                raise ValueError(f'Variable presentation timestamps require temporal resampling: {path}, frame {index}')
            part, encoding = image_part(Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), max_side)
            frames.append((part, {'frame_index': index, 'timestamp_seconds': timestamp,
                'normalized_position': index / max(1, info['frames'] - 1), **encoding,
                'decoder_mode': 'sequential_fallback', 'raw_decoder_timestamp_seconds': raw,
                'presentation_origin_seconds': origin}))
    finally: cap.release()
    if len(frames) != len(indices): raise ValueError(f'Missing sequential samples: {path}')
    return frames


def extract(path: Path, indices: list[int], max_side: int):
    try:
        return _extract_seek(path, indices, max_side)
    except ValueError as exc:
        if not any(word in str(exc) for word in ('Inexact seek', 'frame timestamps', 'Failed decoding')):
            raise
        try:
            return _extract_sequential(path, indices, max_side)
        except (ValueError, IndexError, subprocess.SubprocessError) as fallback_error:
            raise VideoDecodeError(f'Fast decode needs display timeline: {path}') from fallback_error


def fixed_reference_frames(bundle: Path, case_id: str, ref_index: int, source: dict):
    """Load the reviewed JPEG bytes and their original frame times."""
    manifest_path = bundle / 'manifest.json'
    rows = json.loads(manifest_path.read_text())
    matches = [r for r in rows if r['case_id'] == case_id and r['reference_video_index'] == ref_index]
    if len(matches) != 1:
        raise ValueError(f'Missing or duplicate fixed anchors for {case_id}, reference {ref_index}')
    row = matches[0]
    if row['source_video'] != source['path'] or row['source_frame_count'] != source['frames']:
        raise ValueError(f'Fixed anchors do not match reference video for {case_id}, reference {ref_index}')
    if not math.isclose(row['fps'], source['fps'], rel_tol=1e-4):
        raise ValueError(f'Fixed anchors have a different reference frame rate for {case_id}, reference {ref_index}')
    anchors = row['anchors']
    indices = [a['frame_index'] for a in anchors]
    if not indices or indices != sorted(set(indices)) or any(not 0 <= i < source['frames'] for i in indices):
        raise ValueError(f'Invalid fixed anchor indices for {case_id}, reference {ref_index}')
    frames = []
    bundle_digest = sha256(manifest_path)
    for anchor in anchors:
        path = bundle / anchor['image']
        data = path.read_bytes()
        with Image.open(io.BytesIO(data)) as im:
            size = list(im.size)
        part = {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' +
                base64.b64encode(data).decode('ascii')}}
        info = {key: anchor[key] for key in ('frame_index', 'timestamp_seconds', 'normalized_position')}
        info.update(source_size=[source['width'], source['height']], encoded_size=size,
                    jpeg_sha256=hashlib.sha256(data).hexdigest(), bytes=len(data),
                    anchor_bundle_manifest_sha256=bundle_digest)
        frames.append((part, info))
    return frames


def prepare_evidence(root: Path, case: dict, output: Path, max_side: int = 1024,
                     anchors: dict | None = None,
                     anchors_dir: Path = DEFAULT_ANCHORS_DIR) -> tuple[list[dict], dict]:
    try:
        return _prepare_evidence(root, case, output, max_side, anchors, anchors_dir)
    except VideoDecodeError as exc:
        parts, manifest = _prepare_evidence(root, case, output, max_side, anchors, anchors_dir,
                                          display_timeline=True)
        manifest['decoder_fallback_reason'] = str(exc)
        return parts, manifest


def reference_frames(path: Path, indices: list[int], max_side: int, timeline=None):
    key = (str(path.resolve()), tuple(indices), max_side, timeline is not None)
    with _REFERENCE_LOCK:
        if key not in _REFERENCE_FRAMES:
            frames = (extract_display_frames(path, indices, max_side, timeline)
                      if timeline is not None else extract(path, indices, max_side))
            _REFERENCE_FRAMES[key] = frames
            if len(_REFERENCE_FRAMES) > _REFERENCE_CACHE_SIZE:
                _REFERENCE_FRAMES.popitem(last=False)
        _REFERENCE_FRAMES.move_to_end(key)
        return _REFERENCE_FRAMES[key]


def _prepare_evidence(root, case, output, max_side, anchors, anchors_dir, *, display_timeline=False):
    """Prepare ordered judge images and provenance for one generated video.

    Rough storyboards use fixed reference JPEGs by default; a nonempty
    ``anchors`` mapping explicitly requests fresh decoding at those indices.
    Generated video frames are always sampled independently.
    """
    inputs, roles = case['inputs'], reference_roles(case)
    timelines = {}
    def info_for(path):
        if not display_timeline: return video_info(path)
        timeline = presentation_timeline(path)
        timelines[path] = timeline
        return {k: v for k, v in timeline.items() if k != 'times'}
    def choose(path, info, count):
        return temporal_positions(timelines[path], count) if display_timeline else positions(info['frames'], count)
    def decode(path, indices):
        return extract_display_frames(path, indices, max_side, timelines[path]) if display_timeline else extract(path, indices, max_side)
    task = case['task_id']
    mode = 'aligned' if task in ALIGNED else 'rough' if task in ROUGH else 'continuation' if task == 'continuation' else 'nonaligned'
    parts, manifest = [], {'mode': mode, 'media': [], 'items': [], 'max_side': max_side,
                          'timing_note': 'Frame order and normalized positions are provided. Durations may differ; absolute speed is comparable only through the recorded timestamps, not paired frame spacing alone. Sparse frames cannot prove absence of brief events or exact frequencies.'}
    def add(label, part, info):
        parts.extend([{'type': 'text', 'text': label}, part])
        manifest['items'].append({'label': label, **info})
    def media(path, label, kind):
        item = {'label': label, 'path': str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
                'sha256': sha256(path), 'kind': kind}
        if kind == 'video': item.update(info_for(path))
        manifest['media'].append(item)
        return item
    for i, rel in enumerate(inputs.get('image', []), 1):
        path = (root / case['path_base'] / rel).resolve()
        label = f'Reference Image {i}'
        media(path, label, 'image')
        with Image.open(path) as im:
            part, info = image_part(im, max_side)
        add(label, part, info)
    ref_frames = []
    for i, rel in enumerate(inputs.get('video', []), 1):
        path = (root / case['path_base'] / rel).resolve()
        label = f'Reference Video {i}'
        info = media(path, label, 'video')
        if mode == 'rough' and not anchors:
            frames = fixed_reference_frames(anchors_dir, case['case_id'], i, info)
        else:
            if mode == 'aligned':
                indices = choose(path, info, 10)
            elif mode == 'rough':
                try:
                    indices = anchors[case['case_id']][str(i)]
                except KeyError:
                    raise ValueError(f'Missing custom anchors for {case["case_id"]}, reference {i}') from None
            else:
                indices = choose(path, info, ordinary_count(info))
            frames = reference_frames(path, indices, max_side, timelines.get(path))
        ref_frames.append((label, frames))
    out_info = media(output.resolve(), 'Generated Video', 'video')
    count = 10 if mode == 'aligned' else 12 if mode == 'rough' else ordinary_count(out_info)
    output = output.resolve()
    generated = decode(output, choose(output, out_info, count))
    def present(label, frame, suffix=''):
        part, info = frame
        add(f'{label}; frame {info["frame_index"]}; t={info["timestamp_seconds"]:.4f}s; '
            f'normalized={info["normalized_position"]:.5f}{suffix}', part, info)
    if mode == 'aligned':
        # Short videos cannot make ten distinct pairs: keep explicit evidence and refuse silent mismatching.
        if len(generated) != 10 or not ref_frames or any(len(fs) != 10 for _, fs in ref_frames):
            raise ValueError('Reference/output too short for aligned ten-pair evidence')
        for j, out_frame in enumerate(generated):
            for label, frames in ref_frames: present(label, frames[j], f'; pair {j+1}')
            present('Generated Video', out_frame, f'; pair {j+1}')
    else:
        for label, frames in ref_frames:
            for frame in frames: present(label, frame, '; preceding shot' if mode == 'continuation' else '; ordered anchor' if mode == 'rough' else '')
        for frame in generated: present('Generated Video', frame, '; continuation' if mode == 'continuation' else '')
    manifest['time_context'] = {'generated_duration_seconds': out_info['duration'],
        'reference_duration_seconds': {x['label']: x['duration'] for x in manifest['media'] if x['kind'] == 'video' and x['label'] != 'Generated Video'},
        'absolute_timing_comparable': mode == 'aligned',
        'note': 'For aligned clips, compare elapsed timestamps to assess pace; normalized pair indices align phases and do not assert equal duration. Rough storyboard anchor holds do not prescribe absolute pacing.'}
    manifest['reference_roles'] = roles
    manifest['generated_frame_count'] = len(generated)
    manifest['reference_frame_counts'] = {k: len(v) for k, v in ref_frames}
    return parts, manifest
