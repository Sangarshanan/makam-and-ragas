"""
Pitch Curve Extractor for Swarlipi XML files.

Extracts pitch contours from Bhatkhande notation XML files,
considering tonic frequency, octave markers, and ornaments.
"""

import re
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import xml.etree.ElementTree as ET
from dataclasses import dataclass


# Just Intonation ratios for Indian classical music
# These are the frequency ratios relative to the tonic (Sa)
NOTE_RATIOS = {
    's': 1.0,           # Sa - tonic
    'R': 256/243,       # Re komal (minor second) ~1.053
    'r': 9/8,           # Re shuddha (major second) = 1.125
    'G': 32/27,         # Ga komal (minor third) ~1.185
    'g': 81/64,         # Ga shuddha (major third) ~1.266
    'm': 4/3,           # Ma shuddha (perfect fourth) ~1.333
    'M': 729/512,       # Ma teevra (augmented fourth) ~1.424
    'p': 3/2,           # Pa (perfect fifth) = 1.5
    'D': 128/81,        # Dha komal (minor sixth) ~1.580
    'd': 27/16,         # Dha shuddha (major sixth) ~1.688
    'N': 16/9,          # Ni komal (minor seventh) ~1.778
    'n': 243/128,       # Ni shuddha (major seventh) ~1.898
}

# Chhand symbols indicate notes per beat
CHHAND_MULTIPLIERS = {
    '@': 2,   # Dugun - 2 notes per beat
    '#': 3,   # Tigun - 3 notes per beat
    '$': 4,   # Chaugun - 4 notes per beat
    '%': 5,   # Pachgun - 5 notes per beat
    '^': 6,   # Chhatgun - 6 notes per beat
    '&': 7,   # Satgun - 7 notes per beat
    '*': 8,   # Athgun - 8 notes per beat
    '`': 4,   # Lower Chaugun
    '!': 6,   # Lower Chhatgun
    '~': 8,   # Lower Athgun
}


@dataclass
class PitchEvent:
    """Represents a pitch event in time."""
    start_time: float       # Start time in beats
    duration: float         # Duration in beats
    frequency: float        # Frequency in Hz (0 for rest)
    note_name: str          # Original note name
    is_meend: bool = False  # Part of a meend glide
    meend_target: float = 0 # Target frequency for meend end


@dataclass
class PitchCurve:
    """Complete pitch curve for a composition."""
    times: np.ndarray       # Time points (in beats)
    frequencies: np.ndarray # Frequencies at each time point
    title: str
    raag: str
    taal: str
    tonic_freq: float
    

class PitchExtractor:
    """
    Extract pitch curves from Swarlipi XML files.
    
    Handles:
    - Note to frequency mapping using just intonation
    - Octave markers (u/U for upper, l/L for lower)
    - Chhand/laya markers for timing
    - Meend (glide) ornaments
    - Rests and sustained notes
    """
    
    def __init__(self, tonic_freq: float = 261.63):
        """
        Initialize the extractor.
        
        Args:
            tonic_freq: Frequency of Sa in Hz (default: C4 = 261.63 Hz)
        """
        self.tonic_freq = tonic_freq
        self.beat_duration = 1.0  # Duration of one beat in arbitrary units
        self.samples_per_beat = 100  # Resolution for continuous curves
        
    def note_to_frequency(self, note: str, octave_shift: int = 0) -> float:
        """
        Convert a note name to frequency.
        
        Args:
            note: Single character note (s, r, R, g, G, m, M, p, d, D, n, N)
            octave_shift: -2, -1, 0, 1, or 2 for octave transposition
            
        Returns:
            Frequency in Hz
        """
        if note not in NOTE_RATIOS:
            return 0.0  # Unknown note
        
        base_freq = self.tonic_freq * NOTE_RATIOS[note]
        return base_freq * (2 ** octave_shift)
    
    def parse_note_token(self, token: str) -> Tuple[Optional[str], int]:
        """
        Parse a note token to extract note and octave.
        
        Args:
            token: Note token like 's', 'gu', 'Dl', 'pU', etc.
            
        Returns:
            Tuple of (note_char, octave_shift) or (None, 0) for non-notes
        """
        if not token:
            return None, 0
            
        # First character should be the note
        note_char = token[0]
        
        if note_char not in NOTE_RATIOS:
            return None, 0
        
        # Check for octave markers
        octave_shift = 0
        if len(token) > 1:
            suffix = token[1:]
            if 'U' in suffix:
                octave_shift = 2   # Ati Tar (two octaves up)
            elif 'u' in suffix:
                octave_shift = 1   # Tar (one octave up)
            elif 'L' in suffix:
                octave_shift = -2  # Ati Mandra (two octaves down)
            elif 'l' in suffix:
                octave_shift = -1  # Mandra (one octave down)
        
        return note_char, octave_shift
    
    def tokenize_content(self, content: str) -> List[str]:
        """
        Tokenize notation content into individual elements.
        
        Args:
            content: Raw content string from XML
            
        Returns:
            List of tokens (notes, rests, ornament markers, etc.)
        """
        tokens = []
        i = 0
        
        while i < len(content):
            char = content[i]
            
            # Skip whitespace
            if char.isspace():
                i += 1
                continue
            
            # Check for note with possible octave suffix
            if char in NOTE_RATIOS:
                token = char
                # Look ahead for octave markers
                j = i + 1
                while j < len(content) and content[j] in 'uUlL':
                    token += content[j]
                    j += 1
                tokens.append(token)
                i = j
                continue
            
            # Ornament and structural markers
            if char in '-_qwWeEQq()@#$%^&*`!~':
                tokens.append(char)
                i += 1
                continue
            
            # Skip other characters (like <sup> tags, commas, etc.)
            i += 1
        
        return tokens
    
    def extract_pitch_events(self, xml_path: str) -> Tuple[List[PitchEvent], Dict]:
        """
        Extract pitch events from an XML file.
        
        Args:
            xml_path: Path to the Swarlipi XML file
            
        Returns:
            Tuple of (list of PitchEvent, metadata dict)
        """
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Extract metadata
        metadata = {
            'title': self._get_text(root, ".//INFO/TITLE"),
            'raag': self._get_text(root, ".//RAAG/RAAG_NAME"),
            'taal': self._get_text(root, ".//TAAL/TAAL_NAME"),
            'maatra': int(self._get_text(root, ".//TAAL/MAATRA") or 16),
        }
        
        # Extract all content
        contents = []
        for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
            if content_elem.text:
                contents.append(content_elem.text)
        
        # Process content
        all_tokens = []
        for content in contents:
            tokens = self.tokenize_content(content)
            all_tokens.extend(tokens)
        
        # Convert tokens to pitch events
        events = self._tokens_to_events(all_tokens)
        
        return events, metadata
    
    def _get_text(self, root: ET.Element, xpath: str) -> str:
        """Helper to get text from XML element."""
        elem = root.find(xpath)
        return elem.text if elem is not None and elem.text else ""
    
    def _tokens_to_events(self, tokens: List[str]) -> List[PitchEvent]:
        """
        Convert tokens to pitch events.
        
        Handles:
        - Notes with octave markers
        - Rests (-)
        - Sustained notes (_)
        - Chhand markers for timing
        - Meend sequences
        """
        events = []
        current_time = 0.0
        current_duration = 1.0  # Default: 1 beat per note
        notes_per_beat = 1
        
        # Track meend state
        in_meend = False
        meend_notes = []
        
        # Track last note for sustain
        last_frequency = 0.0
        last_note_name = ""
        
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # Chhand markers - affect timing
            if token in CHHAND_MULTIPLIERS:
                notes_per_beat = CHHAND_MULTIPLIERS[token]
                current_duration = 1.0 / notes_per_beat
                i += 1
                continue
            
            # Meend start
            if token == 'q':
                in_meend = True
                meend_notes = []
                i += 1
                continue
            
            # Meend continue
            if token == 'w' or token == 'W':
                i += 1
                continue
            
            # Meend end
            if token == 'e':
                in_meend = False
                # Process collected meend notes
                if len(meend_notes) >= 2:
                    events.extend(self._create_meend_events(
                        meend_notes, current_time, current_duration
                    ))
                    current_time += len(meend_notes) * current_duration
                meend_notes = []
                i += 1
                continue
            
            # Rest
            if token == '-':
                events.append(PitchEvent(
                    start_time=current_time,
                    duration=current_duration,
                    frequency=0.0,
                    note_name='rest'
                ))
                current_time += current_duration
                i += 1
                continue
            
            # Sustained note (repeat last note)
            if token == '_':
                if last_frequency > 0:
                    events.append(PitchEvent(
                        start_time=current_time,
                        duration=current_duration,
                        frequency=last_frequency,
                        note_name=last_note_name + " (sustained)"
                    ))
                current_time += current_duration
                i += 1
                continue
            
            # Murki markers - skip for now (mark notes inside)
            if token in '()':
                i += 1
                continue
            
            # Parse as note
            note_char, octave_shift = self.parse_note_token(token)
            
            if note_char:
                frequency = self.note_to_frequency(note_char, octave_shift)
                
                if in_meend:
                    meend_notes.append((note_char, octave_shift, frequency))
                else:
                    events.append(PitchEvent(
                        start_time=current_time,
                        duration=current_duration,
                        frequency=frequency,
                        note_name=token
                    ))
                    current_time += current_duration
                    last_frequency = frequency
                    last_note_name = token
            
            i += 1
        
        return events
    
    def _create_meend_events(self, meend_notes: List[Tuple], 
                             start_time: float, 
                             note_duration: float) -> List[PitchEvent]:
        """
        Create pitch events for a meend sequence with gliding frequencies.
        """
        events = []
        
        for idx, (note_char, octave_shift, frequency) in enumerate(meend_notes):
            is_last = (idx == len(meend_notes) - 1)
            
            if is_last:
                target_freq = 0
            else:
                target_freq = meend_notes[idx + 1][2]
            
            events.append(PitchEvent(
                start_time=start_time + idx * note_duration,
                duration=note_duration,
                frequency=frequency,
                note_name=note_char,
                is_meend=True,
                meend_target=target_freq
            ))
        
        return events
    
    def events_to_curve(self, events: List[PitchEvent]) -> PitchCurve:
        """
        Convert discrete pitch events to a continuous pitch curve.
        
        Args:
            events: List of PitchEvent objects
            
        Returns:
            PitchCurve with time and frequency arrays
        """
        if not events:
            return PitchCurve(
                times=np.array([]),
                frequencies=np.array([]),
                title="",
                raag="",
                taal="",
                tonic_freq=self.tonic_freq
            )
        
        # Calculate total duration
        total_time = max(e.start_time + e.duration for e in events)
        
        # Create time array
        num_samples = int(total_time * self.samples_per_beat)
        times = np.linspace(0, total_time, num_samples)
        frequencies = np.zeros(num_samples)
        
        for event in events:
            start_idx = int(event.start_time * self.samples_per_beat)
            end_idx = int((event.start_time + event.duration) * self.samples_per_beat)
            end_idx = min(end_idx, num_samples)
            
            if event.frequency == 0:
                # Rest - keep as zero
                continue
            
            if event.is_meend and event.meend_target > 0:
                # Create glide from current frequency to target
                glide = np.linspace(event.frequency, event.meend_target, end_idx - start_idx)
                frequencies[start_idx:end_idx] = glide
            else:
                # Constant frequency
                frequencies[start_idx:end_idx] = event.frequency
        
        return PitchCurve(
            times=times,
            frequencies=frequencies,
            title="",
            raag="",
            taal="",
            tonic_freq=self.tonic_freq
        )
    
    def extract_pitch_curve(self, xml_path: str) -> PitchCurve:
        """
        Extract complete pitch curve from XML file.
        
        Args:
            xml_path: Path to Swarlipi XML file
            
        Returns:
            PitchCurve object with all data
        """
        events, metadata = self.extract_pitch_events(xml_path)
        curve = self.events_to_curve(events)
        
        curve.title = metadata['title']
        curve.raag = metadata['raag']
        curve.taal = metadata['taal']
        
        return curve


def plot_pitch_curve(curve: PitchCurve, 
                     show_note_lines: bool = True,
                     figsize: Tuple[int, int] = (14, 6),
                     save_path: Optional[str] = None) -> None:
    """
    Plot a pitch curve with optional note reference lines.
    
    Args:
        curve: PitchCurve object to plot
        show_note_lines: Whether to show horizontal lines for each note
        figsize: Figure size
        save_path: If provided, save plot to this path
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    # Plot pitch curve (convert to cents relative to tonic for better visualization)
    # Or plot raw frequency
    mask = curve.frequencies > 0  # Only plot non-zero (non-rest) values
    
    times_valid = curve.times[mask]
    freqs_valid = curve.frequencies[mask]
    
    # Convert to cents relative to tonic for better visualization
    cents = 1200 * np.log2(freqs_valid / curve.tonic_freq)
    
    ax.plot(times_valid, cents, 'b-', marker='o', markersize=3, linewidth=1.5, label='Pitch')
    ax.scatter(times_valid[::10], cents[::10], c='blue', s=5, alpha=0.5)
    
    if show_note_lines:
        # Add horizontal lines for each note
        note_cents = {
            'Sa': 0,
            'Re♭': 1200 * np.log2(256/243),
            'Re': 1200 * np.log2(9/8),
            'Ga♭': 1200 * np.log2(32/27),
            'Ga': 1200 * np.log2(81/64),
            'Ma': 1200 * np.log2(4/3),
            'Ma♯': 1200 * np.log2(729/512),
            'Pa': 1200 * np.log2(3/2),
            'Dha♭': 1200 * np.log2(128/81),
            'Dha': 1200 * np.log2(27/16),
            'Ni♭': 1200 * np.log2(16/9),
            'Ni': 1200 * np.log2(243/128),
            'Sa\'': 1200,  # Upper octave Sa
        }
        
        for note_name, cent_value in note_cents.items():
            ax.axhline(y=cent_value, color='gray', linestyle='--', 
                      alpha=0.3, linewidth=0.5)
            ax.text(curve.times[-1] * 1.01, cent_value, note_name, 
                   va='center', fontsize=8, color='gray')
    
    ax.set_xlabel('Time (beats)', fontsize=12)
    ax.set_ylabel('Pitch (cents relative to Sa)', fontsize=12)
    ax.set_title(f'{curve.title}\nRaag: {curve.raag} | Taal: {curve.taal} | Tonic: {curve.tonic_freq:.1f} Hz',
                fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend()
    
    plt.tight_layout()
    
    plt.show()
    

def plot_pitch_curve_frequency(curve: PitchCurve,
                                figsize: Tuple[int, int] = (14, 6),
                                save_path: Optional[str] = None) -> None:
    """
    Plot pitch curve showing actual frequencies in Hz.
    
    Args:
        curve: PitchCurve object to plot
        figsize: Figure size
        save_path: If provided, save plot to this path
    """
    fig, ax = plt.subplots(figsize=figsize)
    
    mask = curve.frequencies > 0
    times_valid = curve.times[mask]
    freqs_valid = curve.frequencies[mask]
    
    ax.plot(times_valid, freqs_valid, 'b-', marker='o', markersize=3, linewidth=1.5, label='Pitch')
    
    # Add horizontal lines for key notes
    tonic = curve.tonic_freq
    note_freqs = {
        'Sa': tonic,
        'Pa': tonic * 3/2,
        'Sa\'': tonic * 2,
    }
    
    for note_name, freq in note_freqs.items():
        ax.axhline(y=freq, color='red', linestyle='--', alpha=0.5, linewidth=1)
        ax.text(curve.times[-1] * 1.01, freq, note_name, va='center', fontsize=9)
    
    ax.set_xlabel('Time (beats)', fontsize=12)
    ax.set_ylabel('Frequency (Hz)', fontsize=12)
    ax.set_title(f'{curve.title}\nRaag: {curve.raag} | Taal: {curve.taal}',
                fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.set_yscale('log')  # Log scale for frequency
    ax.legend()
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close(fig)


def plot_multiple_curves(curves: List[PitchCurve],
                         figsize: Tuple[int, int] = (14, 8),
                         save_path: Optional[str] = None) -> None:
    """
    Plot multiple pitch curves for comparison.
    """
    n_curves = len(curves)
    fig, axes = plt.subplots(n_curves, 1, figsize=(figsize[0], figsize[1] * n_curves // 2),
                            sharex=False)
    
    if n_curves == 1:
        axes = [axes]
    
    colors = plt.cm.tab10(np.linspace(0, 1, n_curves))
    
    for idx, (curve, ax, color) in enumerate(zip(curves, axes, colors)):
        mask = curve.frequencies > 0
        times_valid = curve.times[mask]
        freqs_valid = curve.frequencies[mask]
        
        cents = 1200 * np.log2(freqs_valid / curve.tonic_freq)
        
        ax.plot(times_valid, cents, color=color, linewidth=1.5)
        ax.set_ylabel('Cents', fontsize=10)
        ax.set_title(f'{curve.title} ({curve.raag})', fontsize=10)
        ax.grid(True, alpha=0.3)
        
        # Add Sa and Pa lines
        ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
        ax.axhline(y=1200 * np.log2(3/2), color='gray', linestyle='--', alpha=0.5)
    
    axes[-1].set_xlabel('Time (beats)', fontsize=12)
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')
    else:
        plt.show()
    
    plt.close(fig)


# Example usage and demonstration
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Default paths
    workspace = Path(__file__).parent
    dataset_path = workspace / "Bhatkhande Dataset"
    
    # Get XML file from command line or use first file in dataset
    if len(sys.argv) > 1:
        xml_file = sys.argv[1]
    else:
        xml_files = list(dataset_path.glob("*.xml"))
        if xml_files:
            xml_file = str(xml_files[0])
        else:
            print("No XML files found in dataset")
            sys.exit(1)
    
    # Set tonic frequency (common choices: C4=261.63, D4=293.66, etc.)
    # For classical Hindustani, common tonics are around 240-300 Hz
    tonic_freq = 261.63  # C4
    
    print(f"Extracting pitch curve from: {xml_file}")
    print(f"Tonic frequency: {tonic_freq} Hz (Sa)")
    print()
    
    # Create extractor
    extractor = PitchExtractor(tonic_freq=tonic_freq)
    
    # Extract pitch curve
    curve = extractor.extract_pitch_curve(xml_file)
    
    print(f"Title: {curve.title}")
    print(f"Raag: {curve.raag}")
    print(f"Taal: {curve.taal}")
    print(f"Duration: {curve.times[-1]:.1f} beats" if len(curve.times) > 0 else "No notes found")
    print()
    
    # Plot the curve
    if len(curve.frequencies) > 0:
        # Generate output filename from input
        input_path = Path(xml_file)
        output_file = workspace / f"{input_path.stem}_pitch_curve.png"
        
        # Save and display plot
        plot_pitch_curve(curve, show_note_lines=True, save_path=str(output_file))
    else:
        print("No pitch data to plot")
