# Swaralipi

Swaralipi is a framework designed to represent Indic music—such as Hindustani, Carnatic, and Rabindrasangeet—using a Matrix Model. Unlike Western Staff notation, which uses a continuous linear system with bar lines, this framework organizes music into a 2D matrix for each line of a music piece. 

- The Row: Each line can have up to eight rows to accommodate different components like the primary melody, lyrics, beat markings and variations for repeated segments.
- The Column Model: The number of columns is determined by the Taala (cyclic beat pattern), the number of Bibhagas (measures), and the Avartana (number of cycles per line).

The paper highlights that Indic music is rich in ornaments that cannot be easily captured by Western notation software. The framework represents them using special symbols

1. Lack of Unicode Standardization: Most Indic music symbols (except for a few Bhatkhande symbols) have not yet been encoded in Unicode. This requires the use of non-Unicode fonts or a "mixed format," making the music sheets non-standard across different applications.
2. Architectural Complexity: Because Indic music depends on language scripts and lacks standard bar lines, the architecture used for Western music software cannot be used, necessitating this entirely new, complex matrix-based system.
3. Performance specific details are missing: The framework tells the computer "there is a glide here," but it does not specify the shape of that glide. In actual performance, an artist might slide linearly, exponentially, or with a slight oscillation. Because the data is stored as a symbol across cells, the precise "curve" is left to interpretation.

You can plot only a general melodic skeleton, without the fluid, continuous movement.


# Turkish Makams

SymbTr: A Turkish Makam Music Symbolic Representation Database has the representation of microtones and non-equal temperament in Turkish Makam music is achieved through a specialized system called 53TET (53-tone equal temperament) and the use of the Holdrian Comma


### The Intervallic Unit: The Holdrian Comma (Hc)

Because Turkish makam music uses a much finer pitch palette than Western music (17, 24, or more tones per octave), the framework uses the Holdrian Comma as the basic intervallic unit. 

- An octave is divided into 53 equal parts
- 1 Hc is approximately 22.5 cents ($1200 / 53$).
- The database adopts 53TET as the master underlying tuning because it accommodates both the 24-note Classical system (KTM) and the 17-note Folk system (THM) with deviations of less than 1 cent.


### Multi-Layered Symbolic Notation

To bridge the gap between theoretical scores and actual performance, SymbTr represents notes using several distinct fields:

- NoteAE / CommaAE (Theory): This field represents the note according to the Arel-Ezgi (AE) system, which is the official theoretical model for Turkish music. It uses scientific pitch notation plus an accidental (e.g., `B4b1` for a Segah note that is theoretically 1 comma flat).
- Note53 / Comma53 (Practice): This represents the note's value in the 53TET system as it is actually performed. The paper notes that theory and practice often differ; for example, a note written as 1 comma flat in theory might be performed 2 commas flat in practice. The `Comma53` field captures this specific frequency.
- Accidentals: The system uses a variety of symbols to represent microtonal shifts, including reverse and hooked flat signs (which lower notes by 1 and 4 commas, respectively) or numerical superscripts over standard accidental signs to indicate precise comma alterations.

###  Ornamentation

Ornamentation in Turkish music is often intrinsic to the melodic movement. SymbTr represents these symbolically using specific Codes:

- **#9:** A normal note.
- **#7, #8, #12, #23:** Codes for tremolos, acciaccatura, trills, and mordents.

In Turkish Folk Music (THM), where ornamentations are often written out as clusters of small rhythmic notes, the database simplifies these into a single core note while using the "Code" field to indicate the type of ornamentation performed.



