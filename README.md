# OmniVBench

**OmniVBench: A Benchmark and Large-Scale Dataset for Omni Reference-to-Video Generation**

[Project Website](https://wxliii.github.io/OmniVBench/) · [Benchmark Examples](https://wxliii.github.io/OmniVBench/benchmark.html#benchmark-examples) · [Omni-R2V Dataset](https://huggingface.co/datasets/wxli318/Omni-R2V)

Omni reference-to-video (R2V) generation requires models to interpret heterogeneous references, extract the intended visual factors, and compose them according to an instruction. **OmniVBench** evaluates these capabilities, while the **Omni-R2V Dataset** provides large-scale training data for the same diverse reference settings.

## Highlights

- **Comprehensive R2V task coverage.** 813 evaluation cases span 7 task families and 18 fine-grained tasks, covering heterogeneous references and multi-reference compositions.
- **Factor-grounded evaluation.** 12,172 case-specific checklist items assess whether intended reference factors are preserved, correctly disentangled, bound to their targets, and realized according to the instruction.
- **Fine-grained capability analysis.** Evaluation of 11 open- and closed-source models reveals task-specific strengths and limitations, including a discrepancy between reference fidelity and instruction realization.

## Task Coverage

<p align="center">
  <img src="https://raw.githubusercontent.com/wxliii/OmniVBench/gh-pages/img/omnivbench.webp" alt="OmniVBench task taxonomy" width="520">
</p>

| Task family | Evaluation focus |
| --- | --- |
| Content | Object, character, and scene preservation, including selective attribute transfer. |
| Motion | Transfer of subject actions or camera trajectories while changing appearance and context. |
| Style | Transfer of visual style while following the requested target content. |
| Structure | Spatial composition, poses, layout, and timing guided by greybox, line art, or rough storyboards. |
| Narrative | Storyboard realization, story transformation, and preceding-shot continuation. |
| Multi-content | Composition of multiple entities and grounded assignment of reference factors. |
| Cross-aspect | Joint control using content with motion, style, structure, or narrative references. |

## Evaluation Protocol

OmniVBench evaluates generated videos along three dimensions:

- **Reference Fidelity (RF):** whether the designated reference information is faithfully preserved or transferred. Changes explicitly requested by the instruction are not treated as fidelity errors.
- **Instruction Realization (IR):** whether reference factors are correctly disentangled and assigned to their intended targets, and whether the requested operations are realized.
- **Video Quality (VQ):** technical quality, aesthetic quality, and physical plausibility, evaluated separately from reference fidelity and instruction compliance.

RF and IR use manually verified, case-specific checklists. The checklist is fixed across all model outputs for the same case. RF questions use a 1–5 scale and IR questions a 1–3 scale; scores are normalized to a 100-point scale and aggregated hierarchically. Task-family scores average RF, IR, and VQ.

## Benchmark Results

No model leads across all seven task families. Seedance 2.5 obtains the highest overall score, closely followed by MiniMax H3. The task-level results expose capability differences that a single overall score can hide.

| Model | Group | Content | Motion | Style | Structure | Narrative | Multi-content | Cross-aspect | Overall |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Seedance 2.5 | Closed | 78.88 | 66.10 | 67.13 | 73.35 | 73.97 | 77.77 | 71.53 | 72.68 |
| MiniMax H3 | Open | 78.86 | 65.32 | 66.24 | 72.94 | 73.90 | 77.22 | 72.36 | 72.41 |
| Seedance 2.0 | Closed | 79.00 | 63.05 | 63.73 | 68.36 | 73.76 | 76.63 | 71.83 | 70.91 |
| Happy Horse 1.0 | Closed | 75.90 | 68.58 | 65.62 | 69.46 | 72.34 | 74.62 | 69.71 | 70.89 |
| Gemini Omni | Closed | 75.02 | 62.25 | 69.24 | 70.13 | 75.11 | 73.36 | 70.18 | 70.76 |
| Kling 3.0 Omni | Closed | 75.99 | 64.20 | 55.90 | 71.12 | 68.59 | 75.98 | 68.33 | 68.59 |
| Vidu-Q2-Pro | Closed | 71.87 | 47.65 | 59.87 | 51.81 | 50.68 | 72.07 | 62.21 | 59.45 |
| Bernini | Open | 69.27 | 55.92 | 50.62 | 69.44 | 42.02 | 60.32 | 51.03 | 56.95 |
| LoomVideo | Open | 61.24 | 52.09 | 42.03 | 62.53 | 46.98 | 49.02 | 44.86 | 51.25 |
| UniVideo | Open | 66.01 | 44.52 | 47.40 | 48.84 | 36.97 | 58.00 | 46.09 | 49.69 |
| OmniWeaving | Open | 62.23 | 50.58 | 41.40 | 63.19 | 38.03 | 47.49 | 39.25 | 48.88 |

Explore the [reference inputs, instructions, and model outputs](https://wxliii.github.io/OmniVBench/benchmark.html#benchmark-examples) on the project website.

## Omni-R2V Dataset

The Omni-R2V Dataset comprises approximately **340K processed training samples** across the seven task families. Built primarily from professional video footage, it spans live-action, 2D animation, and 3D animation. Task-specific pipelines construct reference–target pairs and corresponding training instructions, providing a reusable recipe for omni-R2V data construction.

[Download the dataset](https://huggingface.co/datasets/wxli318/Omni-R2V) · [Browse training examples](https://wxliii.github.io/OmniVBench/#single-reference)

## Code Release

Evaluation code and instructions for running the benchmark will be added here.

## Citation

```bibtex
@article{omnivbench2026,
  title   = {OmniVBench: A Benchmark and Large-Scale Dataset for Omni Reference-to-Video Generation},
  author  = {Li, Wenxue and Guan, Peiyan and Jiang, Haoyang and Cai, Junxian and
             Liu, Hualuo and Zhang, Chunjie and Guan, Chong and Huang, Kai and
             Li, Songlian and Wu, Taiyi and Yu, Yongjian and Zhao, Xiaotong and
             Zhao, Alan and Liu, Eric and Chen, Xi and Liu, Yu and Zhu, Lei},
  journal = {arXiv preprint},
  year    = {2026}
}
```
