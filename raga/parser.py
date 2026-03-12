"""
Swarlipi Extractor - Python methods for extracting data from Swarlipi XML files.
"""

import re
import csv
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Union
import xml.etree.ElementTree as ET


# Note ASCII code points used in Bhatkhande notation
NOTE_CODES = {
    's': 115,   # Sa
    'R': 82,    # Re komal
    'r': 114,   # Re shuddha
    'G': 71,    # Ga komal
    'g': 103,   # Ga shuddha
    'm': 109,   # Ma shuddha
    'M': 77,    # Ma teevra
    'p': 112,   # Pa
    'D': 68,    # Dha komal
    'd': 100,   # Dha shuddha
    'N': 78,    # Ni komal
    'n': 110,   # Ni shuddha
}

# Reverse mapping: code point to note name
CODE_TO_NOTE = {v: k for k, v in NOTE_CODES.items()}

# Ordered list of note codes (matching XQuery order)
NOTE_CODE_ORDER = [115, 82, 114, 71, 103, 109, 77, 112, 68, 100, 78, 110]
NOTE_NAMES_ORDER = ['s', 'R', 'r', 'G', 'g', 'm', 'M', 'p', 'D', 'd', 'N', 'n']

# Ornamentation symbols used in Ome Bhatkhande Hindi notation
# Reference: https://omenad.github.io/fonts/ome-bhatkhande-hindi/
#
# Meend (glide/portamento) symbols - used as a set:
#   q = Meend Start, w = Meend Continue, W = Meend Stroke, e = Meend End
#   Q = Ghaseet Start, E = Ghaseet End
#   Example: qswrwgem = meend from Sa through Re, Ga to Ma
#
# Other ornaments:
#   ( ) = Murki (quick movement to adjacent notes and back)
#   <sup>...</sup> = Kan (grace note) / Krintan (repeated kan)
#
# Chhand (tempo/laya groupings - notes per beat):
#   @ = Dugun (2), # = Tigun (3), $ = Chaugun (4)
#   % = Pachgun (5), ^ = Chhatgun (6), & = Satgun (7), * = Athgun (8)
#   ` = Lower Chaugun (4), ! = Lower Chhatgun (6), ~ = Lower Athgun (8)

# Meend symbols (glide between notes)
MEEND_SYMBOLS = {
    'q': 'meend_start',      # Start of meend
    'Q': 'ghaseet_start',    # Start of ghaseet (reverse meend)
    'w': 'meend_continue',   # Middle notes in meend
    'W': 'meend_stroke',     # Stroke needed to continue meend
    'e': 'meend_end',        # End of meend
    'E': 'ghaseet_end',      # End of ghaseet
}

# Murki symbols
MURKI_SYMBOLS = {
    '(': 'murki_start',      # Start of murki
    ')': 'murki_end',        # End of murki
}

# Chhand symbols (laya/tempo groupings - number of notes per beat)
CHHAND_SYMBOLS = {
    '@': 'dugun',            # 2 notes per beat
    '#': 'tigun',            # 3 notes per beat
    '$': 'chaugun',          # 4 notes per beat
    '%': 'pachgun',          # 5 notes per beat
    '^': 'chhatgun',         # 6 notes per beat
    '&': 'satgun',           # 7 notes per beat
    '*': 'athgun',           # 8 notes per beat
    '`': 'lower_chaugun',    # Lower Chaugun (4) - for larger groupings
    '!': 'lower_chhatgun',   # Lower Chhatgun (6) - for larger groupings
    '~': 'lower_athgun',     # Lower Athgun (8) - for larger groupings
}

# Structural/notation symbols
NOTATION_SYMBOLS = {
    '_': 'long_dash',        # Sustained note / hold
    '-': 'khali',            # Rest / empty beat
    'a': 'beat_divider',     # Divides beats
    'A': 'phase_divider',    # Divides phrases
    'x': 'sam',              # First beat (sam)
    '+': 'plus',             # Plus sign
    ',': 'comma',            # Comma
}

# Combined mappings
ORNAMENT_SYMBOLS = {**MEEND_SYMBOLS, **MURKI_SYMBOLS}
LAYA_SYMBOLS = CHHAND_SYMBOLS  # Alias for clarity
ALL_SYMBOLS = {**MEEND_SYMBOLS, **MURKI_SYMBOLS, **CHHAND_SYMBOLS, **NOTATION_SYMBOLS}

# Reverse mapping
ORNAMENT_NAMES = {v: k for k, v in ALL_SYMBOLS.items()}


class SwarlipiExtractor:
    """
    Extractor for Swarlipi XML files containing Indian classical music notations.
    
    Provides methods to:
    - Find compositions with specific arohana patterns
    - Calculate note frequency distributions
    - Find compositions containing specific ornaments (like meend)
    - Export frequency distributions to CSV
    """
    
    def __init__(self, dataset_path: str):
        """
        Initialize the extractor with a path to the dataset directory.
        
        Args:
            dataset_path: Path to directory containing Swarlipi XML files
        """
        self.dataset_path = Path(dataset_path)
        self._xml_files = None
    
    @property
    def xml_files(self) -> List[Path]:
        """Lazily load and cache list of XML files in the dataset."""
        if self._xml_files is None:
            self._xml_files = list(self.dataset_path.glob("*.xml"))
        return self._xml_files
    
    def _parse_xml(self, file_path: Path) -> Optional[ET.Element]:
        """
        Parse an XML file and return its root element.
        
        Args:
            file_path: Path to the XML file
            
        Returns:
            Root element of the XML tree, or None if parsing fails
        """
        try:
            tree = ET.parse(file_path)
            return tree.getroot()
        except ET.ParseError as e:
            print(f"Error parsing {file_path}: {e}")
            return None
    
    def _get_title(self, root: ET.Element) -> str:
        """Extract the title from a swarlipi XML element."""
        title_elem = root.find(".//INFO/TITLE")
        return title_elem.text if title_elem is not None and title_elem.text else ""
    
    def _get_raag_name(self, root: ET.Element) -> str:
        """Extract the raag name from a swarlipi XML element."""
        raag_elem = root.find(".//RAAG/RAAG_NAME")
        return raag_elem.text if raag_elem is not None and raag_elem.text else ""
    
    def _get_arohana(self, root: ET.Element) -> str:
        """Extract the arohana from a swarlipi XML element."""
        arohana_elem = root.find(".//RAAG/AROHANA")
        return arohana_elem.text if arohana_elem is not None and arohana_elem.text else ""
    
    def _get_sheet_contents(self, root: ET.Element) -> str:
        """
        Extract all sheet contents (notes) from a swarlipi XML element.
        
        Args:
            root: Root element of the swarlipi XML
            
        Returns:
            Concatenated string of all note contents, cleaned of markup
        """
        contents = []
        for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
            if content_elem.text:
                contents.append(content_elem.text)
        
        # Join all contents
        joined_str = ''.join(contents)
        
        # Clean up: remove markup tags and special characters
        # Pattern matches: <sup>, </sup>, @, u, l, ), (, -, comma, whitespace
        cleaned = re.sub(r'<sup>|</sup>|@|u|l|\)|\(|-|,|\s+', '', joined_str)
        
        return cleaned
    
    def _count_notes(self, content: str) -> Dict[str, int]:
        """
        Count occurrences of each note in the content string.
        
        Args:
            content: Cleaned string of note characters
            
        Returns:
            Dictionary mapping note names to their counts
        """
        counts = {}
        code_points = [ord(c) for c in content]
        
        for note_code in NOTE_CODE_ORDER:
            count = code_points.count(note_code)
            note_name = CODE_TO_NOTE[note_code]
            counts[note_name] = count
        
        return counts
    
    def _get_note_frequency_list(self, content: str) -> List[int]:
        """
        Get note frequencies as an ordered list (matching XQuery output order).
        
        Args:
            content: Cleaned string of note characters
            
        Returns:
            List of counts in the order: s, R, r, G, g, m, M, p, D, d, N, n
        """
        code_points = [ord(c) for c in content]
        return [code_points.count(note_code) for note_code in NOTE_CODE_ORDER]

    # =========================================================================
    # XQuery equivalent methods
    # =========================================================================
    
    def find_compositions_by_arohana(self, arohana_pattern: str) -> List[str]:
        """
        Find compositions containing a specific arohana pattern.
        
        Equivalent to arohana.xq:
        ```xquery
        for $songs in collection ("Bhatkhande-Database")//swarlipi
        let $title := $songs/INFO/TITLE/text()
        let $arohana := $songs/RAAG/AROHANA/text()
        return if (contains($arohana, "s-R-g")) then $title
        ```
        
        Args:
            arohana_pattern: Pattern to search for (e.g., "s-R-g")
            
        Returns:
            List of composition titles containing the pattern
        """
        matching_titles = []
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            arohana = self._get_arohana(root)
            if arohana_pattern in arohana:
                title = self._get_title(root)
                if title:
                    matching_titles.append(title)
        
        return matching_titles
    
    def get_note_frequency_distribution(self) -> List[Dict[str, Union[str, List[int]]]]:
        """
        Get note frequency distribution for each composition.
        
        Equivalent to freq-dist-notes.xq:
        ```xquery
        for $song in collection("Bhatkhande-Database")//swarlipi
        let $raag := $song/RAAG/RAAG_NAME/text()
        let $contents := $song/SHEET/LINES/LINE/ROW/COL/CONTENT/text()
        ...
        return $result
        ```
        
        Returns:
            List of dictionaries with 'title', 'raag', 'frequencies', and 'note_counts'
        """
        results = []
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            title = self._get_title(root)
            raag = self._get_raag_name(root)
            content = self._get_sheet_contents(root)
            frequencies = self._get_note_frequency_list(content)
            note_counts = self._count_notes(content)
            
            results.append({
                'title': title,
                'file': xml_file.name,
                'raag': raag,
                'frequencies': frequencies,
                'note_counts': note_counts
            })
        
        return results
    
    def export_frequency_distribution_to_csv(self, output_path: str) -> None:
        """
        Export note frequency distribution with raag to CSV file.
        
        Equivalent to fre-dist-raag-to-csv.xq:
        ```xquery
        file:write("D:/result.csv",
        for $song in collection("Bhatkhande-Database")//swarlipi
        ...
        let $result := concat($result, ",", $raag, "&#10;")
        return $result
        )
        ```
        
        Args:
            output_path: Path to output CSV file
        """
        results = self.get_note_frequency_distribution()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            # Header: note names + raag
            header = NOTE_NAMES_ORDER + ['raag']
            writer = csv.writer(csvfile)
            writer.writerow(header)
            
            for result in results:
                row = result['frequencies'] + [result['raag']]
                writer.writerow(row)
        
        print(f"Exported frequency distribution to {output_path}")
    
    def find_compositions_with_meend(self) -> List[str]:
        """
        Find compositions containing meend (glide/portamento) notation.
        
        Equivalent to meend.xq - searches for 'q' (meend start character).
        
        In Ome Swarlipi, meend is notated as a sequence:
        q (start) + note + [w (continue) + note]* + e (end) + note
        
        Returns:
            List of composition titles containing meend
        """
        matching_titles = []
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            contents = []
            for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
                if content_elem.text:
                    contents.append(content_elem.text)
            
            joined_content = ''.join(contents)
            
            # Search for meend start symbol 'q'
            if 'q' in joined_content:
                title = self._get_title(root)
                if title:
                    matching_titles.append(title)
        
        return matching_titles
    
    def find_compositions_with_gamak(self) -> List[str]:
        """
        Find compositions containing gamak (vibration) notation.
        
        In Ome Swarlipi, gamak is notated with 'v' after a note.
        
        Returns:
            List of composition titles containing gamak
        """
        return self._find_compositions_with_symbol('v')
    
    def find_compositions_with_murki(self) -> List[str]:
        """
        Find compositions containing murki notation.
        
        In Ome Swarlipi, murki is notated with parentheses around a note: (p)
        
        Returns:
            List of composition titles containing murki
        """
        return self._find_compositions_with_symbol('(')
    
    def _find_compositions_with_symbol(self, symbol: str) -> List[str]:
        """Helper to find compositions containing a specific symbol."""
        matching_titles = []
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            contents = []
            for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
                if content_elem.text:
                    contents.append(content_elem.text)
            
            joined_content = ''.join(contents)
            
            if symbol in joined_content:
                title = self._get_title(root)
                if title:
                    matching_titles.append(title)
        
        return matching_titles
    
    def find_compositions_with_ornament(self, ornament_name: str) -> List[str]:
        """
        Find compositions containing a specific ornamentation.
        
        Available ornaments (from Ome Swarlipi spec):
            - 'meend': Glide/portamento (symbols: q, w, W, e)
            - 'gamak': Quick vibration (symbol: v)
            - 'murki': Quick movement to adjacent notes (symbols: ( ))
        
        Dataset-specific symbols (unverified):
            - 'unknown_at': @ symbol (980 occurrences)
            - 'long_dash': _ sustained note
            - 'iteration': # marker
        
        Args:
            ornament_name: Name of the ornament to search for
            
        Returns:
            List of composition titles containing the ornament
        """
        # Handle meend specially - search for start symbol
        if ornament_name in ('meend', 'meend_start'):
            return self.find_compositions_with_meend()
        
        if ornament_name == 'gamak':
            return self.find_compositions_with_gamak()
        
        if ornament_name in ('murki', 'murki_start'):
            return self.find_compositions_with_murki()
        
        # Look up in all symbol mappings
        if ornament_name not in ORNAMENT_NAMES:
            raise ValueError(f"Unknown ornament: {ornament_name}. "
                           f"Available: {list(ORNAMENT_NAMES.keys())}")
        
        symbol = ORNAMENT_NAMES[ornament_name]
        return self._find_compositions_with_symbol(symbol)
    
    def find_compositions_with_laya(self, laya_name: str) -> List[str]:
        """
        Find compositions containing a specific laya/tempo grouping.
        
        Available laya types (Chhand):
            - 'dugun': 2 notes per beat (@)
            - 'tigun': 3 notes per beat (#)
            - 'chaugun': 4 notes per beat ($)
            - 'pachgun': 5 notes per beat (%)
            - 'chhatgun': 6 notes per beat (^)
            - 'satgun': 7 notes per beat (&)
            - 'athgun': 8 notes per beat (*)
            - 'lower_chaugun': Lower 4-grouping (`)
            - 'lower_chhatgun': Lower 6-grouping (!)
            - 'lower_athgun': Lower 8-grouping (~)
        
        Args:
            laya_name: Name of the laya type
            
        Returns:
            List of composition titles using that laya
        """
        if laya_name not in [v for v in CHHAND_SYMBOLS.values()]:
            raise ValueError(f"Unknown laya: {laya_name}. "
                           f"Available: {list(CHHAND_SYMBOLS.values())}")
        
        symbol = ORNAMENT_NAMES[laya_name]
        return self._find_compositions_with_symbol(symbol)
    
    def get_laya_statistics(self) -> Dict[str, Dict[str, Union[int, List[str]]]]:
        """
        Get statistics about laya/tempo usage across the dataset.
        
        Returns:
            Dictionary mapping laya names to their stats
        """
        stats = {name: {'count': 0, 'compositions': []} 
                 for name in CHHAND_SYMBOLS.values()}
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            title = self._get_title(root)
            contents = []
            for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
                if content_elem.text:
                    contents.append(content_elem.text)
            
            joined_content = ''.join(contents)
            
            for symbol, laya_name in CHHAND_SYMBOLS.items():
                count = joined_content.count(symbol)
                if count > 0:
                    stats[laya_name]['count'] += count
                    if title:
                        stats[laya_name]['compositions'].append(title)
        
        return stats
        
        return matching_titles
    
    def get_ornament_statistics(self) -> Dict[str, Dict[str, Union[int, List[str]]]]:
        """
        Get statistics about ornamentations (meend, murki) across the dataset.
        
        For laya/tempo statistics, use get_laya_statistics() instead.
        
        Returns:
            Dictionary mapping ornament names to their stats
        """
        # Only count actual ornaments (meend, murki), not chhand/laya
        ornament_only = {**MEEND_SYMBOLS, **MURKI_SYMBOLS}
        stats = {name: {'count': 0, 'compositions': []} 
                 for name in ornament_only.values()}
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            title = self._get_title(root)
            contents = []
            for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
                if content_elem.text:
                    contents.append(content_elem.text)
            
            joined_content = ''.join(contents)
            
            for symbol, ornament_name in ornament_only.items():
                count = joined_content.count(symbol)
                if count > 0:
                    stats[ornament_name]['count'] += count
                    if title:
                        stats[ornament_name]['compositions'].append(title)
        
        return stats
    
    def get_composition_ornaments(self, file_name: str) -> Dict[str, int]:
        """
        Get ornament counts for a specific composition.
        
        Args:
            file_name: Name of the XML file
            
        Returns:
            Dictionary mapping symbol names to their occurrence counts
        """
        file_path = self.dataset_path / file_name
        if not file_path.exists():
            return {}
        
        root = self._parse_xml(file_path)
        if root is None:
            return {}
        
        contents = []
        for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
            if content_elem.text:
                contents.append(content_elem.text)
        
        joined_content = ''.join(contents)
        
        ornament_counts = {}
        for symbol, ornament_name in ALL_SYMBOLS.items():
            count = joined_content.count(symbol)
            if count > 0:
                ornament_counts[ornament_name] = count
        
        return ornament_counts
    
    def get_all_ornament_data(self) -> List[Dict]:
        """
        Get ornamentation data for all compositions.
        
        Returns:
            List of dictionaries with composition info and ornament counts
        """
        results = []
        
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            title = self._get_title(root)
            raag = self._get_raag_name(root)
            
            contents = []
            for content_elem in root.findall(".//SHEET/LINES/LINE/ROW/COL/CONTENT"):
                if content_elem.text:
                    contents.append(content_elem.text)
            
            joined_content = ''.join(contents)
            
            ornament_counts = {}
            for symbol, ornament_name in ALL_SYMBOLS.items():
                ornament_counts[ornament_name] = joined_content.count(symbol)
            
            results.append({
                'title': title,
                'file': xml_file.name,
                'raag': raag,
                'ornaments': ornament_counts,
                'total_ornaments': sum(ornament_counts.values())
            })
        
        return results
    
    def export_ornaments_to_csv(self, output_path: str) -> None:
        """
        Export ornamentation data to CSV file.
        
        Args:
            output_path: Path to output CSV file
        """
        results = self.get_all_ornament_data()
        
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            ornament_names = list(ALL_SYMBOLS.values())
            header = ['title', 'file', 'raag'] + ornament_names + ['total']
            writer = csv.writer(csvfile)
            writer.writerow(header)
            
            for result in results:
                row = [result['title'], result['file'], result['raag']]
                row += [result['ornaments'][name] for name in ornament_names]
                row.append(result['total_ornaments'])
                writer.writerow(row)
        
        print(f"Exported ornament data to {output_path}")

    # =========================================================================
    # Additional utility methods
    # =========================================================================
    
    def get_all_raags(self) -> List[str]:
        """Get list of all unique raags in the dataset."""
        raags = set()
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is not None:
                raag = self._get_raag_name(root)
                if raag:
                    raags.add(raag)
        return sorted(list(raags))
    
    def get_compositions_by_raag(self, raag_name: str) -> List[Dict]:
        """
        Get all compositions of a specific raag.
        
        Args:
            raag_name: Name of the raag to filter by
            
        Returns:
            List of dictionaries with composition details
        """
        compositions = []
        for xml_file in self.xml_files:
            root = self._parse_xml(xml_file)
            if root is None:
                continue
            
            raag = self._get_raag_name(root)
            if raag.lower() == raag_name.lower():
                compositions.append({
                    'title': self._get_title(root),
                    'file': xml_file.name,
                    'arohana': self._get_arohana(root),
                    'raag': raag
                })
        
        return compositions
    
    def get_composition_details(self, file_name: str) -> Optional[Dict]:
        """
        Get detailed information about a specific composition.
        
        Args:
            file_name: Name of the XML file
            
        Returns:
            Dictionary with composition details, or None if not found
        """
        file_path = self.dataset_path / file_name
        if not file_path.exists():
            return None
        
        root = self._parse_xml(file_path)
        if root is None:
            return None
        
        # Extract INFO
        info = {}
        for elem in root.findall(".//INFO/*"):
            info[elem.tag.lower()] = elem.text
        
        # Extract TAAL
        taal = {}
        for elem in root.findall(".//TAAL/*"):
            taal[elem.tag.lower()] = elem.text
        
        # Extract RAAG
        raag = {}
        for elem in root.findall(".//RAAG/*"):
            raag[elem.tag.lower()] = elem.text
        
        # Get note frequencies
        content = self._get_sheet_contents(root)
        
        return {
            'info': info,
            'taal': taal,
            'raag': raag,
            'note_frequencies': self._count_notes(content),
            'total_notes': len(content)
        }


# Convenience functions for direct use
def find_by_arohana(dataset_path: str, pattern: str) -> List[str]:
    """Find compositions by arohana pattern."""
    extractor = SwarlipiExtractor(dataset_path)
    return extractor.find_compositions_by_arohana(pattern)


def get_frequency_distribution(dataset_path: str) -> List[Dict]:
    """Get note frequency distribution for all compositions."""
    extractor = SwarlipiExtractor(dataset_path)
    return extractor.get_note_frequency_distribution()


def export_to_csv(dataset_path: str, output_path: str) -> None:
    """Export frequency distribution to CSV."""
    extractor = SwarlipiExtractor(dataset_path)
    extractor.export_frequency_distribution_to_csv(output_path)


def find_meend_compositions(dataset_path: str) -> List[str]:
    """Find compositions containing meend ornaments."""
    extractor = SwarlipiExtractor(dataset_path)
    return extractor.find_compositions_with_meend()


def find_compositions_with_ornament(dataset_path: str, ornament_name: str) -> List[str]:
    """Find compositions containing a specific ornament."""
    extractor = SwarlipiExtractor(dataset_path)
    return extractor.find_compositions_with_ornament(ornament_name)


def get_ornament_statistics(dataset_path: str) -> Dict:
    """Get ornamentation statistics for the entire dataset."""
    extractor = SwarlipiExtractor(dataset_path)
    return extractor.get_ornament_statistics()


def export_ornaments_to_csv(dataset_path: str, output_path: str) -> None:
    """Export ornamentation data to CSV."""
    extractor = SwarlipiExtractor(dataset_path)
    extractor.export_ornaments_to_csv(output_path)
