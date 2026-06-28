import numpy as np
import scipy.signal as sig
import scipy.io.wavfile as wavfile

fs, data = wavfile.read("recordings/recording4.wav")
if data.ndim > 1: data = data[:, 0]
if data.dtype == np.int16: data = data.astype(np.float64) / 32768.0

ratio = fs // 4000
audio = data[::ratio]
fs2 = fs // ratio

print("Analyzing bit-by-bit energy across the recording...")
print("Looking for ANY clear signal pattern\n")

spb = int(13 * fs2)
stab_offset = int(3 * fs2)

def bp(audio, fs, center, bw=30):
    low = max(center - bw, 2)
    high = min(center + bw, fs/2 - 2)
    nyq = fs / 2.0
    b, a = sig.butter(4, [low/nyq, high/nyq], btype="band")
    return sig.filtfilt(b, a, audio)

print("Testing 70Hz vs 140Hz at 1-second resolution:")
a0 = bp(audio, fs2, 70, 30)
a1 = bp(audio, fs2, 140, 30)

print(f"{'Time':>6s}  {'E(70Hz)':>10s}  {'E(140Hz)':>10s}  {'Ratio':>8s}  {'Total':>10s}")
for t in range(0, min(600, len(audio)//fs2), 1):
    s = int(t * fs2)
    e = s + int(1 * fs2)
    if e > len(audio):
        break
    e0 = float(np.sqrt(np.mean(a0[s:e]**2)))
    e1 = float(np.sqrt(np.mean(a1[s:e]**2)))
    total = float(np.sqrt(np.mean(audio[s:e]**2)))
    ratio = e1/e0 if e0 > 1e-9 else 999
    
    if total > 0.001:
        marker = " <<<"
    else:
        marker = ""
    
    if t % 10 == 0 or total > 0.001:
        print(f"{t:6d}s  {e0:10.6f}  {e1:10.6f}  {ratio:8.3f}  {total:10.6f}{marker}")
