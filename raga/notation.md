# Ome Bhatkhande Hindi Notation Symbols

This document describes the symbols used in the Bhatkhande notation system as implemented in the Sangeet dataset.

**Reference:** [Ome Bhatkhande Hindi Font Documentation](https://omenad.github.io/fonts/ome-bhatkhande-hindi/)

---

## Swar (Notes)

### Regular Notes (Shuddha Swar)
| Note | Key | Description |
|------|-----|-------------|
| Sa | `s` | Shadja |
| Re | `r` | Rishabh (natural) |
| Ga | `g` | Gandhar (natural) |
| Ma | `m` | Madhyam (natural) |
| Pa | `p` | Pancham |
| Dha | `d` | Dhaivat (natural) |
| Ni | `n` | Nishad (natural) |

### Variant Notes (Vikrit Swar)
| Note | Key | Description |
|------|-----|-------------|
| Komal Re | `R` | Flat Rishabh |
| Komal Ga | `G` | Flat Gandhar |
| Teevra Ma | `M` | Sharp Madhyam |
| Komal Dha | `D` | Flat Dhaivat |
| Komal Ni | `N` | Flat Nishad |

### Octaves (Saptak)
| Octave | Suffix | Example | Description |
|--------|--------|---------|-------------|
| Mandra (Lower) | `l` | `Ml` | Lower octave |
| Madhya (Middle) | (none) | `p` | Middle octave (default) |
| Tar (Upper) | `u` | `Du` | Upper octave |
| Ati Mandra | `L` | `GL` | Two octaves lower |
| Ati Tar | `U` | `GU` | Two octaves upper |

---

## Meend (Glide/Portamento)

Meend represents a continuous glide between notes. The symbols are used as a sequence.

| Symbol | Key | Name | Description |
|--------|-----|------|-------------|
| Meend Start | `q` | meend_start | Beginning of meend |
| Meend Continue | `w` | meend_continue | Intermediate notes in meend |
| Meend Stroke | `W` | meend_stroke | Note requiring a stroke to continue |
| Meend End | `e` | meend_end | Final note of meend |
| Ghaseet Start | `Q` | ghaseet_start | Reverse meend start |
| Ghaseet End | `E` | ghaseet_end | Reverse meend end |

**Example:** `qswrwgem` = Meend from Sa through Re, Ga to Ma

---

## Murki

Quick ornamental movement from a note to adjacent notes and back.

| Symbol | Key | Name | Description |
|--------|-----|------|-------------|
| Murki Start | `(` | murki_start | Opening parenthesis |
| Murki End | `)` | murki_end | Closing parenthesis |

**Example:** `(p)` = Quick movement around Pa (could be Mpdp, dpMp, or pMdp)

---

## Chhand (Laya/Tempo Groupings)

Chhand symbols indicate how many notes are played per beat. They are zero-width and placed before the notes they affect.

### Primary Chhand
| Symbol | Key | Name | Notes/Beat |
|--------|-----|------|------------|
| Dugun | `@` | dugun | 2 |
| Tigun | `#` | tigun | 3 |
| Chaugun | `$` | chaugun | 4 |
| Pachgun | `%` | pachgun | 5 |
| Chhatgun | `^` | chhatgun | 6 |
| Satgun | `&` | satgun | 7 |
| Athgun | `*` | athgun | 8 |

### Lower Chhand (for larger groupings)
| Symbol | Key | Name | Notes/Beat |
|--------|-----|------|------------|
| Lower Chaugun | `` ` `` | lower_chaugun | 4 |
| Lower Chhatgun | `!` | lower_chhatgun | 6 |
| Lower Athgun | `~` | lower_athgun | 8 |

**Note:** Lower versions are used in combination with primary chhand for complex layakari (e.g., 16 or 24 notes per beat).

---

## Kan and Krintan

Grace notes rendered using HTML superscript.

| Type | Notation | Description |
|------|----------|-------------|
| Kan | `<sup>m</sup>p` | Single grace note (m) before p |
| Krintan | `<sup>m3</sup>p` | Grace note repeated 3 times |

---

## Mizrab Ke Bol (Strokes)

| Symbol | Key | Name | Description |
|--------|-----|------|-------------|
| Da | `;` | da | Down stroke |
| Ra | `'` | ra | Up stroke |
| Daa | `[` | daa | Emphasized down stroke |
| Raa | `]` | raa | Emphasized up stroke |
| Dir | `\` | dir | Combined stroke (takes 2 spaces) |

---

## Structural Symbols

| Symbol | Key | Name | Description |
|--------|-----|------|-------------|
| Khali | `-` | khali | Rest / empty beat |
| Long Dash | `_` | long_dash | Sustained note |
| Sam | `x` | sam | First beat of cycle |
| Plus | `+` | plus | Khali position marker |
| Beat Divider | `a` | beat_divider | Separates beats |
| Phase Divider | `A` | phase_divider | Separates phrases/sections |
| Comma | `,` | comma | Breath mark |

---

## Dataset Statistics

Based on analysis of 116 compositions in the Bhatkhande Dataset:

### Laya Usage
| Laya | Occurrences | Compositions |
|------|-------------|--------------|
| Dugun (@) | 980 | 105 |
| Tigun (#) | 80 | 26 |
| Chaugun ($) | 35 | 10 |
| Lower Chaugun (`) | 26 | 10 |
| Pachgun (%) | 11 | 8 |
| Lower Chhatgun (!) | 10 | 6 |
| Lower Athgun (~) | 5 | 3 |
| Chhatgun (^) | 4 | 3 |

### Ornament Usage
| Ornament | Occurrences | Compositions |
|----------|-------------|--------------|
| Meend (q/w/e) | 120+ | 59 |
| Murki (()) | 48 | 31 |

---

## References

1. **Ome Bhatkhande Hindi Font**: https://omenad.github.io/fonts/ome-bhatkhande-hindi/
2. **Ome Swarlipi Font**: https://omenad.github.io/fonts/ome-swarlipi/
3. **Omenad Fonts Project**: https://github.com/omenad/fonts
4. **Dataset Source**: Kramik Pustak Malika by Vishnu Narayan Bhatkhande

---

## Usage with Python Extractor

```python
from swarlipi_extractor import SwarlipiExtractor

extractor = SwarlipiExtractor("Bhatkhande Dataset")

# Find compositions with meend
meend_compositions = extractor.find_compositions_with_meend()

# Find compositions with murki
murki_compositions = extractor.find_compositions_with_murki()

# Get laya statistics
laya_stats = extractor.get_laya_statistics()

# Find compositions using dugun
dugun_compositions = extractor.find_compositions_with_laya('dugun')

# Get ornament statistics
ornament_stats = extractor.get_ornament_statistics()
```
