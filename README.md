# Fedora Jam — Audio Configuration Tools

This package provides small user-facing utilities to help configure PipeWire and JACK-style
audio settings on Fedora Jam systems. The tools are intended to make it easy to select
low-latency-friendly settings for interactive audio work (music production, live performance,
and pro audio testing).

Included utilities
- `fedorajam-audio-config` — a simple graphical configuration utility for common
  PipeWire/JACK preferences and system tweaks useful for low-latency audio.
- `fedorajam-pwjack-config` — a minimal command-line helper that writes a profile file to
  `/etc/profile.d/fedorajam-pwjack.sh` to set PipeWire quantum and sample rate.

Usage

- Graphical: run `fedorajam-audio-config` from your desktop menu or terminal. It exposes
  common settings and actions for tuning a desktop for low-latency audio.

- Command-line: `fedorajam-pwjack-config BUFFERSIZE SAMPLERATE`
  - `BUFFERSIZE` must be one of: 16, 32, 64, 128, 256, 512, 1024, 2048, 4096
  - `SAMPLERATE` must be one of: 22050, 32000, 44100, 48000, 88200, 96000, 192000
  Example: `sudo fedorajam-pwjack-config 1024 48000` — on success this writes
  `/etc/profile.d/fedorajam-pwjack.sh` and advises you to log out and back in.

Installation

Install the RPM built from this package (noarch):

```
sudo dnf install ./fedora-jam-audio-config-<version>.noarch.rpm
```

Files installed
- `/usr/bin/fedorajam-audio-config` (graphical helper)
- `/usr/sbin/fedorajam-pwjack-config` (command-line helper)
- systemd user unit files to assist with session-time services
- desktop entry for the GUI

Notes and guidance
- These tools are small helpers — they do not replace careful system tuning for professional
  audio work. Use them to simplify common tasks such as selecting a consistent PipeWire
  quantum and sample rate and enabling recommended session services.
- The `fedorajam-pwjack-config` script writes a file into `/etc/profile.d`; a user must
  re-login for the environment changes to take effect.

Troubleshooting
- If a setting does not appear to take effect, ensure you logged out and back in, or
  restart the relevant session services.
- Verify that `/etc/profile.d/fedorajam-pwjack.sh` exists and contains the expected
  `PIPEWIRE_QUANTUM` value.

License

This package is distributed under the terms of the `GPL-2.0-or-later` license. See
the `COPYING` file for the full license text.
