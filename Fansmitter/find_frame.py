import numpy as np
import scipy.signal as sig
import scipy.io.wavfile as wavfile

fs, data = wavfile.read("recordings/recording3.wav")
if data.ndim > 1: data = data[:, 0]
if data.dtype == np.int16: data = data.astype(np.float64) / 32768.0

ratio = fs // 4000
audio = data[::ratio]
fs2 = fs // ratio

def bp(audio, fs, center, bw=30):
    low = max(center - bw, 2)
    high = min(center + bw, fs/2 - 2)
    nyq = fs / 2.0
    b, a = sig.butter(4, [low/nyq, high/nyq], btype="band")
    return sig.filtfilt(b, a, audio)

f0, f1 = 70, 140
a0 = bp(audio, fs2, f0, 30)
a1 = bp(audio, fs2, f1, 30)

SECRET = "EH2026"
PREAMBLE = "10100000"

def string_to_binary(text):
    return "".join(format(ord(c), "08b") for c in text)

def build_frame(payload_bits):
    length_bits = format(len(payload_bits) // 8, "08b")
    checksum = 0
    for i in range(0, len(payload_bits), 8):
        checksum ^= int(payload_bits[i:i+8], 2)
    return PREAMBLE + length_bits + payload_bits + format(checksum, "08b")

payload_binary = string_to_binary(SECRET)
frame = build_frame(payload_binary)
print(f"Expected frame ({len(frame)} bits):")
print(f"  Preamble: {PREAMBLE}")
print(f"  Length  : {format(len(SECRET), '08b')}")
print(f"  Payload : {payload_binary}")
print(f"  Checksum: {frame[-8:]}")
print()

spb_total = int(7 * fs2)
stab_offset = int(2 * fs2)
spb_stable = int(5 * fs2)

print("Scanning for best frame match (0-30s, 0.5s steps)...")
best_score = 0
best_start = 0
best_bits = ""

for start_s in np.arange(0, 30, 0.5):
    start = int(start_s * fs2)
    bits = ""
    for b in range(len(frame)):
        s = start + b * spb_total + stab_offset
        e = s + spb_stable
        if e > len(audio):
            break
        e0 = float(np.sqrt(np.mean(a0[s:e]**2)))
        e1 = float(np.sqrt(np.mean(a1[s:e]**2)))
        bits += "1" if e1 > e0 else "0"
    
    if len(bits) < len(frame):
        continue
    
    score = sum(a == b for a, b in zip(bits, frame))
    if score > best_score:
        best_score = score
        best_start = start
        best_bits = bits
        print(f"  {score}/{len(frame)} at {start_s:.1f}s")

print()
print(f"Best match: {best_score}/{len(frame)} at {best_start/fs2:.2f}s")
print()
print("Bit-by-bit comparison:")
print(f"Detected : {best_bits}")
print(f"Expected : {frame}")
print()

matches = "".join("^" if a == b else " " for a, b in zip(best_bits, frame))
print(f"         : {matches}")
print()

sections = [
    ("PREAMBLE", 0, 8),
    ("LENGTH", 8, 16),
    ("PAYLOAD", 16, 64),
    ("CHECKSUM", 64, 72),
]
for name, s, e in sections:
    det = best_bits[s:e]
    exp = frame[s:e]
    score = sum(a == b for a, b in zip(det, exp))
    print(f"{name:10s}: det={det}  exp={exp}  {score}/{e-s} correct")

if best_bits[16:64]:
    payload_bits = best_bits[16:64]
    chars = []
    for i in range(0, len(payload_bits), 8):
        v = int(payload_bits[i:i+8], 2)
        chars.append(chr(v) if 32 <= v <= 126 else f"[{v}]")
    print(f"\nDecoded payload: {''.join(chars)}")
