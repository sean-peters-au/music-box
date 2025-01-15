"""
File: main.py
Demonstrates usage of the Cassette and RodWithHandle classes.
"""

from cassette import Cassette
from spindle import Spindle

def main():
    cassette = Cassette()
    spindle = Spindle()
    
    cassette.export("stl/cassette.stl")
    spindle.export("stl/spindle.stl")
    
    cassette.simulate()

if __name__ == "__main__":
    main()