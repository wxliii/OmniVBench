"""Combine per-video RF, IR and VQ scores with equal task-family weights."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from statistics import mean

from rfir.core import FAMILIES


def average(values):
    values = [v for v in values if v is not None]
    return mean(values) if values else None


def macro(groups, column):
    values = [g[column] for g in groups]
    return mean(values) if len(values) == len(FAMILIES) and all(v is not None for v in values) else None


def read_vq(path):
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        return {r['path']: r for r in csv.DictReader(stream)}


def combine(rfir, vq):
    family_sizes = {g['family']: g['expected_cases'] for g in rfir['families']}
    models = [m['model'] for m in rfir['models']]
    samples = []
    for row in rfir['samples']:
        key = row['output_key']
        item = {'model': row['model'], 'case_id': row['case_id'],
                'family': row['family'], 'task': row['task'], 'path': key,
                'RF': row['RF'].get('score'), 'IR': row['IR'].get('score'), 'VQ': None}
        if key in vq:
            value = vq[key]
            expected = {'family': row['family'], 'task': row['task'],
                        'model': row['model'], 'case': Path(key).stem}
            if any(value[k] != v for k, v in expected.items()):
                raise ValueError(f'VQ metadata does not match video: {key}')
            item['VQ'] = float(value['vq_100'])
        item['Overall'] = mean(item[d] for d in ('RF', 'IR', 'VQ')) if all(item[d] is not None for d in ('RF', 'IR', 'VQ')) else None
        samples.append(item)

    families, model_scores = [], []
    for model in models:
        groups = []
        for family in FAMILIES:
            rows = [s for s in samples if s['model'] == model and s['family'] == family]
            group = {'model': model, 'family': family, 'expected_cases': family_sizes[family]}
            for dim in ('RF', 'IR', 'VQ'):
                group[dim] = average(s[dim] for s in rows)
                group[dim + '_scored'] = sum(s[dim] is not None for s in rows)
            group['Overall'] = mean(group[d] for d in ('RF', 'IR', 'VQ')) if all(group[d] is not None for d in ('RF', 'IR', 'VQ')) else None
            group['joint_scored'] = sum(s['Overall'] is not None for s in rows)
            groups.append(group)
        families.extend(groups)
        item = {'model': model}
        for dim in ('RF', 'IR', 'VQ', 'Overall'):
            item[dim] = macro(groups, dim)
        for dim in ('RF', 'IR', 'VQ'):
            item[dim + '_scored'] = sum(g[dim + '_scored'] for g in groups)
        item['joint_scored'] = sum(g['joint_scored'] for g in groups)
        model_scores.append(item)
    return {'samples': samples, 'families': families, 'models': model_scores,
            'aggregation': 'Per-family means use all valid videos for each dimension. RF, IR and VQ have equal weight within each family; the seven families have equal weight.'}


def write_csv(path, rows, fields):
    with path.open('w', newline='', encoding='utf-8-sig') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rfir', required=True, type=Path, help='RF/IR scores.json')
    parser.add_argument('--vq', required=True, type=Path, help='VQ aggregate/per_sample.csv')
    parser.add_argument('--out-dir', required=True, type=Path)
    args = parser.parse_args()
    result = combine(json.loads(args.rfir.read_text()), read_vq(args.vq))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / 'scores.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    write_csv(args.out_dir / 'per_sample.csv', result['samples'],
              ['model', 'case_id', 'family', 'task', 'path', 'RF', 'IR', 'VQ', 'Overall'])
    write_csv(args.out_dir / 'by_family.csv', result['families'],
              ['model', 'family', 'expected_cases', 'RF', 'RF_scored', 'IR', 'IR_scored',
               'VQ', 'VQ_scored', 'Overall', 'joint_scored'])
    write_csv(args.out_dir / 'by_model.csv', result['models'],
              ['model', 'RF', 'IR', 'VQ', 'Overall', 'RF_scored', 'IR_scored', 'VQ_scored', 'joint_scored'])
    print(json.dumps({'out_dir': str(args.out_dir), 'models': result['models']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
