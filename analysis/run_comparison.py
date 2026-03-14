import argparse
import csv
import sys
import time
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Tuple
import numpy as np

# Add project root to path so raga/makam packages can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

from raga.pitch_extractor import load_raga_notes
from makam.parser import load_makam_notes
from melodyshape import (
    build_spans,
    compute_span_frequencies,
    shapeh_similarity,
    time_similarity,
)


def _aggregate_metrics(rows: List[Dict], group_cols: List[str], metric_cols: List[str], top_k: int) -> List[Dict]:
    groups: Dict[Tuple, List[Dict]] = {}
    for r in rows:
        key = tuple(r[c] for c in group_cols)
        groups.setdefault(key, []).append(r)

    out = []
    for key, group in groups.items():
        base = {col: val for col, val in zip(group_cols, key)}
        for metric in metric_cols:
            vals = [r.get(metric) for r in group if r.get(metric) is not None]
            if not vals:
                continue
            vals_sorted = sorted(vals)
            out.append({**base, 'metric': metric, 'agg': 'mean', 'value': float(mean(vals_sorted))})
            out.append({**base, 'metric': metric, 'agg': 'median', 'value': float(median(vals_sorted))})
            out.append({**base, 'metric': metric, 'agg': 'max', 'value': float(vals_sorted[-1])})
            top = vals_sorted[-min(top_k, len(vals_sorted)):]
            out.append({**base, 'metric': metric, 'agg': f'top_{top_k}_mean', 'value': float(mean(top))})

    return out


def _best_matches(rows: List[Dict], raga_col: str, makam_col: str, usul_col: str) -> List[Dict]:
    groups: Dict[Tuple, List[Dict]] = {}
    for r in rows:
        key = (r[raga_col], r['metric'], r['agg'])
        groups.setdefault(key, []).append(r)

    out = []
    for (raga, metric, agg), group in groups.items():
        best = max(group, key=lambda x: x['value'])
        out.append({
            raga_col: raga,
            'metric': metric,
            'agg': agg,
            'best_makam': best[makam_col],
            'best_usul': best[usul_col],
            'value': best['value'],
        })
    return out


def _write_csv(path: Path, rows: List[Dict], fieldnames: List[str]) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--raga-dir', default='datasets/ragas')
    parser.add_argument('--makam-dir', default='datasets/makams')
    parser.add_argument('--samples-per-beat', type=int, default=20)
    parser.add_argument('--shape-samples', type=int, default=200)
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--out-dir', default='ai-code/output')
    parser.add_argument('--limit-ragas', type=int, default=0)
    parser.add_argument('--limit-makams', type=int, default=0)
    parser.add_argument('--makam-file', default='')
    parser.add_argument('--makam-name', default='')
    parser.add_argument('--makam-usul', default='')
    parser.add_argument('--log-every', type=float, default=10.0)
    parser.add_argument('--system', choices=['shapeh', 'time', 'shapetime'], default='shapeh')
    parser.add_argument('--shapetime-top-k', type=int, default=10)
    args = parser.parse_args()

    raga_dir = Path(args.raga_dir)
    makam_dir = Path(args.makam_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raga_files = sorted(raga_dir.glob('*.xml'))
    makam_files = sorted(makam_dir.glob('*.xml'))
    if args.limit_ragas > 0:
        raga_files = raga_files[:args.limit_ragas]
    if args.limit_makams > 0:
        makam_files = makam_files[:args.limit_makams]
    if args.makam_file:
        makam_files = [makam_dir / args.makam_file]

    # Load raga notes
    raga_items = []
    print(f"Loading ragas from {raga_dir} ({len(raga_files)} files)")
    last_log = time.time()
    for f in raga_files:
        notes, meta = load_raga_notes(str(f))
        if not notes:
            continue
        raga_items.append({
            'file': f.name,
            'raag': meta.get('raag', ''),
            'taal': meta.get('taal', ''),
            'notes': notes,
        })
        if time.time() - last_log >= args.log_every:
            print(f"  loaded {len(raga_items)} raga melodies...")
            last_log = time.time()
    print(f"Loaded {len(raga_items)} raga melodies")

    # Load makam notes
    makam_items = []
    print(f"Loading makams from {makam_dir} ({len(makam_files)} files)")
    last_log = time.time()
    for f in makam_files:
        notes, meta = load_makam_notes(str(f))
        if not notes:
            continue
        makam_items.append({
            'file': f.name,
            'makam': meta.get('makam', ''),
            'usul': meta.get('usul', ''),
            'notes': notes,
        })
        if time.time() - last_log >= args.log_every:
            print(f"  loaded {len(makam_items)} makam melodies...")
            last_log = time.time()

    if args.makam_name:
        target = args.makam_name.strip().lower()
        makam_items = [m for m in makam_items if m['makam'].strip().lower() == target]
    if args.makam_usul:
        target = args.makam_usul.strip().lower()
        makam_items = [m for m in makam_items if m['usul'].strip().lower() == target]
    print(f"Loaded {len(makam_items)} makam melodies after filtering")

    # Build spans
    for r in raga_items:
        if args.system in ('shapeh', 'shapetime'):
            r['spans_shapeh'] = build_spans(r['notes'], 3)
        if args.system in ('time', 'shapetime'):
            r['spans_time'] = build_spans(r['notes'], 4)

    for m in makam_items:
        if args.system in ('shapeh', 'shapetime'):
            m['spans_shapeh'] = build_spans(m['notes'], 3)
        if args.system in ('time', 'shapetime'):
            m['spans_time'] = build_spans(m['notes'], 4)

    # Span frequencies for ShapeH (document collection = makams)
    f = {}
    if args.system in ('shapeh', 'shapetime'):
        f = compute_span_frequencies([m.get('spans_shapeh', []) for m in makam_items])

    # Pairwise similarity
    print("Computing pairwise similarities...")
    records = []
    total_pairs = len(raga_items) * len(makam_items)
    done = 0
    last_log = time.time()

    for r in raga_items:
        for m in makam_items:
            rec = {
                'raga_file': r['file'],
                'raga': r['raag'],
                'taal': r['taal'],
                'makam_file': m['file'],
                'makam': m['makam'],
                'usul': m['usul'],
            }
            if args.system in ('shapeh', 'shapetime'):
                rec['shapeh_score'] = shapeh_similarity(r.get('spans_shapeh', []), m.get('spans_shapeh', []), f)
            if args.system in ('time', 'shapetime'):
                rec['time_score'] = time_similarity(r.get('spans_time', []), m.get('spans_time', []))
            records.append(rec)

            done += 1
            if time.time() - last_log >= args.log_every:
                pct = (done / total_pairs * 100) if total_pairs else 100.0
                print(f"  pairwise {done}/{total_pairs} ({pct:.1f}%)")
                last_log = time.time()

    print("Pairwise similarity complete")

    # ShapeTime re-ranking
    if args.system == 'shapetime':
        # Compute shapetime_rank per raga
        by_raga: Dict[str, List[Dict]] = {}
        for r in records:
            by_raga.setdefault(r['raga'], []).append(r)

        for raga, group in by_raga.items():
            group.sort(key=lambda x: x['shapeh_score'], reverse=True)
            top = group[:args.shapetime_top_k]
            rest = group[args.shapetime_top_k:]
            top.sort(key=lambda x: x['time_score'], reverse=True)
            combined = top + rest
            for rank, row in enumerate(combined, start=1):
                row['shapetime_rank'] = rank

    # Write pairwise
    pairwise_fields = ['raga_file', 'raga', 'taal', 'makam_file', 'makam', 'usul']
    if args.system in ('shapeh', 'shapetime'):
        pairwise_fields.append('shapeh_score')
    if args.system in ('time', 'shapetime'):
        pairwise_fields.append('time_score')
    if args.system == 'shapetime':
        pairwise_fields.append('shapetime_rank')

    _write_csv(out_dir / 'pairwise_similarity.csv', records, pairwise_fields)

    # Aggregate
    metric_cols = []
    if args.system in ('shapeh', 'shapetime'):
        metric_cols.append('shapeh_score')
    if args.system in ('time', 'shapetime'):
        metric_cols.append('time_score')

    agg_rows = _aggregate_metrics(records, ['raga', 'makam', 'usul'], metric_cols, top_k=args.top_k)
    _write_csv(out_dir / 'agg_similarity_by_raga_makam_usul.csv', agg_rows, ['raga', 'makam', 'usul', 'metric', 'agg', 'value'])

    best_rows = _best_matches(agg_rows, 'raga', 'makam', 'usul')
    _write_csv(out_dir / 'best_makam_per_raga.csv', best_rows, ['raga', 'metric', 'agg', 'best_makam', 'best_usul', 'value'])

    print("Done")


if __name__ == '__main__':
    main()
