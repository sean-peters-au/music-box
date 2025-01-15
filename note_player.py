"""
File: note_player.py
Generates and plays 'music-box' tones for a given sequence of notes.
"""

import time
import os
import numpy as np
import sounddevice as sd


def note_to_freq(note_name: str) -> float:
    """
    Convert a note name (e.g. 'A4') to frequency in Hz (A4=440Hz reference).
    """
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = int(note_name[-1])
    note = note_name[:-1]
    semitone_index = note_names.index(note)
    return 440.0 * 2 ** ((octave - 4) + (semitone_index - 9) / 12)


def generate_tone(freq: float, duration_ms: int = 250) -> np.ndarray:
    """
    Generate a music-box-like tone simulating a struck metal tine.
    Returns raw audio samples.
    """
    sample_rate = 44100
    num_samples = int(sample_rate * duration_ms / 1000)
    t = np.arange(num_samples) / sample_rate

    # Slightly stretched harmonics to simulate tine inharmonicity
    harmonics = [
        (1.000, 1.00),    # fundamental
        (2.002, 0.75),    # slightly sharp octave (increased from 0.60)
        (3.004, 0.35),    # slightly sharp twelfth (increased from 0.18)
        (4.008, 0.15),    # slightly sharp double octave
        (5.015, 0.08),    # upper harmonics increasingly sharp
        (6.025, 0.05),
        (7.040, 0.03),
        (8.060, 0.02),
    ]

    # Generate base waveform with inharmonic components
    samples = np.zeros_like(t)
    for mult, amp in harmonics:
        # Add slight random phase variation for more natural sound
        phase = np.random.uniform(0, 0.2)  # Increased phase variation
        samples += amp * np.sin(2 * np.pi * freq * mult * t + phase)

    # Initial "ping" transient
    ping_duration = int(0.015 * sample_rate)  # Increased to 15ms
    ping_freq = freq * 3  # Reduced from 4x to 3x for less harsh attack
    ping = np.sin(2 * np.pi * ping_freq * t[:ping_duration]) * np.exp(-t[:ping_duration] * 150)
    samples[:ping_duration] += ping * 0.4

    # More sophisticated envelope with longer decay
    attack_ms = 3
    decay_1_ms = 40   # Initial quick decay
    decay_2_ms = 150  # Longer resonant decay
    release_ms = 60
    
    attack_samples = int(sample_rate * attack_ms / 1000)
    decay_1_samples = int(sample_rate * decay_1_ms / 1000)
    decay_2_samples = int(sample_rate * decay_2_ms / 1000)
    release_samples = int(sample_rate * release_ms / 1000)
    
    # Create envelope
    envelope = np.ones(num_samples)
    
    # Fast but smooth attack
    envelope[:attack_samples] = np.power(np.linspace(0, 1, attack_samples), 0.7)
    
    # Two-stage decay for more natural resonance
    decay_1_curve = np.exp(-np.linspace(0, 2, decay_1_samples))  # Gentler initial decay
    decay_2_curve = np.exp(-np.linspace(2, 3, decay_2_samples))  # Much gentler long decay
    decay_curve = np.concatenate([decay_1_curve, decay_2_curve])
    
    decay_start = attack_samples
    decay_end = min(decay_start + len(decay_curve), num_samples)
    envelope[decay_start:decay_end] *= decay_curve[:decay_end-decay_start]
    
    # Gentle release
    if num_samples > (decay_start + len(decay_curve)):
        release_start = decay_start + len(decay_curve)
        release_curve = np.exp(-np.linspace(3, 4, release_samples))
        release_end = min(release_start + release_samples, num_samples)
        envelope[release_start:release_end] *= release_curve[:release_end-release_start]

    # Apply envelope
    samples *= envelope

    # Add subtle resonant frequencies
    resonance = np.random.normal(0, 0.0002, len(samples))
    resonance = np.convolve(resonance, np.exp(-np.linspace(0, 10, 1000)), mode='same')
    resonance *= envelope
    samples += resonance

    # Soft limiting to prevent harsh clipping while preserving dynamics
    samples = np.tanh(samples * 0.8)
    
    return samples.astype(np.float32)


def simulate_notes(note_events, total_duration: float):
    """
    Renders and plays the complete song.
    Each event is a tuple (time_in_sec, note_name).
    Supports simultaneous notes for chords.
    """
    if not note_events:
        print("No notes to simulate.")
        return

    print("Simulating cassette playback...")
    
    # Audio settings
    sample_rate = 44100
    total_samples = int(sample_rate * total_duration)
    
    # Pre-render all unique notes
    unique_notes = sorted(set([evt[1] for evt in note_events]))
    tone_map = {n: generate_tone(note_to_freq(n)) for n in unique_notes}
    
    # Create full song buffer
    song_buffer = np.zeros(total_samples, dtype=np.float32)
    
    # Group notes by time
    time_grouped_notes = {}
    for time, note in note_events:
        sample_pos = int(time * sample_rate)
        if sample_pos not in time_grouped_notes:
            time_grouped_notes[sample_pos] = []
        time_grouped_notes[sample_pos].append(note)
    
    # Mix all notes into the song buffer
    for sample_pos, notes in sorted(time_grouped_notes.items()):
        # Print chord or single note
        if len(notes) > 1:
            print(f"♪ [{' '.join(notes)}]", end=' ', flush=True)
        else:
            print(f"♪ {notes[0]}", end=' ', flush=True)
            
        # Mix notes that start at this position
        chord_samples = np.zeros_like(tone_map[notes[0]])
        for note in notes:
            chord_samples += tone_map[note]
        
        # Normalize chord
        chord_samples /= max(1.0, len(notes))
        
        # Add to song buffer
        end_pos = min(sample_pos + len(chord_samples), total_samples)
        song_buffer[sample_pos:end_pos] += chord_samples[:end_pos-sample_pos]
    
    # Optional: Add subtle reverb
    reverb_length = int(0.1 * sample_rate)  # 100ms reverb
    reverb = np.exp(-np.linspace(0, 4, reverb_length)).astype(np.float32)  # Force float32
    song_buffer = np.convolve(song_buffer, reverb, mode='same').astype(np.float32)  # Force float32
    
    # Final normalization
    song_buffer /= np.max(np.abs(song_buffer))
    song_buffer = song_buffer.astype(np.float32)  # Ensure final buffer is float32
    
    # Play the complete song
    stream = sd.OutputStream(
        samplerate=sample_rate,
        channels=1,
        dtype=np.float32,
        latency='low'
    )
    
    with stream:
        stream.write(song_buffer)
    
    print("\nSimulation complete.")