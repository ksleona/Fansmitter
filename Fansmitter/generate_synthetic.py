import numpy as np
import scipy.io.wavfile as wavfile
import time

SECRET = "EH2026"
PREAMBLE = "10100000"
F0_HZ = 70
F1_HZ = 140
BIT_DURATION = 10
STABILIZE_TIME = 3
SAMPLE_RATE = 44100

def string_to_binary(text):
    return "".join(format(ord(c), "08b") for c in text)

def build_frame(payload_bits):
    length_bits = format(len(payload_bits) // 8, "08b")
    checksum = 0
    for i in range(0, len(payload_bits), 8):
        checksum ^= int(payload_bits[i:i+8], 2)
    return PREAMBLE + length_bits + payload_bits + format(checksum, "08b")

def generate_tone(freq, duration, sample_rate, amplitude=0.3):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq * t)

def generate_transition(freq_start, freq_end, duration, sample_rate, amplitude=0.3):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    freq_sweep = np.linspace(freq_start, freq_end, len(t))
    phase = 2 * np.pi * np.cumsum(freq_sweep) / sample_rate
    return amplitude * np.sin(phase)

print("Generating synthetic Fansmitter recording...")
print(f"  Secret: {SECRET}")
print(f"  F0: {F0_HZ} Hz (bit 0)")
print(f"  F1: {F1_HZ} Hz (bit 1)")
print(f"  Bit duration: {BIT_DURATION}s")
print(f"  Stabilization: {STABILIZE_TIME}s")
print()

payload_binary = string_to_binary(SECRET)
frame = build_frame(payload_binary)

print(f"Frame ({len(frame)} bits):")
print(f"  Preamble: {PREAMBLE}")
print(f"  Length  : {format(len(SECRET), '08b')}")
print(f"  Payload : {payload_binary}")
print(f"  Checksum: {frame[-8:]}")
print()

audio = []

print("Adding 5 seconds of silence at start...")
audio.append(np.zeros(int(5 * SAMPLE_RATE)))

print("Generating bits...")
for i, bit in enumerate(frame):
    target_freq = F1_HZ if bit == "1" else F0_HZ
    
    if i == 0:
        prev_freq = 100
    else:
        prev_bit = frame[i-1]
        prev_freq = F1_HZ if prev_bit == "1" else F0_HZ
    
    transition = generate_transition(prev_freq, target_freq, STABILIZE_TIME, SAMPLE_RATE, 0.25)
    audio.append(transition)
    
    stable = generate_tone(target_freq, BIT_DURATION, SAMPLE_RATE, 0.3)
    audio.append(stable)
    
    if i < len(PREAMBLE):
        section = "PREAMBLE"
    elif i < len(PREAMBLE) + 8:
        section = "LENGTH"
    elif i < len(frame) - 8:
        char_idx = (i - len(PREAMBLE) - 8) // 8
        char = SECRET[min(char_idx, len(SECRET)-1)]
        section = f"PAYLOAD '{char}'"
    else:
        section = "CHECKSUM"
    
    progress = int((i / len(frame)) * 40)
    bar = chr(9608) * progress + chr(9617) * (40 - progress)
    print(f"  [{bar}] bit {i+1:2d}/{len(frame)}  val={bit}  {target_freq}Hz  {section}")

print("\nAdding 5 seconds of silence at end...")
audio.append(np.zeros(int(5 * SAMPLE_RATE)))

audio = np.concatenate(audio)

print("\nAdding realistic noise...")
noise = np.random.normal(0, 0.02, len(audio))
audio = audio + noise

audio = np.clip(audio, -1.0, 1.0)
audio_int16 = (audio * 32767).astype(np.int16)

output_file = "recordings/synthetic_test.wav"
print(f"\nSaving to {output_file}...")
wavfile.write(output_file, SAMPLE_RATE, audio_int16)

duration = len(audio) / SAMPLE_RATE
print(f"Duration: {duration:.1f} seconds")
print(f"File size: {len(audio_int16) * 2 / 1024 / 1024:.1f} MB")
print()
print("Now decode with:")
print(f"  python fansmitter_decode.py {output_file}")
