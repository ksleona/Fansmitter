import numpy as np
import scipy.signal as sig
import scipy.io.wavfile as wavfile

fs, data = wavfile.read("recordings/recording3.wav")
if data.ndim > 1: data = data[:, 0]
if data.dtype == np.int16: data = data.astype(np.float64) / 32768.0

print(f"fs={fs}, duration={len(data)/fs:.1f}s")

ratio = fs // 4000
audio = data[::ratio]
fs2 = fs // ratio

freqs, psd = sig.welch(audio, fs2, nperseg=4096)
mask = (freqs >= 30) & (freqs <= 300)
fm = freqs[mask]
pm = psd[mask]

peaks, _ = sig.find_peaks(pm, height=np.max(pm)*0.02, distance=5)
top = sorted(peaks, key=lambda x: pm[x], reverse=True)[:15]

print("\nTop 15 frequency peaks:")
for p in top:
    print(f"  {fm[p]:6.1f} Hz  PSD={pm[p]:.2e}")

print("\n=== Checking specific frequency pairs ===")
pairs = [
    (60, 120, "Original config"),
    (84.2, 142.9, "Recording2 detected"),
    (121.4, 146.8, "Recording3 detected"),
    (70, 140, "Hypothesis 1"),
    (80, 160, "Hypothesis 2"),
]

for f0, f1, label in pairs:
    ratio = f1 / f0
    print(f"\n{label}: F0={f0}Hz, F1={f1}Hz (ratio={ratio:.2f})")
    
    def bp(audio, fs, center, bw=30):
        low = max(center - bw, 2)
        high = min(center + bw, fs/2 - 2)
        nyq = fs / 2.0
        b, a = sig.butter(4, [low/nyq, high/nyq], btype="band")
        return sig.filtfilt(b, a, audio)
    
    a0 = bp(audio, fs2, f0, 30)
    a1 = bp(audio, fs2, f1, 30)
    
    spb = int(7 * fs2)
    stab_offset = int(2 * fs2)
    
    print(f"  Energy at different times (after 2s stabilization):")
    for t in [10, 20, 30, 40, 50, 100, 150, 200, 250]:
        start = int(t * fs2) + stab_offset
        end = start + int(5 * fs2)
        if end > len(audio):
            break
        e0 = float(np.sqrt(np.mean(a0[start:end]**2)))
        e1 = float(np.sqrt(np.mean(a1[start:end]**2)))
        ratio = e1/e0 if e0 > 1e-9 else 999
        print(f"    {t:3d}s: e0={e0:.6f}  e1={e1:.6f}  ratio={ratio:.3f}")
