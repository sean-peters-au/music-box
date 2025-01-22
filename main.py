"""
File: main.py
CLI interface for generating music box parts from MP3 files or text descriptions.
"""

import click
from pathlib import Path
from note_extractor import extract_notes_from_mp3
from note_player import simulate_notes
from cassette import CassetteCAD
from spindle import SpindleCAD
from mechanism import ROTATION_TIME
from ai_note_builder import get_notes_from_text

@click.command()
@click.option('--input-file', '-i', type=click.Path(exists=True),
              help='Input MP3 file to extract notes from')
@click.option('--input-text', '-t', type=str,
              help='Name or description of the song to generate notes for')
@click.option('--output-dir', '-o', default='stl',
              help='Output directory for STL files (default: stl/)')
@click.option('--simulate/--no-simulate', default=True,
              help='Whether to simulate playing the tune.')
@click.option('--squeeze-time', '-t', type=float,
              help=f'Extract this many seconds from the MP3 and squeeze into cassette rotation time')
def main(input_file: str, input_text: str, output_dir: str, simulate: bool, squeeze_time: float):
    """
    Generate music box parts from either an MP3 file or a text description.
    """
    if not input_file and not input_text:
        raise click.UsageError("Must specify either --input-file or --input-text")
    if input_file and input_text:
        raise click.UsageError("Cannot specify both --input-file and --input-text")

    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Get notes either from MP3 or AI
    if input_file:
        note_events = extract_notes_from_mp3(
            input_file, 
            max_time=squeeze_time if squeeze_time else ROTATION_TIME,
            squeeze_to_duration=ROTATION_TIME if squeeze_time else None
        )
    else:
        note_events = get_notes_from_text(input_text, ROTATION_TIME)

    # Build cassette geometry
    cassette_cad = CassetteCAD(note_events=note_events, rotation_duration=ROTATION_TIME)
    cassette_cad.export(str(output_path / "cassette.stl"))

    # Build spindle
    spindle_cad = SpindleCAD()
    spindle_cad.export(str(output_path / "spindle.stl"))

    # Optional real-time playback simulation
    if simulate and note_events:
        print("\nSimulating cassette playback...")
        simulate_notes(note_events, total_duration=ROTATION_TIME)

if __name__ == "__main__":
    main()