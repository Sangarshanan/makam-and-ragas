#!/usr/bin/env python3
"""
ShapeTime metric calculator for Raag Bhairav vs all Makams.

ShapeTime algorithm:
1. Run ShapeH (3-note spans, ignores time, uses IDF weighting) to rank all makams
2. Re-rank the top-k results using Time score (4-note spans, considers time dimension)
"""

import argparse
import csv
import sys
import time as time_module
from pathlib import Path
from statistics import mean, median
from typing import Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from raga.pitch_extractor import load_raga_notes
from makam.pitch_extractor import load_makam_notes
from melodyshape import (
    build_spans,
    compute_span_frequencies,
    shapeh_similarity,
    time_similarity,
)

from tqdm import tqdm as _tqdm

def _tie_cutoff_indices(scores: List[float], k: int, eps: float = 1e-9) -> int:
    """
    Return the cutoff index (exclusive) that includes all items tied
    with the k-th score. If k >= len(scores), returns len(scores).
    """
    if k <= 0:
        return 0
    if k >= len(scores):
        return len(scores)
    cutoff_score = scores[k - 1]
    idx = k
    while idx < len(scores) and abs(scores[idx] - cutoff_score) <= eps:
        idx += 1
    return idx


def compute_shapetime_ranking(
    raga_item: Dict,
    makam_items: List[Dict],
    span_freq: Dict[Tuple[int, int], float],
    top_k: int = 10,
) -> List[Dict]:
    """
    Compute ShapeTime ranking for a single raga against all makams.
    
    Returns list of dicts with shapeh_score, time_score, and shapetime_rank.
    """
    results = []
    
    # Step 1: Compute ShapeH scores for all makams
    for m in makam_items:
        shapeh_score = shapeh_similarity(
            raga_item.get('spans_shapeh', []),
            m.get('spans_shapeh', []),
            span_freq
        )
        results.append({
            'makam_file': m['file'],
            'makam': m['makam'],
            'usul': m['usul'],
            'shapeh_score': shapeh_score,
            'time_score': None,
            'shapetime_rank': None,
        })
    
    # Step 2: Sort by ShapeH score (descending) to get initial ranking
    results.sort(key=lambda x: x['shapeh_score'], reverse=True)

    # Step 3: Compute Time scores for top-k (including ties at k-th)
    shapeh_scores = [r['shapeh_score'] for r in results]
    cutoff = _tie_cutoff_indices(shapeh_scores, top_k)

    for res in results[:cutoff]:
        makam = next(m for m in makam_items if m['file'] == res['makam_file'])
        time_score = time_similarity(
            raga_item.get('spans_time', []),
            makam.get('spans_time', [])
        )
        res['time_score'] = time_score

    # Step 4: Re-rank top-k (plus ties) by Time score
    top_k_items = results[:cutoff]
    rest_items = results[cutoff:]
    top_k_items.sort(key=lambda x: x['time_score'], reverse=True)

    # Combine and assign final ranks
    final_results = top_k_items + rest_items
    for rank, res in enumerate(final_results, start=1):
        res['shapetime_rank'] = rank
        # ShapeTime score follows the re-ranking rule:
        # use Time for the re-ranked subset, otherwise ShapeH.
        res['shapetime_score'] = res['time_score'] if res['time_score'] is not None else res['shapeh_score']

    return final_results


def main():
    parser = argparse.ArgumentParser(
        description='Compute ShapeTime metric for Raag Bhairav vs all Makams'
    )
    parser.add_argument('--raga-dir', default='datasets/ragas',
                        help='Directory containing raga XML files')
    parser.add_argument('--makam-dir', default='datasets/makams',
                        help='Directory containing makam XML files')
    parser.add_argument('--top-k', type=int, default=10,
                        help='Number of top ShapeH results to re-rank with Time')
    parser.add_argument('--out-dir', default='analysis/output/shapetime',
                        help='Output directory for results')
    parser.add_argument('--log-every', type=float, default=5.0,
                        help='Log progress every N seconds')
    args = parser.parse_args()

    raga_dir = Path(args.raga_dir)
    makam_dir = Path(args.makam_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load only Bhairav raga files
    bhairav_files = sorted(raga_dir.glob('Bhairav-*.xml'))
    print(f"Found {len(bhairav_files)} Bhairav raga files")
    
    if not bhairav_files:
        print("ERROR: No Bhairav files found!")
        sys.exit(1)

    makam_files = sorted(makam_dir.glob('*.xml'))
    print(f"Found {len(makam_files)} makam files")

    # Load Bhairav raga notes
    raga_items = []
    print(f"\nLoading Bhairav ragas...")
    last_log = time_module.time()
    for f in _tqdm(bhairav_files, desc="Loading Bhairav", unit="file"):
        notes, meta = load_raga_notes(str(f))
        if not notes:
            continue
        raga_items.append({
            'file': f.name,
            'raag': meta.get('raag', 'Bhairav'),
            'taal': meta.get('taal', ''),
            'notes': notes,
        })
        if time_module.time() - last_log >= args.log_every:
            print(f"  loaded {len(raga_items)} Bhairav melodies...")
            last_log = time_module.time()
    print(f"Loaded {len(raga_items)} Bhairav melodies")

    # Load makam notes
    makam_items = []
    print(f"\nLoading makams...")
    last_log = time_module.time()
    for f in _tqdm(makam_files, desc="Loading makams", unit="file"):
        notes, meta = load_makam_notes(str(f))
        if not notes:
            continue
        makam_items.append({
            'file': f.name,
            'makam': meta.get('makam', ''),
            'usul': meta.get('usul', ''),
            'notes': notes,
        })
        if time_module.time() - last_log >= args.log_every:
            print(f"  loaded {len(makam_items)} makam melodies...")
            last_log = time_module.time()
    print(f"Loaded {len(makam_items)} makam melodies")

    # Build spans for ShapeH (3-note) and Time (4-note)
    print("\nBuilding spline spans...")
    for r in raga_items:
        r['spans_shapeh'] = build_spans(r['notes'], 3)
        r['spans_time'] = build_spans(r['notes'], 4)

    for m in makam_items:
        m['spans_shapeh'] = build_spans(m['notes'], 3)
        m['spans_time'] = build_spans(m['notes'], 4)

    # Compute span frequencies (IDF) from makam collection
    print("Computing span frequencies (IDF)...")
    span_freq = compute_span_frequencies([m.get('spans_shapeh', []) for m in makam_items])

    # Compute ShapeTime for each Bhairav file
    print(f"\nComputing ShapeTime rankings (top-k={args.top_k})...")
    all_results = []
    last_log = time_module.time()

    for i, r in enumerate(_tqdm(raga_items, desc="ShapeTime", unit="raga"), start=1):
        results = compute_shapetime_ranking(r, makam_items, span_freq, top_k=args.top_k)
        
        for res in results:
            all_results.append({
                'raga_file': r['file'],
                'raga': r['raag'],
                'taal': r['taal'],
                **res
            })
        
        if time_module.time() - last_log >= args.log_every:
            pct = (i) / len(raga_items) * 100
            print(f"  processed {i}/{len(raga_items)} ({pct:.1f}%)")
            last_log = time_module.time()
    
    print(f"Computed {len(all_results)} pairwise comparisons")

    # Write detailed pairwise results
    pairwise_path = out_dir / 'shapetime_pairwise.csv'
    fieldnames = [
        'raga_file', 'raga', 'taal', 'makam_file', 'makam', 'usul',
        'shapeh_score', 'time_score', 'shapetime_rank', 'shapetime_score'
    ]
    with open(pairwise_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for r in all_results:
            writer.writerow(r)
    print(f"\nWrote pairwise results to: {pairwise_path}")

    # Aggregate by makam - find best makams for Bhairav
    print("Aggregating results by makam...")
    by_makam: Dict[str, List[Dict]] = {}
    for r in all_results:
        key = (r['makam'], r['usul'])
        by_makam.setdefault(key, []).append(r)

    agg_results = []
    for (makam, usul), records in by_makam.items():
        shapeh_scores = [r['shapeh_score'] for r in records]
        time_scores = [r['time_score'] for r in records if r['time_score'] is not None]
        ranks = [r['shapetime_rank'] for r in records]
        
        agg_results.append({
            'makam': makam,
            'usul': usul,
            'count': len(records),
            'shapeh_mean': mean(shapeh_scores),
            'shapeh_max': max(shapeh_scores),
            'shapeh_median': median(shapeh_scores),
            'time_mean': mean(time_scores) if time_scores else None,
            'time_max': max(time_scores) if time_scores else None,
            'avg_rank': mean(ranks),
            'best_rank': min(ranks),
            'top_k_count': len(time_scores),  # How many times in top-k
        })

    # Sort by best average rank
    agg_results.sort(key=lambda x: x['avg_rank'])

    agg_path = out_dir / 'shapetime_by_makam.csv'
    agg_fieldnames = [
        'makam', 'usul', 'count', 'shapeh_mean', 'shapeh_max', 'shapeh_median',
        'time_mean', 'time_max', 'avg_rank', 'best_rank', 'top_k_count'
    ]
    with open(agg_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        for r in agg_results:
            writer.writerow(r)
    print(f"Wrote aggregated results to: {agg_path}")

    # Summary: top 10 makams most similar to Bhairav
    print("\n" + "=" * 60)
    print("TOP 10 MAKAMS MOST SIMILAR TO RAAG BHAIRAV (by avg ShapeTime rank)")
    print("=" * 60)
    for i, r in enumerate(agg_results[:10], 1):
        time_str = f"{r['time_mean']:.2f}" if r['time_mean'] else "N/A"
        print(f"{i:2d}. {r['makam']:20s} (usul: {r['usul']:15s}) "
              f"avg_rank={r['avg_rank']:.1f}, shapeh={r['shapeh_mean']:.2f}, "
              f"time={time_str}")

    # Also output unique makam rankings (collapse usul variations)
    print("\nAggregating by makam only (ignoring usul)...")
    by_makam_only: Dict[str, List[Dict]] = {}
    for r in agg_results:
        by_makam_only.setdefault(r['makam'], []).append(r)

    makam_only_results = []
    for makam, records in by_makam_only.items():
        all_shapeh = [r['shapeh_mean'] for r in records]
        all_ranks = [r['avg_rank'] for r in records]
        makam_only_results.append({
            'makam': makam,
            'num_usuls': len(records),
            'shapeh_mean': mean(all_shapeh),
            'shapeh_best': max(all_shapeh),
            'avg_rank': mean(all_ranks),
            'best_rank': min(all_ranks),
        })

    makam_only_results.sort(key=lambda x: x['avg_rank'])

    makam_only_path = out_dir / 'shapetime_by_makam_only.csv'
    with open(makam_only_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(makam_only_results[0].keys()))
        writer.writeheader()
        for r in makam_only_results:
            writer.writerow(r)
    print(f"Wrote makam-only results to: {makam_only_path}")

    print("\n" + "=" * 60)
    print("TOP 10 MAKAMS (by makam name, ignoring usul)")
    print("=" * 60)
    for i, r in enumerate(makam_only_results[:10], 1):
        print(f"{i:2d}. {r['makam']:20s} usuls={r['num_usuls']:2d}, "
              f"avg_rank={r['avg_rank']:.1f}, shapeh={r['shapeh_mean']:.2f}")

    print("\nDone!")


if __name__ == '__main__':
    main()
