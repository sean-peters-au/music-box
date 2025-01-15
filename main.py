"""
File: main.py
CLI interface for generating music box parts from MP3 files.
"""

import click
from cassette import Cassette
from spindle import Spindle
from pathlib import Path

@click.command()
@click.argument('mp3_path', type=click.Path(exists=True))
@click.option('--output-dir', '-o', default='stl',
              help='Output directory for STL files (default: stl/)')
def main(mp3_path: str, output_dir: str):
    """
    Generate music box parts from an MP3 file.
    
    MP3_PATH: Path to the input MP3 file containing the tune
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Generate the parts
    cassette = Cassette(mp3_path=mp3_path)
    spindle = Spindle()
    
    # Export STLs
    cassette.export(f"{output_dir}/cassette.stl")
    spindle.export(f"{output_dir}/spindle.stl")
    
    # Optional simulation
    cassette.simulate()

if __name__ == "__main__":
    main()