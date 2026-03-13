import matplotlib.pyplot as plt
# Pitch curve extractor for Turkish Makam MusicXML
import numpy as np
from .parser import parse_makam_xml

class MakamPitchCurve:
	"""
	Extracts pitch curves from a Makam MusicXML file, given a tonic frequency.
	"""
	def __init__(self, xml_path, tonic_freq=261.63):
		self.xml_path = xml_path
		self.tonic_freq = tonic_freq
		self.meta, self.pitches, self.durations, self.tonic_pitch = parse_makam_xml(xml_path)

	def get_pitch_curve(self, time_unit=1.0):
		"""
		Returns:
			times: np.ndarray of time points (in time_unit, e.g., beats)
			freqs: np.ndarray of frequencies in Hz (0 for rests)
		"""
		# Convert absolute pitches to intervals from tonic
		rel_pitches = np.array(self.pitches) - self.tonic_pitch
		# Convert to frequency ratios
		ratios = 2 ** (rel_pitches / 12)
		freqs = self.tonic_freq * ratios

		# Build time axis
		times = [0]
		for dur in self.durations:
			times.append(times[-1] + dur * time_unit)
		times = np.array(times[:-1])  # last time is end of last note

		return times, freqs

	def get_metadata(self):
		return self.meta

	def plot_pitch_curve(self, time_unit=1.0, ax=None, title=None):
		"""
		Plot the pitch curve (time vs frequency in Hz).
		"""
		times, freqs = self.get_pitch_curve(time_unit=time_unit)
		if ax is None:
			_, ax = plt.subplots(figsize=(10, 4))
		ax.plot(times, freqs, marker='o', linestyle='-', color='C0', alpha=0.8)
		ax.set_xlabel('Time')
		ax.set_ylabel('Frequency (Hz)')
		if title is None:
			meta = self.get_metadata()
			title = meta.get('title', 'Makam Pitch Curve')
		ax.set_title(title)
		ax.grid(True, linestyle='--', alpha=0.5)
		plt.tight_layout()
		plt.show()


def load_makam_notes(xml_path: str) -> Tuple[List[Tuple[float, float]], Dict]:
	"""Return list of (pitch_cents_relative_to_tonic, duration) tuples for melody shape comparison."""
	try:
		metadata, pitches, durations, tonic_pitch = parse_makam_xml(xml_path)
	except Exception:
		return [], {'parse_error': True}

	# Fallback: read makam/usul from filename if not found in XML credits
	if 'makam' not in metadata or 'usul' not in metadata:
		parts = Path(xml_path).stem.split('--')
		if 'makam' not in metadata and len(parts) > 0:
			metadata['makam'] = parts[0]
		if 'usul' not in metadata and len(parts) > 2:
			metadata['usul'] = parts[2]

	notes: List[Tuple[float, float]] = [
		((p - tonic_pitch) * 100.0, float(d))
		for p, d in zip(pitches, durations)
		if d > 0
	]
	return notes, metadata
