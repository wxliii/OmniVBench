# RF/IR checklists

`questions/<family>/<task>.json` maps each case ID to its applicable criteria
and English questions. Criterion definitions are in `../criteria.csv`.
The 18 files mirror the dataset's `task_json/` directories and filenames.
Match task samples and checklist entries by `case_id`; one file may contain
more than one task ID.
RF visibility and evidence rules are in [`../rfir/rubric_RF.txt`](../rfir/rubric_RF.txt).

Instructions and reference assignments are in the
[HF dataset's task_json directory](https://huggingface.co/datasets/wxli318/OmniVBench/tree/main/task_json),
read from the dataset directory passed to `--dataset`.
English instructions and assigned reference factors govern scoring.

See the [evaluation guide](../README.md) for score calculation and commands.
