"""
File: cassette.py
Generates a 3D cassette wheel for a music box, driven by a specified MP3 track.
"""

import math
import time
import os
import sys
from contextlib import contextmanager

import aubio
import cadquery as cq
import numpy as np
from pydub import AudioSegment
from pydub.playback import play
from scipy.signal import butter, filtfilt

class Cassette:
    """
    Builds a music box cassette wheel using CadQuery, placing pins based on
    note/timing data extracted from an MP3 file.

    Public Methods:
        __init__(mp3_path: str): Initializes the Cassette object, reads/clamps
                                 the first 20s of mp3_path, converts to note
                                 events, and builds the geometry.
        export(filename: str): Exports the cassette as an STL file.
        simulate(): Simulates the music box by playing the cassette (placeholder).
    """

    @staticmethod
    def note_to_freq(note_name):
        """Convert note name (e.g. 'A4') to frequency in Hz"""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = int(note_name[-1])
        note = note_name[:-1]
        semitone = note_names.index(note)
        return 440 * 2**((octave - 4) + (semitone - 9) / 12)

    @staticmethod
    def generate_tone(freq, duration_ms=100):
        """
        Generate a music box-like tone with harmonics and envelope shaping.
        Music box tines produce rich harmonics and have a characteristic 'ping' sound.
        """
        sample_rate = 44100
        num_samples = int(sample_rate * duration_ms / 1000)
        t = np.arange(num_samples) / sample_rate
        
        # Create a tone with harmonics typical of a metal tine
        # Fundamental frequency (1x) and overtones (2x, 3x, 4x, etc.)
        harmonics = [
            (1.0, 1.00),    # fundamental
            (2.0, 0.50),    # octave
            (3.0, 0.25),    # octave + fifth
            (4.0, 0.15),    # second octave
            (5.0, 0.10),    # third + major third
        ]
        
        samples = sum(
            amp * np.sin(2 * np.pi * freq * n * t)
            for n, amp in harmonics
        )
        
        # Shape the envelope to sound like a plucked tine
        attack_ms = 5   # Very quick attack
        decay_ms = 60   # Longer decay
        sustain_level = 0.3
        
        attack_samples = int(sample_rate * attack_ms / 1000)
        decay_samples = int(sample_rate * decay_ms / 1000)
        
        envelope = np.ones(num_samples) * sustain_level
        envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        envelope[attack_samples:attack_samples + decay_samples] = np.linspace(
            1, sustain_level, decay_samples
        )
        
        # Apply envelope
        samples = samples * envelope
        
        # Normalize and convert to 16-bit integer
        samples = samples / np.max(np.abs(samples))
        samples = (samples * 32767).astype(np.int16)
        
        return AudioSegment(
            samples.tobytes(), 
            frame_rate=sample_rate,
            sample_width=2,
            channels=1
        )

    @staticmethod
    def freq_to_note_name(freq):
        """Approximate freq -> note name (A4=440) with chromatic scale."""
        if freq <= 0:
            return None
        
        # MIDI note calculation
        midi_num = 69 + 12 * math.log2(freq / 440.0)
        # Round to nearest integer
        midi_rounded = int(round(midi_num))
        
        # Map that MIDI number to a note name (simple octave logic)
        note_names = ["C", "C#", "D", "D#", "E", "F", 
                    "F#", "G", "G#", "A", "A#", "B"]
        #  MIDI=60 -> C4, so note = note_names[ 60 % 12 ] + str( 60//12 - 1 )
        
        name = note_names[midi_rounded % 12]
        octave = midi_rounded // 12 - 1
        return f"{name}{octave}"

    def __init__(self, mp3_path: str):
        """
        Args:
            mp3_path (str): Path to the MP3 file to parse. Only the first 20s
                            are used for pin placement.
        """
        
        # Core cassette dimensions
        self.cassette_rotation_seconds = 20.0
        self.cassette_diameter = 13.0
        self.cassette_radius = self.cassette_diameter / 2.0
        self.cassette_total_height = 17.5
        self.cassette_wall_thickness = 4.0

        # Pin and tine constants
        self.tine_notes = [
            "C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5", 
            "D5", "E5", "F5", "G5", "A5", "B5", "C6", "D6", 
            "E6", "F6"
        ]
        self.total_tines = len(self.tine_notes)
        self.total_tine_width = 16.0
        self.tine_width = self.total_tine_width / self.total_tines
        self.pin_radial_bump = 0.5
        self.pin_width = self.tine_width / 2
        self.pin_height = self.tine_width / 2
        self.pin_vertical_offset = 1.0
        self.arc_safety_factor = 1.2
        self.min_note_angle_spacing = math.degrees(
            (self.pin_width * self.arc_safety_factor) / self.cassette_radius
        )
        
        # Base ring
        self.base_ring_height = 1.8
        self.base_ring_od = 15.0
        self.base_ring_id = 5.0

        # Top assembly dimensions
        self.lower_circle_height = 1.0
        self.lower_circle_diam = 16.0
        self.big_cog_height = 1.8
        self.small_cog_height = 1.5
        self.top_circle_height = 1.2

        self.big_cog_base_diam = 17.0
        self.big_cog_teeth_diam = 20.0
        self.num_teeth_big = 46
        
        self.small_cog_base_diam = 5.0
        self.small_cog_teeth_diam = 8.0
        self.num_teeth_small = 12
        
        self.top_circle_diam = 3.0

        # Build the cassette
        # 1) Extract note events from the MP3 (placeholder).
        # 2) Generate pins from those notes.
        # 3) Build the geometry.
        self._validate_mp3_path(mp3_path)
        self._note_events = self._extract_notes_from_mp3(mp3_path, max_time=self.cassette_rotation_seconds)
        self._pins = self._generate_pins_from_notes()
        self._assembly = self._build_cassette()
    
    def export(self, filename: str):
        """
        Exports the cassette as an STL file with the specified filename.
        
        Args:
            filename (str): Output STL filename.
        """
        self._assembly.val().exportStl(filename, tolerance=0.01)
        print(f"Exported '{filename}'")

    def simulate(self):
        """
        Simulates the music box by playing notes in real time.
        """
        if not self._note_events:
            print("No notes detected to simulate.")
            return

        # Create tones using class methods
        tones = {
            note: self.generate_tone(self.note_to_freq(note))
            for note in self.tine_notes
        }

        # Completely suppress all output during playback
        import os, sys, contextlib
        with contextlib.redirect_stdout(open(os.devnull, 'w')), \
             contextlib.redirect_stderr(open(os.devnull, 'w')):
            
            start_time = time.time()
            idx = 0
            n = len(self._note_events)

            print("\nSimulating cassette...")
            print("Detected notes:")
            for time_sec, note in self._note_events:
                print(f"  {time_sec:.2f}s: {note}")
            print("\nPlaying...")

            while idx < n:
                elapsed = time.time() - start_time
                note_time, note_name = self._note_events[idx]
                
                if elapsed >= note_time:
                    print(f"♪ {note_name}")
                    play(tones[note_name])
                    idx += 1
                else:
                    time.sleep(0.01)

                if elapsed > self.cassette_rotation_seconds:
                    break

            print("\nSimulation complete.")

    def _build_cassette(self) -> cq.Workplane:
        """
        Assemble all parts of the cassette (base ring, main body, pins, top cogs).
        """
        base_ring = self._make_base_ring()
        cassette_body = self._make_cassette_body()
        # pins were built from note data:
        wheel_with_pins_and_base = cassette_body.union(self._pins).union(base_ring)
        top_assembly = self._make_top_assembly()
        return wheel_with_pins_and_base.union(top_assembly)

    def _validate_mp3_path(self, path: str):
        """
        Simple validation for the provided MP3 path.
        """
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Could not find MP3 file at: {path}")

    def _extract_notes_from_mp3(self, mp3_path: str, max_time: float = 20.0):
        """
        Enhanced note detection with better handling of complex audio.
        """
        print(f"\nAnalyzing MP3: {mp3_path}")
        
        # 1) Load/convert MP3, clamp to max_time
        audio = AudioSegment.from_mp3(mp3_path)
        audio = audio[: int(max_time * 1000)]
        
        # Debug the audio file
        print(f"Audio length: {len(audio)/1000:.1f}s")
        print(f"Sample rate: {audio.frame_rate}Hz")
        print(f"Channels: {audio.channels}")
        print(f"Frame width: {audio.frame_width} bytes")
        print(f"Max amplitude: {audio.max}")
        print(f"dBFS: {audio.dBFS}")
        
        # Convert to mono if needed
        if audio.channels > 1:
            audio = audio.set_channels(1)
            print("Converted to mono")

        # Convert to 16-bit PCM, get raw data & sample rate
        audio = audio.set_sample_width(2)  # 16-bit
        sr = audio.frame_rate
        raw_data = np.frombuffer(audio._data, dtype=np.int16).astype(float)

        # Normalize and apply pre-filtering
        raw_data = raw_data / np.max(np.abs(raw_data))
        
        # Apply bandpass filter to focus on musical range
        nyquist = sr / 2
        low_cut = 60   # Hz - just below lowest note we care about
        high_cut = 2000  # Hz - above highest fundamental we care about
        b, a = butter(4, [low_cut/nyquist, high_cut/nyquist], btype='band')
        raw_data = filtfilt(b, a, raw_data)

        # Setup pitch detection with better parameters
        hop_size = 512
        frame_size = 512  # Must match hop_size for aubio
        
        # Use multiple pitch detectors and combine results
        pitch_yinfft = aubio.pitch("yinfft", frame_size, hop_size, sr)
        pitch_yin = aubio.pitch("yin", frame_size, hop_size, sr)
        pitch_yinfft.set_unit("Hz")
        pitch_yin.set_unit("Hz")
        pitch_yinfft.set_silence(-60)
        pitch_yin.set_silence(-60)
        
        # Setup onset detection
        onset_detector = aubio.onset("complex", frame_size, hop_size, sr)
        onset_detector.set_threshold(0.3)

        note_events = []
        last_note_times = {}
        min_time_between_notes = (self.min_note_angle_spacing / 360.0) * self.cassette_rotation_seconds
        
        # Keep track of pitch history for stability
        pitch_history = []
        history_size = 3
        
        for start_idx in range(0, len(raw_data) - frame_size, hop_size):
            frame = raw_data[start_idx : start_idx + frame_size]
            frame_float = frame.astype(np.float32)
            
            frame_time = start_idx / sr
            if frame_time > max_time:
                break
            
            # Get pitch estimates from both detectors
            pitch1 = pitch_yinfft(frame_float)[0]
            pitch2 = pitch_yin(frame_float)[0]
            is_onset = onset_detector(frame_float)[0]
            
            # Average the two pitch estimates if they're close
            if abs(pitch1 - pitch2) < 50:  # Hz
                pitch = (pitch1 + pitch2) / 2
            else:
                pitch = pitch1 if pitch1 > 0 else pitch2
            
            # Add to history
            pitch_history.append(pitch)
            if len(pitch_history) > history_size:
                pitch_history.pop(0)
            
            # Only proceed if we have a stable pitch
            if len(pitch_history) == history_size and is_onset:
                avg_pitch = sum(pitch_history) / len(pitch_history)
                std_pitch = np.std(pitch_history)
                
                if std_pitch < 10:  # Hz - require stable pitch
                    note_name = self.freq_to_note_name(avg_pitch)
                    if note_name and note_name in self.tine_notes:
                        last_time = last_note_times.get(note_name, -min_time_between_notes)
                        if frame_time - last_time >= min_time_between_notes:
                            note_events.append((frame_time, note_name))
                            last_note_times[note_name] = frame_time
                            print(f"Debug: Detected {note_name} at {frame_time:.2f}s (freq: {avg_pitch:.1f}Hz)")

        # Sort by time
        note_events.sort()
        
        print(f"\nDetected {len(note_events)} notes:")
        if note_events:
            for time, note in note_events[:10]:
                print(f"  {time:.2f}s: {note}")
            if len(note_events) > 10:
                print(f"  ... and {len(note_events)-10} more")
        else:
            print("  No notes detected!")
        
        return note_events

    def _generate_pins_from_notes(self) -> cq.Workplane:
        """
        Create a set of pins based on note events, ensuring we skip
        'overlapping' pins for the same note if they occur too close together
        in angle.
        """
        if not self._note_events:
            print("Warning: No notes detected to generate pins from")
            # Return an empty workplane that won't affect the union operation
            return cq.Workplane("XY").box(0.0001, 0.0001, 0.0001)

        pins = cq.Workplane("XY")
        z_min = self.base_ring_height + self.pin_vertical_offset
        centre_offset = self.pin_width / 2.0

        # Track last angle we used for each note to avoid collisions.
        last_note_angle = dict()  # note_name -> angle_in_degrees

        for (time_sec, note_name) in self._note_events:
            if note_name not in self.tine_notes:
                # Skip unknown note
                continue

            # Convert time to rotation angle [0..360]
            angle_deg = (time_sec / self.cassette_rotation_seconds) * 360.0

            # Check for overlap with same note
            if note_name in last_note_angle:
                prev_angle = last_note_angle[note_name]
                if abs(angle_deg - prev_angle) < self.min_note_angle_spacing:
                    # Skip this pin; it's too close in angle to the previous
                    # pin for the same note.
                    continue

            # Compute z offset based on the note's index
            note_index = self.tine_notes.index(note_name)
            spacing_offset = self.tine_width * note_index
            z_pin_center = z_min + spacing_offset + centre_offset
            z_bottom = z_pin_center - (self.pin_height / 2.0)

            # Convert angle_deg -> (x_center, y_center)
            x_center = self.cassette_radius * math.cos(math.radians(angle_deg))
            y_center = self.cassette_radius * math.sin(math.radians(angle_deg))

            single_pin = (
                cq.Workplane("XY")
                .box(
                    length=self.pin_radial_bump,
                    width=self.pin_width,
                    height=self.pin_height,
                    centered=(False, True, False)
                )
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((x_center, y_center, z_bottom))
            )

            pins = pins.union(single_pin)
            last_note_angle[note_name] = angle_deg

        return pins

    # Original geometry for main cassette
    def _make_base_ring(self) -> cq.Workplane:
        return (
            cq.Workplane("XY")
            .circle(self.base_ring_od / 2.0)
            .extrude(self.base_ring_height)
            .cut(
                cq.Workplane("XY")
                .circle(self.base_ring_id / 2.0)
                .extrude(self.base_ring_height)
            )
        )

    def _make_cassette_body(self) -> cq.Workplane:
        outer_cylinder = (
            cq.Workplane("XY")
            .workplane(offset=self.base_ring_height)
            .circle(self.cassette_radius)
            .extrude(self.cassette_total_height)
        )
        inner_cylinder = (
            cq.Workplane("XY")
            .workplane(offset=self.base_ring_height)
            .circle(self.cassette_radius - self.cassette_wall_thickness)
            .extrude(self.cassette_total_height)
        )
        return outer_cylinder.cut(inner_cylinder)

    def _make_top_assembly(self) -> cq.Workplane:
        lower_circle_z_start = self.base_ring_height + self.cassette_total_height
        big_cog_z_start = lower_circle_z_start + self.lower_circle_height
        big_cog_z_top = big_cog_z_start + self.big_cog_height
        small_cog_z_start = big_cog_z_top
        small_cog_z_top = small_cog_z_start + self.small_cog_height
        top_circle_z_start = small_cog_z_top

        lower_circle = (
            cq.Workplane("XY")
            .workplane(offset=lower_circle_z_start)
            .circle(self.lower_circle_diam / 2.0)
            .extrude(self.lower_circle_height)
        )

        big_cog = self._make_big_cog(big_cog_z_start)
        small_cog = self._make_small_cog(small_cog_z_start)
        
        top_circle = (
            cq.Workplane("XY")
            .workplane(offset=top_circle_z_start)
            .circle(self.top_circle_diam / 2.0)
            .extrude(self.top_circle_height)
        )

        return lower_circle.union(big_cog).union(small_cog).union(top_circle)

    def _make_big_cog(self, z_start: float) -> cq.Workplane:
        big_cog_base_radius = self.big_cog_base_diam / 2.0
        big_cog_teeth_radius = self.big_cog_teeth_diam / 2.0
        big_cog_radial_thick = big_cog_teeth_radius - big_cog_base_radius

        big_cog_base = (
            cq.Workplane("XY")
            .workplane(offset=z_start)
            .circle(big_cog_base_radius)
            .extrude(self.big_cog_height)
        )

        big_cog_teeth = cq.Workplane("XY")
        for i in range(self.num_teeth_big):
            angle_deg = i * (360.0 / self.num_teeth_big)
            angle_rad = math.radians(angle_deg)
            tooth_3d = self._make_big_cog_tooth(
                radial_thickness=big_cog_radial_thick,
                base_width=1.0,
                tip_width=0.4,
                tooth_height=self.big_cog_height,
                fillet_3d=0.1
            )
            tooth_3d = (
                tooth_3d
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((
                    big_cog_base_radius * math.cos(angle_rad),
                    big_cog_base_radius * math.sin(angle_rad),
                    z_start
                ))
            )
            big_cog_teeth = big_cog_teeth.union(tooth_3d)

        return big_cog_base.union(big_cog_teeth)

    def _make_small_cog(self, z_start: float) -> cq.Workplane:
        small_cog_base_radius = self.small_cog_base_diam / 2.0
        small_cog_teeth_radius = self.small_cog_teeth_diam / 2.0
        small_cog_radial_thick = small_cog_teeth_radius - small_cog_base_radius

        small_cog_base = (
            cq.Workplane("XY")
            .workplane(offset=z_start)
            .circle(small_cog_base_radius)
            .extrude(self.small_cog_height)
        )

        small_cog_teeth = cq.Workplane("XY")
        for i in range(self.num_teeth_small):
            angle_deg = i * (360.0 / self.num_teeth_small)
            angle_rad = math.radians(angle_deg)
            tooth_3d = self._make_small_cog_tooth(
                radial_thickness=small_cog_radial_thick,
                tooth_width=1.0,
                tooth_height=self.small_cog_height,
                fillet_3d=0.4
            )
            tooth_3d = (
                tooth_3d
                .rotate((0, 0, 0), (0, 0, 1), angle_deg)
                .translate((
                    small_cog_base_radius * math.cos(angle_rad),
                    small_cog_base_radius * math.sin(angle_rad),
                    z_start
                ))
            )
            small_cog_teeth = small_cog_teeth.union(tooth_3d)

        return small_cog_base.union(small_cog_teeth)

    def _make_big_cog_tooth(
        self,
        radial_thickness: float,
        base_width: float,
        tip_width: float,
        tooth_height: float,
        fillet_3d: float
    ) -> cq.Workplane:
        """
        Creates a trapezoidal tooth shape in 2D, extrudes it, then fillets
        the vertical edges. The trapezoid coordinates are defined by base_width,
        tip_width, and radial_thickness.
        """
        shape_2d = (
            cq.Workplane("XY")
            .polyline([
                (0, -base_width / 2.0),
                (0,  base_width / 2.0),
                (radial_thickness,  tip_width / 2.0),
                (radial_thickness, -tip_width / 2.0)
            ])
            .close()
        )
        tooth_3d = shape_2d.extrude(tooth_height)
        return tooth_3d.edges("|Z").fillet(fillet_3d)

    def _make_small_cog_tooth(
        self,
        radial_thickness: float,
        tooth_width: float,
        tooth_height: float,
        fillet_3d: float
    ) -> cq.Workplane:
        """
        Creates a rectangular tooth in 2D, extrudes it, then fillets all edges.
        """
        shape_2d = cq.Workplane("XY").rect(radial_thickness, tooth_width, centered=(False, True))
        tooth_3d = shape_2d.extrude(tooth_height)
        return tooth_3d.edges().fillet(fillet_3d)