"""
File: ai_note_builder.py
Uses Claude AI to generate note sequences for known songs.
"""

import json
import anthropic
from typing import List, Tuple
from tine import Tine

def get_notes_from_text(song_description: str, duration: float) -> List[Tuple[float, str]]:
    """
    Ask Claude to generate a sequence of notes and timings for a given song description.
    
    Args:
        song_description: Name or description of the song
        duration: Target duration in seconds
        
    Returns:
        List of (time_in_sec, note_name) tuples
    """
    client = anthropic.Anthropic()
    
    # Get available notes from Tine class
    available_notes = sorted(Tine().notes)
    
    prompt = f"""
    I need you to provide musical notes and timing for a mechanical music box that will play "{song_description}".

    Important context:
    - This is for a physical music box with metal tines that are plucked by pins on a rotating cylinder
    - The cylinder takes exactly {duration} seconds for one complete rotation
    - The music box only has these available notes: {', '.join(available_notes)}, do not use any other notes.
      Nothing below {available_notes[0]} and nothing above {available_notes[-1]}.
    - If the song requires notes that aren't available (like sharps or flats), transpose it to a key that works with these notes
    - The notes must be spaced far enough apart to allow the tines to resonate (minimum 0.15 seconds between same note)
    - Music boxes can play multiple notes simultaneously for chords or richer arrangements
    - Music boxes typically play at a moderate to brisk tempo (quarter note ≈ 0.3-0.5 seconds)
    - The arrangement should balance simplicity with musicality - chords and harmonies are welcome when appropriate
    
    Please provide the notes as a JSON array of [time_in_seconds, note_name] pairs.
    Times must start at 0 and cannot exceed {duration} seconds.
    Only use notes from the available list above.
    
    Only respond with valid JSON that I can parse. Format:
    {{
        "thinking": "Key points about: 1) Original key and any transposition needed 2) How the melody was adapted 3) Tempo and timing calculations 4) Any compression or adjustments made to fit {duration}s",
        "notes": [
            [0.0, "C5"],
            [0.4, "E5"],
            ...
        ]
    }}

    Make sure to:
    1. Preserve the essential character of the melody when transposing
    2. Keep a lively music box tempo (quarter note around 0.4 seconds)
    3. Use the available time efficiently - you can repeat sections if appropriate
    4. Maintain minimum 0.15s spacing between same notes. Never slow down a song, only speed it up if it doesn't fit within the {duration}-second rotation time
    5. Explain your musical decisions in the thinking field
    
    Important: The "thinking" field must be a single line with no line breaks or special characters.
    """
    
    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2000,
            temperature=0,
            system="You are a musical expert specializing in mechanical music boxes. You understand their physical limitations and how to arrange music appropriately for them.",
            messages=[{
                "role": "user",
                "content": prompt
            }]
        )
        
        # Extract JSON from response
        response = message.content[0].text
        print(response)
        
        # Check if response appears to be truncated
        if not response.strip().endswith('}'):
            raise ValueError("Response appears to be truncated")
            
        try:
            parsed = json.loads(response)
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {e}")
            print("Raw response:")
            print(response)
            return []
            
        note_events = parsed['notes']
        
        # Validate format and notes
        if not isinstance(note_events, list):
            raise ValueError("Response is not a list")
        
        valid_notes = set(available_notes)  # for faster lookups
        for event in note_events:
            if not isinstance(event, list) or len(event) != 2:
                raise ValueError("Invalid event format")
            if not isinstance(event[0], (int, float)) or not isinstance(event[1], str):
                raise ValueError("Invalid event types")
            if event[1] not in valid_notes:
                raise ValueError(f"Invalid note: {event[1]}")
            if event[0] < 0 or event[0] > duration:
                raise ValueError(f"Time out of range: {event[0]}")
                
        return note_events
        
    except Exception as e:
        print(f"Error getting notes from AI: {e}")
        return [] 