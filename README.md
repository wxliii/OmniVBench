# OmniVBench

**A Benchmark and Large-Scale Dataset for Omni Reference-to-Video Generation**

[Project Website](https://wxliii.github.io/OmniVBench/) · [Benchmark Results](https://wxliii.github.io/OmniVBench/benchmark.html) · [Omni-R2V Dataset](https://huggingface.co/datasets/wxli318/Omni-R2V)

OmniVBench and the Omni-R2V Dataset provide a shared foundation for evaluating and training reference-to-video generation models with heterogeneous and compositional references.

## OmniVBench

- **Comprehensive R2V task coverage:** 813 evaluation cases across 7 task families and 18 fine-grained tasks, spanning content, motion, style, structure, narrative, multi-content, and cross-aspect references.
- **Factor-grounded evaluation:** 12,172 case-specific checklist items assess reference-factor preservation, disentanglement, and target binding, alongside instruction realization and video quality.
- **Fine-grained capability analysis:** Evaluation of 11 representative open- and closed-source models reveals task-specific strengths and limitations.

## Omni-R2V Dataset

- **Comprehensive coverage of R2V tasks:** A large-scale public training dataset covering heterogeneous reference types and multi-reference compositions across seven task families.
- **Industry-grade training data:** Approximately 340K processed samples built primarily from professional video footage, spanning live-action, 2D animation, and 3D animation.
- **Reusable R2V construction pipelines:** Task-specific construction of reference–target pairs and corresponding training instructions.

Explore the [dataset examples](https://wxliii.github.io/OmniVBench/#single-reference) or access the [dataset on Hugging Face](https://huggingface.co/datasets/wxli318/Omni-R2V).

## Evaluation Code

The `main` branch is reserved for the project documentation and evaluation code. Evaluation code and usage instructions will be added here.

## Website Source

Website code and demonstration assets are maintained on the [`gh-pages` branch](https://github.com/wxliii/OmniVBench/tree/gh-pages). GitHub Pages publishes that branch at https://wxliii.github.io/OmniVBench/.

To work on the website separately:

```bash
git clone --branch gh-pages --single-branch https://github.com/wxliii/OmniVBench.git OmniVBench-website
cd OmniVBench-website
python3 -m http.server 8000
```

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
