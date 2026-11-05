# OmniVBench evaluation

RF and IR share a multimodal judging pipeline in `rfir/`. VQ is calculated
independently in `vq/`. `aggregate.py` combines their per-video results.

## Annotations and media

The repository includes 12,172 checklist questions covering 813 cases:

```text
OmniVBench/                        # this repository
└── evaluation/
    ├── criteria.csv
    └── checklists/
        └── questions/<family>/<task>.json
```

Checklists are keyed by case ID and criterion, with English questions in `en`.
The scorer reads checklists and scoring definitions from this repository.
Task instructions and reference assignments are read directly from the HF
dataset's `task_json/`. English instructions and explicitly assigned reference
factors govern scoring.

RF visibility and evidence rules are included in [`rfir/rubric_RF.txt`](rfir/rubric_RF.txt).

Get task JSONs, reference media, the companion storyboard-frame bundle, and VQ weights
from [Hugging Face](https://huggingface.co/datasets/wxli318/OmniVBench).
Keep large assets in a separate data directory:

```text
/path/to/OmniVBench_media/
├── task_json/<family>/<task>.json # instructions and reference assignments
├── task_assets/                   # original reference images and videos
└── model_outputs/<family>/<task>/<model>/<case>.mp4

/path/to/storyboard_anchors/
├── manifest.json
└── ...                           # fixed reference JPEGs
```

`--dataset` points to the downloaded dataset directory containing `task_json/`,
`task_assets/`, and `model_outputs/`. Checklists remain in this code repository.
Tasks with several task IDs use `<task_id>_<sample_id>.mp4`; others use
`<sample_id>.mp4`.

## Environment and weights

RF/IR uses Python, NumPy, Pillow, OpenCV and FFmpeg/FFprobe. For VQ, follow
[DOVER](https://github.com/QualityAssessment/DOVER),
[Aesthetic Predictor V2.5](https://github.com/discus0434/aesthetic-predictor-v2-5),
and the official [UnifiedReward deployment](https://huggingface.co/CodeGoat24/UnifiedReward-2.0-qwen35-9b).

Download [VQ weights](https://huggingface.co/datasets/wxli318/OmniVBench/tree/main/evaluation/VQ/weights)
and place them under `evaluation/vq/`:

```text
evaluation/vq/weights/
├── DOVER_plus_plus.pth
├── aesthetic_predictor_v2_5.pth
├── siglip-so400m-patch14-384/
└── UnifiedReward-2.0-qwen35-9b/
```

Download every file inside each model folder. Prepare upstream inference code
from the repository root:

```bash
git clone https://github.com/QualityAssessment/DOVER.git evaluation/vq/upstream/DOVER
git clone https://github.com/discus0434/aesthetic-predictor-v2-5.git evaluation/vq/upstream/aesthetic-predictor-v2-5
```

## 1. RF and IR

Connect your own multimodal judge provider and choose its model. The supplied
client uses an OpenAI-compatible Chat Completions API with image inputs and
SSE streaming; adapt `rfir/client.py` for other API formats. Fill in the empty
values below and run from the repository root:

```bash
export API_KEY=""
export API_BASE_URL=""
export JUDGE_MODEL=""
python evaluation/rfir/run.py \
  --dataset /path/to/OmniVBench_media --models MyModel \
  --anchors-dir /path/to/storyboard_anchors \
  --workers 48 --out results/rfir --execute
```

`API_BASE_URL` is the base URL before `/chat/completions`. You can also set the
URL and model with `--base-url` and `--judge`. Optional provider-specific
request fields can be passed with `--extra-json`; its default is `{}`.

Each video receives separate RF and IR requests. Ordinary videos use 2 FPS
sampling with 8–20 frames; aligned tasks use 10 reference/generated frame pairs;
generated storyboard videos use 12 frames with fixed reference JPEGs. Extracted
images use a maximum side of 1024; fixed storyboard JPEGs retain their bytes.
Encoded reference-video frames are cached in memory across generated models.

`jobs/` contains question scores and evidence. `scores.json` contains RF/IR
video, family and model scores. `--models all` scores available model folders;
`--cases task_id/001` selects cases. Omit `--execute` to inspect the inventory
without API calls. Use the same output directory to resume identical requests.

## 2. VQ

```bash
python evaluation/vq/run.py technical \
  --input-root /path/to/OmniVBench_media/model_outputs \
  --output results/vq/technical.jsonl
python evaluation/vq/run.py aesthetic \
  --input-root /path/to/OmniVBench_media/model_outputs \
  --output results/vq/aesthetic.jsonl
python evaluation/vq/physics.py \
  --input-root /path/to/OmniVBench_media/model_outputs \
  --api-url http://localhost:8080 --output results/vq/physics.jsonl

python evaluation/vq/aggregate.py \
  --technical results/vq/technical.jsonl \
  --aesthetic results/vq/aesthetic.jsonl \
  --physics results/vq/physics.jsonl --out-dir results/vq/aggregate
```

Technical scoring uses the official DOVER++ view: three 32-frame clips with
frame interval 2. Aesthetic scoring averages 8 uniformly sampled RGB frames.
Physics uses the official 16-frame JPEG and empty-caption pipeline and reads
only the Physics Score from the upstream-deployed service.

VQ aggregation produces `per_sample.csv` and `by_model.csv`. Each model's
standalone VQ mean uses all its valid videos, with equal video weights.

## 3. Combined scores

```bash
python evaluation/aggregate.py \
  --rfir results/rfir/scores.json \
  --vq results/vq/aggregate/per_sample.csv --out-dir results/combined
```

Videos are matched by `family/task/model/case.mp4`. Outputs are `scores.json`,
`per_sample.csv`, `by_family.csv`, and `by_model.csv`.

## Score calculation

For RF/IR, average questions within each criterion, active criteria within each
L2 group, and active L2 groups within each video. For the combined report,
average each dimension's valid videos within each family, average RF, IR and
VQ equally within that family, then average the seven families equally.
The combined report's VQ column therefore uses family weights; the standalone
VQ `by_model.csv` uses equal video weights. Missing scores remain missing.

Code is MIT licensed. Annotations and reference resources retain the
[benchmark terms](../TERMS_OF_USE.md).
