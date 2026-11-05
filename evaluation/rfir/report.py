"""Aggregate question answers into RF/IR video, family and model scores."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean

from core import FAMILIES, aggregate_dimension, digest, load_catalog, sha256


def make_report(records: list[dict], catalog: list[dict], models: list[str], floor: int = 0) -> dict:
    by_case = {c['case_id']: c for c in catalog}
    paired = defaultdict(dict)
    for r in records:
        k = r['model'], r['case_id']
        if r['dimension'] not in ('RF', 'IR'): raise ValueError('Unknown dimension')
        if r['dimension'] in paired[k]: raise ValueError(f'Duplicate result: {k}')
        if r['model'] not in models or r['case_id'] not in by_case: raise ValueError('Unexpected result')
        paired[k][r['dimension']] = r
    samples = []
    for (model, case_id), dimensions in sorted(paired.items()):
        case = by_case[case_id]
        row = {'model': model, 'case_id': case_id, 'family': case['family'], 'task': case['task'],
               'output_key': case['output_suffix'].format(model=model)}
        hashes = {r['output_sha256'] for r in dimensions.values() if r.get('output_sha256')}
        if len(hashes) > 1: raise ValueError('RF and IR refer to different video bytes')
        for dim in ('RF', 'IR'):
            r = dimensions.get(dim, {'status': 'not_run'})
            if r['status'] == 'ok':
                qs = [q for q in case['questions'] if q['dimension'] == dim]
                if len(r['answers']) != len(qs) or any(any(a.get(k) != q[k] for k in q) for a,q in zip(r['answers'], qs)):
                    raise ValueError('Cached answers do not match canonical questions')
                row[dim] = aggregate_dimension(r['answers'], floor)
                row[dim]['status'] = 'scored'
            else: row[dim] = {'score': None, 'status': r['status']}
        samples.append(row)
    family_sizes = Counter(c['family'] for c in catalog)
    family_rows, model_rows = [], []
    for model in models:
        for family in FAMILIES:
            rows = [r for r in samples if r['model'] == model and r['family'] == family]
            item = {'model': model, 'family': family, 'expected_cases': family_sizes[family], 'attempted': len(rows)}
            for dim in ('RF', 'IR'):
                values = [r[dim]['score'] for r in rows if r[dim]['score'] is not None]
                item[dim] = mean(values) if values else None
                item[dim + '_scored'] = len(values)
            item['complete'] = all(item[d + '_scored'] == item['expected_cases'] for d in ('RF', 'IR'))
            family_rows.append(item)
        groups = [r for r in family_rows if r['model'] == model]
        full = all(r['complete'] for r in groups)
        model_rows.append({'model': model, 'complete': full,
            'RF_family_macro_observed': mean(r['RF'] for r in groups) if all(r['RF'] is not None for r in groups) else None,
            'IR_family_macro_observed': mean(r['IR'] for r in groups) if all(r['IR'] is not None for r in groups) else None})
    return {'normalization_floor': floor, 'samples': samples, 'families': family_rows, 'models': model_rows,
            'coverage': {'expected_cases_per_model': len(catalog), 'attempted_outputs': len(paired),
                         'status_counts': dict(Counter(r['status'] for r in records)),
                         'scored_dimensions': {d: sum(r[d]['score'] is not None for r in samples) for d in ('RF', 'IR')}},
            'note': 'Family means use all available valid videos for each model. The seven families have equal weight. Merge VQ with evaluation/aggregate.py.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_dir', type=Path)
    args = parser.parse_args()
    run = json.loads((args.run_dir / 'run.json').read_text())
    catalog, sources = load_catalog(Path(run['dataset']))
    if sources != run['source_files']: parser.error('Annotation source changed; cannot relabel old scores')
    records = []
    for path in sorted((args.run_dir / 'jobs').glob('*/*/*/*.json')):
        row = json.loads(path.read_text())
        if digest(row['request']) != row['fingerprint']: parser.error(f'Corrupt request fingerprint: {path}')
        if row['request']['config'] != run['config']: parser.error(f'Mixed judging settings: {path}')
        output = Path(run['dataset']) / 'model_outputs' / row['output_key']
        if not output.is_file() or sha256(output) != row['output_sha256']:
            parser.error(f'Generated video changed: {path}')
        for media in row['request']['evidence']['media']:
            source = Path(run['dataset']) / media['path']
            if not source.is_file() or sha256(source) != media['sha256']:
                parser.error(f'Reference/output media changed: {media["path"]}')
        if row['model'] not in run['models'] or row['case_id'] not in run['selected_cases']:
            parser.error(f'Unexpected job selection: {path}')
        records.append(row)
    failures = args.run_dir / 'failures.json'
    if failures.exists(): records.extend(json.loads(failures.read_text())['records'])
    existing = {(r['model'], r['case_id'], r['dimension']) for r in records}
    for item in json.loads((args.run_dir / 'plan.json').read_text())['items']:
        for dim in ('RF', 'IR'):
            if (item['model'], item['case_id'], dim) not in existing:
                records.append({**item, 'dimension': dim, 'status': 'not_run' if item['output_exists'] else 'missing_output'})
    floor = run['score_floor']
    result = make_report(records, catalog, run['models'], floor)
    result['run_fingerprint'] = run['fingerprint']
    from run import atomic_json
    path = args.run_dir / 'scores.json'
    atomic_json(path, result)
    print(json.dumps({'report': str(path), 'coverage': result['coverage'], 'models': result['models']}, ensure_ascii=False, indent=2))


if __name__ == '__main__': main()
