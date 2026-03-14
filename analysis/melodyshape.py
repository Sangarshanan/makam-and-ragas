"""
Implementation of the melody shape similarity measure 
from "MelodyShape at MIREX 2014 Symbolic Melodic Similarity" by Julian Urbano
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np

# Constants from MIREX paper
MU_P = 2.1838
MU_T = 0.4772
K_T = 0.5
LAMBDA = MU_P / MU_T


@dataclass(frozen=True)
class Span:
    n: int
    pitch_rel: Tuple[float, ...]
    dur_ratios: Tuple[float, ...]
    poly_pitch: np.poly1d
    poly_time: np.poly1d
    dpoly_pitch: np.poly1d
    dpoly_time: np.poly1d
    sign_start: int
    sign_end: int


def _sign(x: float, eps: float = 1e-9) -> int:
    if x > eps:
        return 1
    if x < -eps:
        return -1
    return 0


def _fit_poly(u: np.ndarray, y: np.ndarray, degree: int) -> np.poly1d:
    coeffs = np.polyfit(u, y, degree)
    return np.poly1d(coeffs)


def build_spans(notes: List[Tuple[float, float]], n: int) -> List[Span]:
    spans: List[Span] = []
    if len(notes) < n:
        return spans

    for i in range(0, len(notes) - n + 1):
        chunk = notes[i:i + n]
        pitches = [p for p, _ in chunk]
        durs = [d for _, d in chunk]
        total = sum(durs)
        if total <= 0:
            continue

        pitch_rel = [0.0] + [p - pitches[0] for p in pitches[1:]]
        dur_ratios = [d / total for d in durs]
        time_pos = [0.0]
        acc = 0.0
        for d in dur_ratios[:-1]:
            acc += d
            time_pos.append(acc)
        time_pos[-1] = 1.0 if time_pos else 1.0

        u = np.linspace(0.0, 1.0, n)
        degree = n - 1
        poly_pitch = _fit_poly(u, np.array(pitch_rel), degree)
        poly_time = _fit_poly(u, np.array(time_pos), degree)

        dpoly_pitch = np.polyder(poly_pitch)
        dpoly_time = np.polyder(poly_time)

        s0 = _sign(float(dpoly_pitch(0.0)))
        s1 = _sign(float(dpoly_pitch(1.0)))

        spans.append(Span(
            n=n,
            pitch_rel=tuple(pitch_rel),
            dur_ratios=tuple(dur_ratios),
            poly_pitch=poly_pitch,
            poly_time=poly_time,
            dpoly_pitch=dpoly_pitch,
            dpoly_time=dpoly_time,
            sign_start=s0,
            sign_end=s1,
        ))

    return spans


def span_shape_key(span: Span) -> Tuple[int, int]:
    return (span.sign_start, span.sign_end)


def compute_span_frequencies(spans_by_doc: List[List[Span]]) -> Dict[Tuple[int, int], float]:
    counts: Dict[Tuple[int, int], int] = {}
    total = 0
    for spans in spans_by_doc:
        for sp in spans:
            key = span_shape_key(sp)
            counts[key] = counts.get(key, 0) + 1
            total += 1
    if total == 0:
        return {}
    return {k: v / total for k, v in counts.items()}


def _shapeh_score(a: Span, b: Span, f: Dict[Tuple[int, int], float]) -> float:
    key_a = span_shape_key(a)
    key_b = span_shape_key(b)
    fa = f.get(key_a, 0.0)
    fb = f.get(key_b, 0.0)
    base = 1.0 - (fa + fb) / 2.0

    same_start = a.sign_start == b.sign_start
    same_end = a.sign_end == b.sign_end

    if same_start and same_end:
        return base
    if (not same_start) and (not same_end):
        return -base
    return 0.0


def shapeh_insertion_score(span: Span, f: Dict[Tuple[int, int], float]) -> float:
    key = span_shape_key(span)
    return -(1.0 - f.get(key, 0.0))


def shapeh_deletion_score(span: Span, f: Dict[Tuple[int, int], float]) -> float:
    key = span_shape_key(span)
    return -(1.0 - f.get(key, 0.0))


def _diff_between_spans(a: Span, b: Span, samples: int = 64) -> Tuple[float, float]:
    u = np.linspace(0.0, 1.0, samples)
    pa = a.dpoly_pitch(u)
    pb = b.dpoly_pitch(u)
    ta = a.dpoly_time(u)
    tb = b.dpoly_time(u)

    diff_p = float(np.trapezoid(np.abs(pa - pb), u))
    diff_t = float(np.trapezoid(np.abs(ta - tb), u))
    return diff_p, diff_t


def _diff_pitch_to_axis(a: Span, samples: int = 64) -> float:
    u = np.linspace(0.0, 1.0, samples)
    pa = a.dpoly_pitch(u)
    return float(np.trapezoid(np.abs(pa), u))


def time_insertion_score(a: Span) -> float:
    diff_p = _diff_pitch_to_axis(a)
    diff_t = 0.0
    return -diff_p - (LAMBDA * K_T * diff_t)


def time_deletion_score(a: Span) -> float:
    diff_p = _diff_pitch_to_axis(a)
    diff_t = 0.0
    return -diff_p - (LAMBDA * K_T * diff_t)


def time_substitution_score(a: Span, b: Span) -> float:
    diff_p, diff_t = _diff_between_spans(a, b)
    return -diff_p - (LAMBDA * K_T * diff_t)


def time_match_score() -> float:
    return 2.0 * MU_P * (1.0 + K_T)


def _hybrid_alignment(seq_a: List[Span],
                      seq_b: List[Span],
                      match_fn,
                      ins_fn,
                      del_fn,
                      sub_fn) -> float:
    na = len(seq_a)
    nb = len(seq_b)
    if na == 0 or nb == 0:
        return float('-inf')

    H = np.zeros((na + 1, nb + 1), dtype=float)

    for i in range(1, na + 1):
        H[i, 0] = H[i - 1, 0] + del_fn(seq_a[i - 1])
    for j in range(1, nb + 1):
        H[0, j] = H[0, j - 1] + ins_fn(seq_b[j - 1])

    best = H[0, 0]
    for i in range(1, na + 1):
        for j in range(1, nb + 1):
            a = seq_a[i - 1]
            b = seq_b[j - 1]

            if a.pitch_rel == b.pitch_rel and a.dur_ratios == b.dur_ratios:
                s = match_fn()
            else:
                s = sub_fn(a, b)

            v = max(
                H[i - 1, j - 1] + s,
                H[i - 1, j] + del_fn(a),
                H[i, j - 1] + ins_fn(b),
            )
            H[i, j] = v
            if v > best:
                best = v

    return float(best)


def shapeh_similarity(seq_a: List[Span], seq_b: List[Span], f: Dict[Tuple[int, int], float]) -> float:
    return _hybrid_alignment(
        seq_a,
        seq_b,
        match_fn=lambda: 0.0,  # match handled in sub_fn when shapes equal
        ins_fn=lambda s: shapeh_insertion_score(s, f),
        del_fn=lambda s: shapeh_deletion_score(s, f),
        sub_fn=lambda a, b: _shapeh_score(a, b, f),
    )


def time_similarity(seq_a: List[Span], seq_b: List[Span]) -> float:
    return _hybrid_alignment(
        seq_a,
        seq_b,
        match_fn=time_match_score,
        ins_fn=time_insertion_score,
        del_fn=time_deletion_score,
        sub_fn=time_substitution_score,
    )
