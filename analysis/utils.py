import math
import numpy as np

# Metric helpers (implemented over span polynomials)
def mean_abs_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.mean(np.abs(p1 - p2))) if len(p1) else float("inf")

def rmse_distance(p1: np.ndarray, p2: np.ndarray) -> float:
    return float(np.sqrt(np.mean((p1 - p2) ** 2))) if len(p1) else float("inf")

def similarity_from_distance(dist: float) -> float:
    if math.isinf(dist) or math.isnan(dist):
        return 0.0
    return 1.0 / (1.0 + dist)

def discrete_frechet_distance(pts1: np.ndarray, pts2: np.ndarray) -> float:
    if len(pts1) == 0 or len(pts2) == 0:
        return float("inf")
    ca = np.full((len(pts1), len(pts2)), -1.0)
    def _c(i, j):
        if ca[i, j] > -1:
            return ca[i, j]
        d = np.linalg.norm(pts1[i] - pts2[j])
        if i == 0 and j == 0:
            ca[i, j] = d
        elif i > 0 and j == 0:
            ca[i, j] = max(_c(i - 1, 0), d)
        elif i == 0 and j > 0:
            ca[i, j] = max(_c(0, j - 1), d)
        else:
            ca[i, j] = max(min(_c(i-1, j), _c(i-1, j-1), _c(i, j-1)), d)
        return ca[i, j]
    return float(_c(len(pts1) - 1, len(pts2) - 1))

def hausdorff_distance(pts1: np.ndarray, pts2: np.ndarray) -> float:
    if len(pts1) == 0 or len(pts2) == 0:
        return float("inf")
    def _directed(a, b):
        return float(np.max([np.min(np.linalg.norm(b - p, axis=1)) for p in a]))
    return max(_directed(pts1, pts2), _directed(pts2, pts1))
