"""Canonical case loading, strict ordinal answers and paper §3.3 aggregation."""
from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
ANNOTATIONS = ROOT.parents[1]
FAMILIES = ('content', 'motion', 'style', 'structure', 'narrative', 'multi_content', 'cross_aspect')


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':')).encode()).hexdigest()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_catalog(dataset: Path, root: Path = ANNOTATIONS) -> tuple[list[dict], dict]:
    root = Path(root)
    dataset = Path(dataset)
    task_dir = dataset / 'task_json'
    with (root / 'evaluation/criteria.csv').open() as f:
        criteria = {r['criterion_id']: r for r in csv.DictReader(f)}
    questions, sources = {}, {}
    for p in sorted((root / 'evaluation/checklists/questions').glob('*/*.json')):
        data = json.loads(p.read_text())
        if questions.keys() & data.keys():
            raise ValueError(f'Duplicate checklist case: {p}')
        questions.update(data)
        sources[str(p.relative_to(root))] = sha256(p)
    cases = []
    task_files = sorted(task_dir.glob('*/*.json'))
    for p in task_files:
        data = json.loads(p.read_text())
        sources[str(p.relative_to(dataset))] = sha256(p)
        task_ids = {s['task_id'] for s in data['samples']}
        if data['sample_count'] != len(data['samples']):
            raise ValueError(f'Incorrect sample_count: {p}')
        for sample in data['samples']:
            case = dict(sample, family=p.parent.name, task=p.stem,
                        task_json=str(p.relative_to(dataset)), path_base=data['path_base'])
            case['questions'] = []
            for cid, items in questions.pop(case['case_id']).items():
                c = criteria[cid]
                dim = c['L1']
                if int(c['scale']) != {'RF': 5, 'IR': 3}[dim]:
                    raise ValueError(f'Incorrect scale: {cid}')
                for i, q in enumerate(items, 1):
                    if not isinstance(q.get('en'), str) or not q['en'].strip():
                        raise ValueError(f'Empty question: {case["case_id"]} {cid}:{i}')
                    case['questions'].append({'question_id': f'{cid}:{i}', 'criterion': cid,
                        'l2': c['L2_code'], 'dimension': dim, 'scale': int(c['scale']),
                        'criterion_name': c['criterion_name'], 'question': q['en']})
            filename = (sample['sample_id'] if len(task_ids) == 1 else
                        f'{sample["task_id"]}_{sample["sample_id"]}') + '.mp4'
            case['output_suffix'] = f'{p.parent.name}/{p.stem}/{{model}}/{filename}'
            if not all(any(q['dimension'] == d for q in case['questions']) for d in ('RF', 'IR')):
                raise ValueError(f'Missing dimension: {case["case_id"]}')
            cases.append(case)
    if questions or len({c['case_id'] for c in cases}) != len(cases):
        raise ValueError('Unmatched or duplicate cases')
    sources['evaluation/criteria.csv'] = sha256(root / 'evaluation/criteria.csv')
    return cases, sources


def reference_roles(case: dict) -> dict[str, list[dict]]:
    inputs = case['inputs']
    result = {f'Reference {kind.title()} {i}': []
              for kind in ('image', 'video') for i in range(1, len(inputs.get(kind, [])) + 1)}
    for role in inputs.get('reference_mapping', []):
        ref_type = str(role.get('ref_type', role.get('type', ''))).lower()
        idx = role['ref_index']
        kind = ('video' if 'video' in ref_type or idx == 'video' else 'image')
        index = 1 if idx == 'video' else idx
        if type(index) is not int or f'Reference {kind.title()} {index}' not in result:
            raise ValueError(f'Invalid reference mapping: {case["case_id"]}: {role}')
        result[f'Reference {kind.title()} {index}'].append(role)
    return result


def parse_answers(raw: str, expected: list[dict]) -> list[dict]:
    """Require a complete response. Never salvage a prefix or turn failure into zero."""
    s = raw.strip()
    if s.startswith('```') and s.endswith('```'):
        s = s.split('\n', 1)[1].rsplit('```', 1)[0].strip()
    def unique_pairs(pairs):
        d = {}
        for k, v in pairs:
            if k in d:
                raise ValueError(f'Duplicate JSON key: {k}')
            d[k] = v
        return d
    data = json.loads(s, object_pairs_hook=unique_pairs)
    if not isinstance(data, dict) or set(data) != {'answers'} or not isinstance(data['answers'], list):
        raise ValueError('Expected exactly {"answers": [...]}')
    table = {q['question_id']: q for q in expected}
    answers = {}
    for a in data['answers']:
        if not isinstance(a, dict) or set(a) != {'question_id', 'score', 'evidence', 'uncertainty'}:
            raise ValueError('Incorrect answer schema')
        qid = a['question_id']
        if not isinstance(qid, str) or qid not in table or qid in answers:
            raise ValueError(f'Unexpected or duplicate question: {qid}')
        score = a['score']
        if type(score) is not int or not 1 <= score <= table[qid]['scale']:
            raise ValueError(f'Out-of-range/non-integer score: {qid}')
        if not isinstance(a['evidence'], str) or not a['evidence'].strip():
            raise ValueError(f'Missing visual evidence: {qid}')
        if not isinstance(a['uncertainty'], str):
            raise ValueError(f'Incorrect uncertainty: {qid}')
        answers[qid] = a
    if set(answers) != set(table):
        raise ValueError(f'Missing answers: {sorted(set(table) - set(answers))}')
    return [{**q, **answers[q['question_id']]} for q in expected]


def aggregate_dimension(answers: list[dict], floor: int = 0) -> dict:
    if floor not in (0, 1) or not answers or len({a['dimension'] for a in answers}) != 1:
        raise ValueError('Invalid normalization or dimension')
    criteria = defaultdict(list)
    for a in answers:
        if type(a['score']) is not int or not 1 <= a['score'] <= a['scale']:
            raise ValueError('Invalid score')
        criteria[(a['l2'], a['criterion'], a['scale'])].append(a['score'])
    c_scores, l2 = {}, defaultdict(list)
    for (group, criterion, scale), scores in criteria.items():
        value = floor + (mean(scores) - 1) / (scale - 1) * (100 - floor)
        c_scores[criterion] = {'raw_mean': mean(scores), 'normalized': value, 'n': len(scores)}
        l2[group].append(value)
    l2_scores = {k: mean(v) for k, v in l2.items()}
    return {'score': mean(l2_scores.values()), 'criteria': c_scores, 'l2': l2_scores,
            'questions': len(answers), 'uncertain_questions': sum(bool(a['uncertainty']) for a in answers)}
