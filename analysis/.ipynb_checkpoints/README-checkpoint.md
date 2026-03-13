# Comparing Melodic Similarity

We are working with purely symbolic data there are challenges in comparing melodies especially for two non western musical traditions that do not have a well defined symbolic representation and also rich in microtonal frequencies and rich ornamentations.

## N-gram

The simplest approach: slice the melody into overlapping windows of n notes and treat each window as a "word." Similarity is then overlap between these vocabularies, like a cosine distance over n-gram histograms.

For Hindustani music specifically, this is nearly useless. A raga phrase in Yaman and the same phrase played with different ornaments (meend, gamak, kan) will share almost no n-grams even though a trained listener hears them as the same phrase.


## Edit Distance (Levenshtein) Approaches

Represent a melody as a string of interval sequences and then compute the minimum number of insertions, deletions, and substitutions to transform one string into another.

This captures structural similarity but its still fundamentally discrete and each "edit" costs the same whether you're one semitone off or an octave off. Ornamentations still do not have a clean discrete representation.

## Hidden Markov Models / Statistical Approaches

Model each raga or melodic style as an HMM or n-gram language model over pitch sequences. Similarity is log-likelihood of one melody under the other's model. To help capture long-range probabilistic structure and characteristic note transition probabilities.

With this approach we would required a larger dataset to draw something statistically meaningful and we still operate over a sequence of discrete observations.

## MelodyShape

This implements a symbolic melodic similarity algorithm that compares melodies by fitting polynomial curves to pitch and timing contours, then aligning them via a sequence alignment (Smith-Waterman-style Dynamic Programming).

There are two similarity measures: ShapeH (shape-based) and Time (continuous curve-based).

**Core Idea:** A melody is chunked into overlapping spans of n notes. Each span is represented not by raw values but by a polynomial curve fitted over its pitch contour and timing ratios. Two melodies are then compared by aligning their span sequences using dynamic programming.

This gives three invariances:

- Transposition invariance — pitches are expressed as intervals relative to the span's first note; the derivative of a transposed melody is identical to the original
- Time-scale invariance — durations become ratios within a span, so a melody at double tempo maps to the same curve
- Position invariance — the hybrid alignment finds the best-matching subsequence, so a query fragment can match anywhere in a longer piece

**Span** is the atomic unit: A window of n consecutive notes described by:

- pitch_rel: pitches relative to the first note in the window (translation-invariant)
- dur_ratios: each note's duration as a fraction of the window's total duration (tempo-invariant)
- poly_pitch, poly_time: degree n-1 polynomials fitted to the pitch/time sequences
- dpoly_pitch, dpoly_time: their derivatives (encoding the contour shape)
- sign_start, sign_end: sign of the pitch derivative at u=0 and u=1, giving a coarse shape label (rising/flat/falling at each end)

A span is a sliding window of n consecutive notes, and every melody is represented as an overlapping sequence of them (like n-grams). Inside each span we do Pitch normalization and Time normalization.

Then a polynomial of degree n−1 is fitted through these normalized values using `np.polyfit` over `u = linspace(0, 1, n)`. You get one polynomial for pitch and one for time. 

Their first derivatives are what actually get used for comparison: because the derivative of a transposed melody is the same as the original (constants vanish under differentiation)

We then use two Similarity Measures

### ShapeH: Coarse Categorical Similarity

ShapeH reduces each span to a shape class: a pair of signs (sign_start, sign_end) where each sign `∈ {-1, 0, +1}` giving 9 possible shape classes (rising→falling, flat→rising, flat→flat, etc.)

**IDF-style weight:** A span shape that appears in 80% of all spans across the corpus tells you very little about melodic identity, like the word "the" in text. The corpus frequency f(shape) is computed across all spans in the collection. This feeds into an IDF-style weight `1 - f(shape)`. Rare shapes (small f) → weight close to 1.0 → high reward for matching. Common shapes (large f) → weight close to 0.0 → matching is nearly worthless.

The paper's "naive rationale": two spans with the same derivative signs are treated as equivalent regardless of how different their actual curvatures are. A gently rising-then-falling arc and a dramatic arc are the same shape class. This is intentionally coarse to be robust to small variations.

### Time: Continuous Integral-Based Similarity

Time uses the actual derivative polynomial curves, not a coarse shape label. The derivative (slope) of that line at every point tells you how fast and in which direction the melody is moving at that moment. That's what Time similarity actually compares.

But we cannot directly use this because pitch slopes and time slopes happen to live on very different numerical scales in practice,  pitch differences tend to be 5–7× bigger than time differences just by coincidence of how music works. So if you just added them together, time would barely matter.


### Sequence Alignment

You have two sequences of spans: say melody A has 10 spans and melody B has 8. They might share a similar passage somewhere in the middle, but have different introductions and endings. How do you find and score the best matching region?

**The Table-Filling Approach** Think of it like filling in a grid where rows = spans of melody A and columns = spans of melody B. Each cell (i, j) stores "the best total score I can achieve by aligning the first i spans of A with the first j spans of B." At each cell you have three choices:

```
Option 1: Match/substitute spans A[i] and B[j]
          → take the score from the diagonal cell + similarity score

Option 2: Skip a span in A (delete)
          → take the score from the cell above + deletion penalty

Option 3: Skip a span in B (insert)
          → take the score from the cell to the left + insertion penalty
```

You pick whichever gives the highest value. This propagates the best possible alignment forward as you fill the table left-to-right, top-to-bottom.

This is the most musically interesting design decision. We can argue that listeners remember how a melody begins but are forgiving about how it ends. So the algorithm:

- **Penalizes mismatches at the start:** the first row and column accumulate gap penalties from position zero, so skipping the opening of either melody costs something
- **Is forgiving at the end:** instead of reading the score from the bottom-right corner (which would require both melodies to be fully accounted for), it takes the maximum value anywhere in the entire table


