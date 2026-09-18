# OmniVBench

**A Benchmark and Large-Scale Dataset for Omni Reference-to-Video Generation**

[Project Website](https://wxliii.github.io/OmniVBench/) · [Benchmark](https://wxliii.github.io/OmniVBench/benchmark.html) · [Dataset on Hugging Face](https://huggingface.co/datasets/wxli318/Omni-R2V)

OmniVBench and the Omni-R2V Dataset provide a shared foundation for evaluating and training reference-to-video generation models with heterogeneous and compositional references.

## OmniVBench

A comprehensive R2V benchmark with **813 evaluation cases** spanning **7 task families and 18 fine-grained tasks**. Its factor-grounded evaluation uses **12,172 case-specific checklist items** to assess reference preservation, factor disentanglement, target binding, and instruction realization.

See the [project website](https://wxliii.github.io/OmniVBench/benchmark.html) for task definitions, evaluation results, and model examples. Evaluation code will be added to this repository.

## Omni-R2V Dataset

A large-scale public R2V training dataset with **340K processed samples** covering heterogeneous reference types and multi-reference compositions. Built primarily from professional video footage, it spans live-action, 2D animation, and 3D animation. Task-specific pipelines construct reference–target pairs and training instructions, providing a reusable approach to omni-R2V data construction.

[Download the dataset](https://huggingface.co/datasets/wxli318/Omni-R2V) · [Browse examples](https://wxliii.github.io/OmniVBench/#single-reference)

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
