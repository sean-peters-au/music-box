"""
File: tine.py
Holds the Tine class which specifies the valid music-box notes (tines).
"""

class Tine:
    """
    Stores the valid note names for a music box and any related metadata.
    """

    def __init__(self):
        # Customize as needed
        self.notes = [
            "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5",
            "D5", "E5", "F5", "G5", "A5", "B5", "C6", "D6",
            "E6", "F6"
        ]

    @property
    def total_tines(self) -> int:
        return len(self.notes)