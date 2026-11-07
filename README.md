# Fedora Jam — Audio Configuration Tools

A graphical and command-line toolset for tuning PipeWire and JACK audio settings on
Fedora Jam (and any Fedora spin). Designed for musicians, engineers, and anyone who needs
reliable low-latency audio.

---

## Features

The `fedorajam-audio-config` GUI provides a single tabbed panel for audio, kernel,
dummy-device, and FireWire configuration:

### Configure PipeWire / JACK Settings
- Select the **buffer size** and **sample rate** (PipeWire quantum) for your session.
  - If the **PipeWire Settings Plasma Widget** (KDE) or the **PipeWire Settings GNOME
    Shell Extension** is detected, the GUI defers quantum management to that widget and
    disables the buffer/rate controls.
- Toggle JACK plugin options:
  - `jack.show-monitor` — expose the JACK Monitor client and its ports
  - `jack.merge-monitor` — merge capture and monitor ports on the same device client
  - `jack.show-midi` — expose JACK MIDI clients and ports
  - `jack.short-name` — use shorter names for device clients
- Select the **self-connect mode** for the JACK plugin
  (`allow`, `fail-external`, `ignore-external`, `fail-all`, `ignore-all`).

Settings are written to `~/.config/pipewire/jack.conf.d/fedorajam.conf` and applied
immediately by restarting the relevant PipeWire services.
PipeWire-JACK package availability remains managed by Fedora and is not changed by the
panel.

### Kernel Boot Parameters
Manage real-time–friendly kernel parameters written to
`/etc/default/grub.d/fedorajam.cfg` (applied via `grub2-mkconfig` with `pkexec`):

| Parameter | Effect |
|---|---|
| `preempt=full` | Fully preemptible kernel — best for low-latency workloads |
| `threadirqs` | Forces interrupt handlers into threaded context, reducing xruns |
| `rcu_nocbs=all` | Offloads RCU callbacks to dedicated threads — improves RT performance |
| `nohz_full=all` | Reduces timer noise for latency-critical workloads |

A reboot is required for these changes to take effect.

### Dummy Audio Device
Start or stop a **stereo PipeWire dummy audio sink/source** for use cases where you want
to route audio from an application without sending it to physical outputs (e.g. routing
a DAW or music app into another mixer or recorder). You can also enable or disable the
dummy device automatically at login via the associated systemd user service.

### FireWire (FFADO) Audio Device
Configure a FireWire audio interface to work with PipeWire via the FFADO library:
- Detects connected FireWire devices using `ffado-test`.
- Prompts to install the `ffado` / `libffado` packages if they are not present.
- Select device, buffer size, and sample rate; writes a PipeWire context configuration
  and restarts PipeWire automatically.
- Existing configurations can be reconfigured or removed.

---

## Toolkit Detection

The GUI automatically selects the appropriate widget toolkit based on the running desktop:

| Desktop | Toolkit |
|---|---|
| KDE Plasma, LXQt | **Qt 6** (PyQt6) |
| GNOME, Xfce, MATE, Budgie, Cinnamon, Sway, i3, LXDE, … | **GTK 4 + libadwaita** (PyGObject) |

If the preferred toolkit is unavailable, the other is tried automatically.

---

## Utilities

### `fedorajam-audio-config` (GUI)

Launch from your desktop application menu or from a terminal:

```
fedorajam-audio-config
```

Internal CLI sub-commands (used by systemd services, not normally called directly):

| Sub-command | Purpose |
|---|---|
| `startup` | Apply saved JACK configuration at session start |
| `dummystart` | Load the dummy audio module into PipeWire |
| `dummystop` | Unload the dummy audio module |
| `writeparams [param …]` | Write selected kernel params to the GRUB drop-in |

### `fedorajam-pwjack-config` (command-line)

A root-level helper that writes `/etc/profile.d/fedorajam-pwjack.sh`, setting the
system-wide default PipeWire quantum and sample rate:

```
sudo fedorajam-pwjack-config BUFFERSIZE SAMPLERATE
```

Valid values:

| Argument | Accepted values |
|---|---|
| `BUFFERSIZE` | 16, 32, 64, 128, 256, 512, 1024, 2048, 4096 |
| `SAMPLERATE` | 22050, 32000, 44100, 48000, 88200, 96000, 192000 |

Example:

```
sudo fedorajam-pwjack-config 1024 48000
```

Log out and back in for the environment change to take effect. The GUI defers to this
file for its "system default" quantum display.

---

## systemd User Services

Two user-session services are installed and preset to start automatically:

| Unit | Description |
|---|---|
| `fedorajam-pwconfig-start.service` | Runs `fedorajam-audio-config startup` after PipeWire starts; applies saved JACK settings |
| `fedorajam-dummy-audio.service` | Manages the dummy audio device; started/stopped by the GUI |

Both units are managed via `systemctl --user`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `pipewire`, `pipewire-utils` | Audio server and utilities |
| `pulseaudio-utils` | `pactl` used for dummy device management |
| `python3 >= 3.9` | Runtime for all Python tools |
| `python3-gobject` | GTK 4 UI (on GNOME and other GTK desktops) |
| `python3-PyQt6` | Qt 6 UI (on KDE Plasma and LXQt) |
| `polkit` | Privilege escalation for GRUB / kernel parameter changes |
| `grub2-common`, `bash` | Boot parameter management |

At least one of `python3-gobject` or `python3-PyQt6` must be present.

---

## Installation

Install the pre-built RPM (noarch):

```
sudo dnf install ./fedora-jam-audio-config-<version>.noarch.rpm
```

The `%post` scriptlet automatically runs `fedorajam-pwjack-config 1024 48000` to write
an initial quantum profile if one does not already exist.

### Files installed

| Path | Description |
|---|---|
| `/usr/bin/fedorajam-audio-config` | Graphical configuration tool |
| `/usr/sbin/fedorajam-pwjack-config` | System quantum/sample-rate helper |
| `/usr/share/fedorajam-audio-config/` | Python application package |
| `/usr/lib/systemd/user/*.service` | User session services |
| `/usr/lib/systemd/user-preset/90_fedorajam-pwconfig-start.preset` | Service preset |
| `/usr/share/applications/fedorajam-audio-config.desktop` | Desktop entry |
| `/usr/share/locale/*/LC_MESSAGES/fedorajam-audio-config.mo` | Translations |
| `/usr/share/man/man1/` | Man pages for both tools |

---

## Translations

Translations are managed in the `po/` directory using standard GNU gettext. To add or
update a translation, edit the appropriate `.po` file and run `make` in `po/`.

Currently translated: Arabic, Czech, German, Spanish, Estonian, French, Hindi, Italian,
Japanese, Korean, Lithuanian, Latvian, Dutch, Polish, Brazilian Portuguese, Portuguese,
Russian, Slovak, Turkish, Ukrainian, Simplified Chinese.

---

## Troubleshooting

- **Setting does not take effect after applying** — log out and back in, or restart the
  relevant user service: `systemctl --user restart fedorajam-pwconfig-start.service`
- **Check the active quantum** — verify `/etc/profile.d/fedorajam-pwjack.sh` contains
  the expected `PIPEWIRE_QUANTUM` value.
- **JACK config location** — user overrides live in
  `~/.config/pipewire/jack.conf.d/fedorajam.conf`.
- **Kernel parameters** — check `/etc/default/grub.d/fedorajam.cfg` and confirm
  `grub2-mkconfig` was run successfully (the GUI does this automatically via `pkexec`).

---

## License

`GPL-2.0-or-later` — see the `COPYING` file for the full text.
