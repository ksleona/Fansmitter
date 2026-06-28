# fansmitter_decode.py — diagnostic version
# Run: python fansmitter_decode.py recordings\recording1.wav

import numpy as np
import scipy.signal as sig
import scipy.io.wavfile as wavfile
import matplotlib.pyplot as plt
import sys
import os

# ============================================================
# CONFIGURATION — must match transmitter settings
# ============================================================
BIT_DURATION   = 10
STABILIZE_TIME = 3
BIT_SPACING    = BIT_DURATION + STABILIZE_TIME
PREAMBLE       = "10100000"
F0_HZ          = 70
F1_HZ          = 140
BANDWIDTH      = 30
# ============================================================

def load_audio(path):
    print(f"[*] Loading: {path}")
    fs, data = wavfile.read(path)
    if data.ndim > 1:
        print("    Stereo detected — using left channel")
        data = data[:, 0]
    if data.dtype == np.int16:
        data = data.astype(np.float64) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float64) / 2147483648.0
    elif data.dtype == np.float32:
        data = data.astype(np.float64)
    print(f"    Sample rate : {fs} Hz")
    print(f"    Duration    : {len(data)/fs:.1f} seconds")
    return data, fs

def downsample(audio, fs, target_fs=4000):
    ratio = fs // target_fs
    downsampled = audio[::ratio]
    new_fs = fs // ratio
    print(f"    Downsampled : {fs} Hz -> {new_fs} Hz (faster processing)")
    return downsampled, new_fs

def bandpass(audio, fs, center, bw):
    low  = max(center - bw, 2)
    high = min(center + bw, fs / 2 - 2)
    nyq  = fs / 2.0
    b, a = sig.butter(4, [low/nyq, high/nyq], btype='band')
    return sig.filtfilt(b, a, audio)

def rms(chunk, fs, freq, bw):
    f = bandpass(chunk, fs, freq, bw)
    return float(np.sqrt(np.mean(f ** 2)))

def detect_frequencies(audio, fs):
    print("[*] Using configured frequencies:")
    print(f"    F0 = {F0_HZ} Hz (bit 0)")
    print(f"    F1 = {F1_HZ} Hz (bit 1)")
    return F0_HZ, F1_HZ

def find_preamble(audio, fs, bit_dur, f0, f1, audio_f0=None, audio_f1=None):
    print("[*] Scanning for transmission start (full-frame correlation)...")
    spb_stable = int(bit_dur * fs)
    spb_total  = int(BIT_SPACING * fs)
    stab_offset = int(STABILIZE_TIME * fs)

    if audio_f0 is None:
        audio_f0 = bandpass(audio, fs, f0, BANDWIDTH)
    if audio_f1 is None:
        audio_f1 = bandpass(audio, fs, f1, BANDWIDTH)

    target_bits = 72
    window = target_bits * spb_total

    if window > len(audio):
        target_bits = len(audio) // spb_total - 1
        window = target_bits * spb_total

    best_score = -1
    best_pos = 0

    step_coarse = spb_total
    step_fine = max(spb_total // 4, 1)

    print(f"    Phase 1: Coarse scan ({target_bits} bits, {BIT_SPACING}s spacing)...")
    candidates = []

    for start in range(0, len(audio) - window, step_coarse):
        bits = ""
        for b in range(min(target_bits, 24)):
            s = start + b * spb_total + stab_offset
            e = s + spb_stable
            if e > len(audio):
                break
            e0 = float(np.sqrt(np.mean(audio_f0[s:e] ** 2)))
            e1 = float(np.sqrt(np.mean(audio_f1[s:e] ** 2)))
            bits += "1" if e1 > e0 else "0"

        if len(bits) < 16:
            continue

        preamble_match = sum(a == b for a, b in zip(bits[:8], PREAMBLE))

        length_bits = bits[8:16]
        try:
            length_val = int(length_bits, 2)
            length_score = max(0, 8 - abs(length_val - 6)) if length_val <= 50 else 0
        except:
            length_score = 0

        score = preamble_match * 2 + length_score * 3
        candidates.append((score, start))

        if score > best_score:
            best_score = score
            best_pos = start

    candidates.sort(reverse=True)
    top_candidates = candidates[:10]

    print(f"    Top 3 coarse positions:")
    for score, pos in top_candidates[:3]:
        print(f"      score={score} at {pos/fs:.1f}s")

    print(f"    Phase 2: Fine scan around top candidates...")
    best_score = -1

    for _, coarse_pos in top_candidates:
        fine_start = max(0, coarse_pos - 2 * spb_total)
        fine_end = min(len(audio) - window, coarse_pos + 2 * spb_total)

        for start in range(fine_start, fine_end, step_fine):
            bits = ""
            for b in range(min(target_bits, 24)):
                s = start + b * spb_total + stab_offset
                e = s + spb_stable
                if e > len(audio):
                    break
                e0 = float(np.sqrt(np.mean(audio_f0[s:e] ** 2)))
                e1 = float(np.sqrt(np.mean(audio_f1[s:e] ** 2)))
                bits += "1" if e1 > e0 else "0"

            if len(bits) < 16:
                continue

            preamble_match = sum(a == b for a, b in zip(bits[:8], PREAMBLE))

            length_bits = bits[8:16]
            try:
                length_val = int(length_bits, 2)
                length_score = max(0, 8 - abs(length_val - 6)) if length_val <= 50 else 0
            except:
                length_score = 0

            score = preamble_match * 2 + length_score * 3

            if score > best_score:
                best_score = score
                best_pos = start

    preamble_bits = ""
    for b in range(8):
        s = best_pos + b * spb_total + stab_offset
        e = s + spb_stable
        if e > len(audio):
            break
        e0 = float(np.sqrt(np.mean(audio_f0[s:e] ** 2)))
        e1 = float(np.sqrt(np.mean(audio_f1[s:e] ** 2)))
        preamble_bits += "1" if e1 > e0 else "0"

    preamble_match = sum(a == b for a, b in zip(preamble_bits, PREAMBLE))

    print(f"    Preamble match : {preamble_match}/{len(PREAMBLE)} bits")
    print(f"    Found at       : {best_pos/fs:.2f}s")
    return best_pos, preamble_match

def decode_bits(audio, fs, start, nbits, bit_dur, f0, f1, audio_f0=None, audio_f1=None):
    spb_stable  = int(bit_dur * fs)
    spb_total   = int(BIT_SPACING * fs)
    stab_offset = int(STABILIZE_TIME * fs)
    
    if audio_f0 is None:
        audio_f0 = bandpass(audio, fs, f0, BANDWIDTH)
    if audio_f1 is None:
        audio_f1 = bandpass(audio, fs, f1, BANDWIDTH)
    
    bits = []
    for i in range(nbits):
        s = start + i * spb_total + stab_offset
        e = s + spb_stable
        if e > len(audio):
            print(f"    [!] Audio ended early at bit {i+1}")
            break
        e0 = float(np.sqrt(np.mean(audio_f0[s:e] ** 2)))
        e1 = float(np.sqrt(np.mean(audio_f1[s:e] ** 2)))
        bits.append("1" if e1 > e0 else "0")
    return "".join(bits)

def binary_to_text(bits):
    chars = []
    for i in range(0, len(bits)-7, 8):
        try:
            v = int(bits[i:i+8], 2)
            chars.append(chr(v) if 32<=v<=126 else f"[{v}]")
        except:
            chars.append("?")
    return "".join(chars)

def verify_checksum(payload_bits, crc_bits):
    chk = 0
    for i in range(0, len(payload_bits), 8):
        if i+8 <= len(payload_bits):
            chk ^= int(payload_bits[i:i+8], 2)
    expected = format(chk, "08b")
    return expected == crc_bits, expected, crc_bits

def save_spectrogram(audio_original, fs_original, tx_start_original,
                     f0, f1, wav_path):
    print("[*] Generating spectrogram...")
    fig, axes = plt.subplots(2, 1, figsize=(16, 8))
    fig.suptitle("Fansmitter — Reception Analysis", fontsize=14,
                 fontweight="bold", color="white")
    fig.patch.set_facecolor("#0f0f23")
    t = np.linspace(0, len(audio_original)/fs_original, len(audio_original))
    axes[0].plot(t, audio_original, color="steelblue", linewidth=0.3, alpha=0.8)
    axes[0].axvline(x=tx_start_original, color="red",
                    linewidth=2, label="TX start")
    axes[0].set_title("Raw Waveform", color="white")
    axes[0].set_xlabel("Time (s)", color="white")
    axes[0].set_ylabel("Amplitude", color="white")
    axes[0].legend(facecolor="#1a1a2e", labelcolor="white")
    axes[0].set_facecolor("#1a1a2e")
    axes[0].tick_params(colors="white")
    axes[1].specgram(audio_original, Fs=fs_original, NFFT=4096,
                     noverlap=2048, cmap="inferno", vmin=-100)
    axes[1].set_ylim(0, 800)
    axes[1].axhline(y=f0, color="cyan", ls="--", lw=1.5,
                    label=f"F0={f0}Hz")
    axes[1].axhline(y=f1, color="lime", ls="--", lw=1.5,
                    label=f"F1={f1}Hz")
    axes[1].axvline(x=tx_start_original, color="red",
                    lw=2, label="TX start")
    axes[1].set_title("Frequency Spectrogram (0-800 Hz)", color="white")
    axes[1].set_xlabel("Time (s)", color="white")
    axes[1].set_ylabel("Frequency (Hz)", color="white")
    axes[1].legend(facecolor="#1a1a2e", labelcolor="white", loc="upper right")
    axes[1].set_facecolor("#1a1a2e")
    axes[1].tick_params(colors="white")
    plt.tight_layout()
    out = wav_path.replace(".wav", "_spectrogram.png")
    plt.savefig(out, dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    print(f"[*] Spectrogram saved: {out}")
    plt.close()

# ============================================================
# MAIN
# ============================================================
if len(sys.argv) < 2:
    print("Usage: python fansmitter_decode.py recordings\\recording1.wav")
    sys.exit(1)

wav_path = sys.argv[1]
if not os.path.exists(wav_path):
    print(f"[!] File not found: {wav_path}")
    sys.exit(1)

print("")
print("╔══════════════════════════════════════════════╗")
print("║         FANSMITTER DECODER                   ║")
print("╚══════════════════════════════════════════════╝")
print("")

# Load original audio for spectrogram
audio_orig, fs_orig = load_audio(wav_path)

# Downsample for faster processing
audio, fs = downsample(audio_orig, fs_orig, target_fs=4000)

# Detect frequencies
f0, f1 = detect_frequencies(audio, fs)

# Pre-filter audio once for faster decoding
print("[*] Pre-filtering audio...")
audio_f0 = bandpass(audio, fs, f0, BANDWIDTH)
audio_f1 = bandpass(audio, fs, f1, BANDWIDTH)

# Find preamble
preamble_start, score = find_preamble(audio, fs, BIT_DURATION, f0, f1, audio_f0, audio_f1)
preamble_start_orig = int(preamble_start * (fs_orig / fs))

if score < len(PREAMBLE) * 0.75:
    print("[!] Low preamble confidence — decoding anyway")

spb = int(BIT_SPACING * fs)

# ── DIAGNOSTIC — decode 80 bits after preamble and print raw ──
print("")
print("[*] DIAGNOSTIC — raw bits after preamble:")
raw_80 = decode_bits(audio, fs, preamble_start + len(PREAMBLE) * spb,
                     80, BIT_DURATION, f0, f1, audio_f0, audio_f1)
print(f"    Bits     : {raw_80}")
print(f"    As text  : {binary_to_text(raw_80)}")
print("")

# Decode length field
length_start = preamble_start + len(PREAMBLE) * spb
length_bits  = decode_bits(audio, fs, length_start, 8, BIT_DURATION, f0, f1, audio_f0, audio_f1)
num_chars    = int(length_bits, 2)
print(f"[*] Length bits  : {length_bits}")
print(f"[*] Payload length: {num_chars} characters")

# Decode payload
payload_start = length_start + 8 * spb
payload_bits  = decode_bits(audio, fs, payload_start,
                            num_chars * 8, BIT_DURATION, f0, f1, audio_f0, audio_f1)

# Decode checksum
crc_start = payload_start + num_chars * 8 * spb
crc_bits  = decode_bits(audio, fs, crc_start, 8, BIT_DURATION, f0, f1, audio_f0, audio_f1)

# Verify
csum_ok, expected, received = verify_checksum(payload_bits, crc_bits)
decoded_text = binary_to_text(payload_bits)

print("")
print("╔══════════════════════════════════════════════╗")
print("║           DECODING RESULTS                   ║")
print("╠══════════════════════════════════════════════╣")
print(f"║  F0 used    : {f0} Hz{'':<28}║")
print(f"║  F1 used    : {f1} Hz{'':<28}║")
print(f"║  Preamble   : {score}/{len(PREAMBLE)} bits matched{'':<20}║")
print(f"║  Length bits: {length_bits:<32}║")
print(f"║  Checksum   : {'PASS' if csum_ok else 'FAIL — bit errors present':<32}║")
print("╠══════════════════════════════════════════════╣")
print(f"║  DECODED    : {decoded_text:<32}║")
print("╚══════════════════════════════════════════════╝")
print("")

save_spectrogram(audio_orig, fs_orig, preamble_start_orig, f0, f1, wav_path)