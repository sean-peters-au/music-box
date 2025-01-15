"""
File: note_extractor.py
Extracts and filters note events from an MP3 file.
"""

import math
import numpy as np
import aubio
from pydub import AudioSegment
from scipy.signal import butter, filtfilt
from tine import Tine


def freq_to_note_name(freq: float) -> str:
    """
    Approximate frequency -> note name (A4=440Hz) with a chromatic scale.
    Returns None if freq is invalid or cannot be mapped.
    """
    if freq <= 0:
        return None

    midi_num = 69 + 12 * math.log2(freq / 440.0)
    midi_rounded = int(round(midi_num))

    note_names = ["C", "C#", "D", "D#", "E", "F",
                  "F#", "G", "G#", "A", "A#", "B"]
    name = note_names[midi_rounded % 12]
    octave = (midi_rounded // 12) - 1
    return f"{name}{octave}"


def extract_notes_from_mp3(
    mp3_path: str,
    max_time: float = 20.0,
    min_time_between_notes: float = 0.15,
    onset_threshold: float = 0.3,
    pitch_stability_threshold: float = 9.0,
    squeeze_to_duration: float = None
):
    """
    Extracts note events from an MP3 file up to max_time seconds.
    Returns a list of (time_in_sec, note_name).

    Args:
        mp3_path: Path to the MP3 file to analyze.
        max_time: Maximum audio duration to process (seconds).
        min_time_between_notes: Minimum gap (seconds) to register a new note.
        onset_threshold: Onset strength threshold for aubio.
        pitch_stability_threshold: Maximum stddev in pitch history to accept.
        squeeze_to_duration: If set, squeezes the extracted notes into this duration.

    Returns:
        A sorted list of (time_sec, note_name).
    """
    # Load and clamp to max_time
    print(f"Loading {mp3_path}...")
    print(f"Max time: {max_time}s")
    audio = AudioSegment.from_mp3(mp3_path)
    audio = audio[: int(max_time * 1000)]

    # Convert to mono, 16-bit PCM
    if audio.channels > 1:
        audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)
    sr = audio.frame_rate
    raw_data = np.frombuffer(audio._data, dtype=np.int16).astype(float)
    raw_data = raw_data / np.max(np.abs(raw_data))

    # Bandpass filter to focus on typical fundamental frequencies
    nyquist = sr / 2
    low_cut = 60
    high_cut = 2000
    b, a = butter(4, [low_cut/nyquist, high_cut/nyquist], btype='band')
    raw_data = filtfilt(b, a, raw_data)

    # Setup pitch and onset detectors
    frame_size = 512
    hop_size = 512

    pitch_yinfft = aubio.pitch("yinfft", frame_size, hop_size, sr)
    pitch_yin = aubio.pitch("yin", frame_size, hop_size, sr)
    pitch_yinfft.set_unit("Hz")
    pitch_yin.set_unit("Hz")
    pitch_yinfft.set_silence(-20)
    pitch_yin.set_silence(-20)

    onset_detector = aubio.onset("complex", frame_size, hop_size, sr)
    onset_detector.set_threshold(onset_threshold)

    # Prepare results
    note_events = []
    last_note_time = {}
    pitch_history = []
    history_size = 3
    allowed_notes = set(Tine().notes)  # for quick membership checks

    for start_idx in range(0, len(raw_data) - frame_size, hop_size):
        frame = raw_data[start_idx : start_idx + frame_size].astype(np.float32)
        frame_time = start_idx / sr
        if frame_time > max_time:
            break

        # Pitch detection
        p1 = pitch_yinfft(frame)[0]
        p2 = pitch_yin(frame)[0]
        pitch = p1 if abs(p1 - p2) > 50 else (p1 + p2) / 2

        # Onset detection
        is_onset = onset_detector(frame)[0]

        # Rolling pitch history
        pitch_history.append(pitch)
        if len(pitch_history) > history_size:
            pitch_history.pop(0)

        if is_onset and len(pitch_history) == history_size:
            avg_pitch = sum(pitch_history) / len(pitch_history)
            std_pitch = np.std(pitch_history)

            if std_pitch < pitch_stability_threshold:
                note_name = freq_to_note_name(avg_pitch)
                if note_name and note_name in allowed_notes:
                    # Enforce a minimal time gap between repeats
                    last_t = last_note_time.get(note_name, -min_time_between_notes)
                    if (frame_time - last_t) >= min_time_between_notes:
                        note_events.append((frame_time, note_name))
                        last_note_time[note_name] = frame_time

    note_events.sort(key=lambda x: x[0])

    # If squeezing is requested, scale all timestamps
    if squeeze_to_duration and note_events:
        print(f"Squeezing to {squeeze_to_duration}s")
        original_duration = note_events[-1][0]  # Last event's timestamp
        if original_duration > 0:  # Prevent division by zero
            scale_factor = squeeze_to_duration / original_duration
            note_events = [(t * scale_factor, note) for t, note in note_events]

    print(f"Extracted {len(note_events)} notes")
    print(note_events)
    return note_events
