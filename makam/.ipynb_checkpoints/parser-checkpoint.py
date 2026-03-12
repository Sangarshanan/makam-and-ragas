from pathlib import Path
# Makam MusicXML parser for Turkish makam corpus
import xml.etree.ElementTree as ET

# Step to semitone mapping for Western pitch names
STEP_TO_SEMITONE = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

def parse_makam_xml(filepath):
	def find_makam_files_by_metadata(directory, makam_name=None, usul_name=None):
		"""
		Find Makam XML files in a directory filtered by makam and/or usul.
		Args:
			directory: Path to directory containing Makam XML files
			makam_name: (optional) Filter by makam name (case-insensitive, substring match)
			usul_name: (optional) Filter by usul name (case-insensitive, substring match)
		Returns:
			List of Path objects for matching XML files
		"""
		directory = Path(directory)
		xml_files = list(directory.glob("*.xml"))
		matches = []
		for xml_file in xml_files:
			try:
				meta, _, _, _ = parse_makam_xml(str(xml_file))
				makam_ok = True
				usul_ok = True
				if makam_name:
					makam_val = meta.get("makam", "").lower()
					makam_ok = makam_name.lower() in makam_val
				if usul_name:
					usul_val = meta.get("usul", "").lower()
					usul_ok = usul_name.lower() in usul_val
				if makam_ok and usul_ok:
					matches.append(xml_file)
			except Exception:
				continue
		return matches
	"""
	Parse a MusicXML (partwise) file from the Turkish Makam corpus.

	Returns:
		metadata: dict with title, makam, usul, composer
		pitches: list of absolute pitch values in semitones (with microtonal alter)
		durations: list of durations in divisions
		tonic_pitch: the karar (tonic) — last pitched note of the piece
	"""
	tree = ET.parse(filepath)
	root = tree.getroot()

	# --- Metadata ---
	metadata = {}
	title_el = root.find(".//work-title")
	metadata["title"] = title_el.text if title_el is not None else ""

	composer_el = root.find(".//creator[@type='composer']")
	metadata["composer"] = composer_el.text if composer_el is not None else ""

	# Extract makam and usul from credits
	for credit in root.findall(".//credit-words"):
		text = (credit.text or "").strip()
		if "Makam:" in text:
			metadata["makam"] = text.replace("Makam:", "").strip()
		elif "Usul:" in text:
			metadata["usul"] = text.replace("Usul:", "").strip()

	# --- Parse notes ---
	pitches = []
	durations = []
	divisions = 192  # default, updated from attributes

	for measure in root.findall(".//part/measure"):
		# Update divisions if present
		div_el = measure.find("attributes/divisions")
		if div_el is not None:
			divisions = int(div_el.text)

		for note in measure.findall("note"):
			# Skip rests
			if note.find("rest") is not None:
				continue

			# Skip tied notes (tie type="stop" means this is a continuation)
			tie = note.find("tie")
			if tie is not None and tie.get("type") == "stop":
				ties = note.findall("tie")
				types = [t.get("type") for t in ties]
				if "start" not in types:
					continue  # pure stop = continuation only
				continue

			# Extract pitch
			pitch_el = note.find("pitch")
			if pitch_el is None:
				continue

			step = pitch_el.find("step").text
			octave = int(pitch_el.find("octave").text)
			alter_el = pitch_el.find("alter")
			alter = float(alter_el.text) if alter_el is not None else 0.0

			# Convert to absolute semitone value (MIDI-like)
			abs_pitch = (octave + 1) * 12 + STEP_TO_SEMITONE[step] + alter
			pitches.append(abs_pitch)

			dur_el = note.find("duration")
			dur = int(dur_el.text) if dur_el is not None else 0
			durations.append(dur)

	# Tonic = last pitched note (karar in Turkish makam)
	tonic_pitch = pitches[-1] if pitches else 60
	metadata["tonic_pitch"] = tonic_pitch

	return metadata, pitches, durations, tonic_pitch
