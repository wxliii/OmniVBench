<div align="center">

# OmniVBench

### A Benchmark and Large-Scale Dataset for Omni Reference-to-Video Generation

<p>
  <a href="https://wxliii.github.io/OmniVBench/"><img src="https://img.shields.io/badge/Project_Page-4B4395?style=for-the-badge&amp;logo=googlechrome&amp;logoColor=white" alt="Project page"></a>
  <a href="https://wxliii.github.io/OmniVBench/benchmark.html"><img src="https://img.shields.io/badge/Benchmark-DE7933?style=for-the-badge&amp;logo=chartdotjs&amp;logoColor=white" alt="Benchmark"></a>
  <a href="https://huggingface.co/datasets/wxli318/Omni-R2V"><img src="https://img.shields.io/badge/Dataset-Omni--R2V-FFD21E?style=for-the-badge&amp;logo=huggingface&amp;logoColor=black" alt="Omni-R2V dataset"></a>
</p>

</div>

<p align="center">
  <img src="https://raw.githubusercontent.com/wxliii/OmniVBench/gh-pages/img/show_case.webp" width="100%" alt="Representative examples from the Omni-R2V Dataset">
</p>

## Overview

Reference-to-video generation is moving from single-reference conditioning toward heterogeneous and compositional references. **OmniVBench** and the **Omni-R2V Dataset** provide a shared foundation for evaluating and training models in this broader setting.

- **Comprehensive R2V task coverage.** Seven task families span content, motion, style, structure, narrative, multi-content, and cross-aspect references.
- **Factor-grounded evaluation.** OmniVBench contains **813 evaluation cases**, **18 fine-grained tasks**, and **12,172 case-specific checklist items** for assessing reference preservation, factor disentanglement, target binding, and instruction realization.
- **Large-scale training data.** Omni-R2V provides **340K processed samples**, built primarily from professional video footage through reusable, task-specific construction pipelines.

## OmniVBench

OmniVBench evaluates R2V models from single-reference factor transfer to multi-reference composition. Its taxonomy separates the visual factor supplied by each reference and the control objective required by the instruction.

<p align="center">
  <img src="https://raw.githubusercontent.com/wxliii/OmniVBench/gh-pages/img/omnivbench.webp" width="600" alt="OmniVBench task taxonomy">
</p>

Explore the complete task definitions, model comparison, and qualitative examples on the [benchmark page](https://wxliii.github.io/OmniVBench/benchmark.html).

## Omni-R2V Dataset

Omni-R2V is a large-scale public R2V training dataset covering heterogeneous image and video references as well as multi-reference compositions. It contains live-action, 2D animation, and 3D animation videos across all seven task families. Each processed sample pairs reference input(s) with a training instruction and target video.

<p align="center">
  <img src="https://raw.githubusercontent.com/wxliii/OmniVBench/gh-pages/img/statistic.webp" width="820" alt="Omni-R2V Dataset statistics">
</p>

<div align="center">
  <a href="https://huggingface.co/datasets/wxli318/Omni-R2V"><strong>Download on Hugging Face</strong></a>
  &nbsp;·&nbsp;
  <a href="https://wxliii.github.io/OmniVBench/#single-reference"><strong>Browse dataset examples</strong></a>
</div>

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
