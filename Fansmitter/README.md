# Fansmitter

Acoustic data exfiltration from air-gapped computers via CPU fan speed modulation.

This project implements a covert acoustic channel that encodes binary data by varying CPU fan speed between two RPM levels, each producing a distinct acoustic frequency. A nearby recording device (smartphone) captures the audio, which is then decoded using DSP techniques to recover the original data.

Based on the research paper *"Fansmitter: Acoustic Data Exfiltration from (Speakerless) Air-Gapped Computers"* by Mordechai Guri et al., Ben-Gurion University (2016).

## How It Works

```
┌──────────────────┐         acoustic          ┌──────────────────┐
│  Air-gapped PC   │      70 Hz / 140 Hz       │  Smartphone Mic  │
│                  │ ─────────────────────────> │                  │
│  fansmitter_     │    bit 0 = 10% (~1000RPM) │  Record WAV      │
│  transmit.py     │    bit 1 = 100% (~2800RPM)│                  │
└──────────────────┘                            └────────┬─────────┘
                                                         │
                                                         ▼
                                                ┌──────────────────┐
                                                │  fansmitter_     │
                                                │  decode.py       │
                                                │                  │
                                                │  Output: EH2026  │
                                                └──────────────────┘
```

### Protocol Frame

```
┌──────────┬──────────┬──────────────────┬──────────┐
│ Preamble │  Length  │     Payload      │ Checksum │
│ 8 bits   │ 8 bits   │    N × 8 bits    │ 8 bits   │
│ 10100000 │ 00000110 │  ASCII encoded   │   XOR    │
└──────────┴──────────┴──────────────────┴──────────┘
```

## Requirements

### Hardware
- **PC/Laptop** with a PWM-controllable CPU fan
- **Smartphone** with a microphone for recording (Android/iOS)

### Software
- **Windows 10/11** (x64)
- **Python** ≥ 3.9
- **LibreHardwareMonitor** ≥ 0.9.3

### Python Packages
```
pip install pythonnet numpy scipy matplotlib
```

## Setup

1. **Install LibreHardwareMonitor** — extract to `C:\Fansmitter\lhm\`
2. **Run it as Administrator** and verify your CPU fan is listed
3. **Note the fan name** (e.g. `Fan #2`) — update `FAN_NAME` in the scripts
4. **Install Python packages:**
   ```
   pip install pythonnet numpy scipy matplotlib
   ```

### Project Structure
```
Fansmitter/
├── fansmitter_transmit.py   # Transmitter — controls fan speed
├── fansmitter_decode.py     # Decoder — DSP analysis of WAV
├── fan_test.py              # Fan control verification
├── generate_synthetic.py    # Synthetic test recording generator
├── lhm/                     # LibreHardwareMonitor DLLs
│   └── LibreHardwareMonitorLib.dll
└── recordings/              # WAV recordings
```

## Usage

### 1. Verify Fan Control

```
python fan_test.py
```

Confirms the fan responds to software speed commands and reports RPM.

### 2. Transmit Data

```
python fansmitter_transmit.py
```

- Start recording on your phone (WAV format, mic pointed at fan, 0.5–1.5m away)
- Press **ENTER** when recording
- Wait for transmission to complete (~15 min for a 6-character string)
- Stop recording and transfer the WAV to `recordings/`

**Configuration** (edit in `fansmitter_transmit.py`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `FAN_NAME` | `"Fan #2"` | Fan name in LibreHardwareMonitor |
| `PCT_BIT_0` | `10` | Fan speed % for bit 0 |
| `PCT_BIT_1` | `100` | Fan speed % for bit 1 |
| `BIT_DURATION` | `10` | Stable signal duration (seconds) |
| `STABILIZE_TIME` | `3` | Fan spin-up time (seconds) |
| `SECRET` | `"EH2026"` | Data to exfiltrate |

### 3. Decode Recording

```
python fansmitter_decode.py recordings\recording1.wav
```

**Configuration** (must match transmitter — edit in `fansmitter_decode.py`):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `BIT_DURATION` | `10` | Must match transmitter |
| `STABILIZE_TIME` | `3` | Must match transmitter |
| `F0_HZ` | `70` | Frequency for bit 0 |
| `F1_HZ` | `140` | Frequency for bit 1 |
| `BANDWIDTH` | `30` | Bandpass filter bandwidth (±Hz) |



| Limitation | Impact |
|------------|--------|
| **Throughput** | ~0.077 bit/s — 15+ minutes for 6 characters |
| **Range** | < 2 meters, same room only |
| **Noise sensitivity** | Ambient noise degrades signal quality |
| **Hardware dependent** | Not all fans produce clean tonal frequencies |
| **Fan inertia** | 2–5s spin-up time reduces effective bit rate |
| **No error correction** | Single-bit errors cause checksum failure |
| **Lossless audio required** | MP3/AAC compression destroys low frequencies |

## Defenses

- **RPM monitoring** — detect abnormal fan speed patterns
- **PWM locking** — disable software fan control in BIOS
- **Acoustic isolation** — soundproofed server rooms
- **Device policy** — ban recording devices in secure areas
- **White noise generators** — mask acoustic signals

## License

This project is for educational and research purposes only.

## References

- Guri, M., Monitz, M., Mirski, Y., Elovici, Y. (2016). *Fansmitter: Acoustic Data Exfiltration from (Speakerless) Air-Gapped Computers*. arXiv:1606.05915
- [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor)
