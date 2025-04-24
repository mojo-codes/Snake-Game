import os
import numpy as np
from scipy.io import wavfile

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def create_eat_sound():
    # Create a short "blip" sound for eating
    sample_rate = 44100
    duration = 0.1  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Create a simple sine wave with frequency that increases
    frequency = 800 + 1200 * t / duration
    waveform = np.sin(2 * np.pi * frequency * t)
    # Apply a simple envelope to avoid clicks
    envelope = np.linspace(1, 0, len(waveform)) ** 0.5
    waveform = waveform * envelope
    # Normalize
    waveform = waveform * 0.5
    # Convert to 16-bit PCM
    waveform_integers = (waveform * 32767).astype(np.int16)
    
    return sample_rate, waveform_integers

def create_game_over_sound():
    # Create a "fail" sound for game over
    sample_rate = 44100
    duration = 0.7  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Create a descending tone
    frequency = 400 - 300 * t / duration
    waveform = np.sin(2 * np.pi * frequency * t)
    # Add a bit of distortion
    waveform = np.clip(waveform * 1.5, -1, 1)
    # Apply an envelope
    envelope = np.exp(-5 * t / duration)
    waveform = waveform * envelope
    # Normalize
    waveform = waveform * 0.7
    # Convert to 16-bit PCM
    waveform_integers = (waveform * 32767).astype(np.int16)
    
    return sample_rate, waveform_integers

def create_pause_sound():
    # Create a simple "click" sound for pause
    sample_rate = 44100
    duration = 0.05  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    # Create a simple sine wave
    frequency = 700
    waveform = np.sin(2 * np.pi * frequency * t)
    # Apply a simple envelope to avoid clicks
    envelope = np.exp(-10 * t / duration)
    waveform = waveform * envelope
    # Normalize
    waveform = waveform * 0.6
    # Convert to 16-bit PCM
    waveform_integers = (waveform * 32767).astype(np.int16)
    
    return sample_rate, waveform_integers

def create_background_music():
    # Create a simple looping background "music" (basic tones)
    sample_rate = 44100
    duration = 5.0  # seconds
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    # Create a simple chord sequence
    chord_duration = 0.5  # seconds
    num_chords = int(duration / chord_duration)
    chord_frequencies = [
        [261.63, 329.63, 392.00],  # C major
        [293.66, 369.99, 440.00],  # D major
        [261.63, 329.63, 392.00],  # C major
        [246.94, 311.13, 369.99],  # B minor
        [261.63, 329.63, 392.00],  # C major
        [293.66, 369.99, 440.00],  # D major
        [329.63, 392.00, 493.88],  # E minor
        [293.66, 369.99, 440.00],  # D major
        [261.63, 329.63, 392.00],  # C major
        [246.94, 311.13, 369.99],  # B minor
    ]
    
    waveform = np.zeros_like(t)
    for i in range(num_chords):
        chord = chord_frequencies[i % len(chord_frequencies)]
        start_idx = int(i * chord_duration * sample_rate)
        end_idx = int((i + 1) * chord_duration * sample_rate)
        segment_t = t[start_idx:end_idx] - i * chord_duration
        
        for freq in chord:
            waveform[start_idx:end_idx] += 0.2 * np.sin(2 * np.pi * freq * segment_t)
    
    # Add a simple rhythm
    beat_freq = 4  # beats per second
    beat_waveform = np.sin(2 * np.pi * beat_freq * t)
    beat_waveform = (beat_waveform > 0.9).astype(float) * 0.1
    waveform += beat_waveform
    
    # Apply a gentle limiting
    waveform = np.tanh(waveform)
    
    # Convert to 16-bit PCM
    waveform_integers = (waveform * 32767).astype(np.int16)
    
    return sample_rate, waveform_integers

def main():
    print("Creating sound directory...")
    ensure_dir("sounds")
    
    print("Generating eat sound...")
    sample_rate, eat_sound = create_eat_sound()
    wavfile.write("sounds/eat.wav", sample_rate, eat_sound)
    
    print("Generating game over sound...")
    sample_rate, game_over_sound = create_game_over_sound()
    wavfile.write("sounds/game_over.wav", sample_rate, game_over_sound)
    
    print("Generating pause sound...")
    sample_rate, pause_sound = create_pause_sound()
    wavfile.write("sounds/pause.wav", sample_rate, pause_sound)
    
    print("Generating background music...")
    sample_rate, bg_music = create_background_music()
    wavfile.write("sounds/background.wav", sample_rate, bg_music)
    
    print("All sounds created successfully!")
    print("Run the game with: python snake_game.py")

if __name__ == "__main__":
    main() 