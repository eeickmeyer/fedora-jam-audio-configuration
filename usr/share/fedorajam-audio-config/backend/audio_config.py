"""Audio configuration backend for Fedora Jam."""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from i18n import _

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_BUFFER_SIZES = (16, 32, 64, 128, 256, 512, 1024, 2048, 4096)
VALID_SAMPLE_RATES = (22050, 32000, 44100, 48000, 88200, 96000, 192000)

JACK_BOOL_PARAMS = (
    "jack.show-monitor",
    "jack.merge-monitor",
    "jack.show-midi",
    "jack.short-name",
)

SELF_CONNECT_MODES = (
    "allow",
    "fail-external",
    "ignore-external",
    "fail-all",
    "ignore-all",
)

SELF_CONNECT_DESCRIPTIONS: dict[str, str] = {
    "allow": _("Don't restrict self connect requests (default)"),
    "fail-external": _("Fail self connect requests to external ports only"),
    "ignore-external": _("Ignore self connect requests to external ports only"),
    "fail-all": _("Fail all self connect requests"),
    "ignore-all": _("Ignore all self connect requests"),
}

JACK_PARAM_DESCRIPTIONS: dict[str, str] = {
    "jack.show-monitor": _("Show the Monitor client and its ports."),
    "jack.merge-monitor": _(
        "Exposes the capture ports and monitor ports on the same JACK device client."
    ),
    "jack.show-midi": _("Show the MIDI clients and their ports."),
    "jack.short-name": _("Use shorter names for the device client name."),
}

ICON_PATH = "/usr/share/icons/hicolor/scalable/apps/start-here.svg"

APP_TITLE = _("Fedora Jam Audio Configuration")

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class JackConfig:
    """Parsed JACK configuration from fedorajam.conf."""

    buffer_size: int = 1024
    sample_rate: int = 48000
    show_monitor: bool = True
    merge_monitor: bool = True
    show_midi: bool = True
    short_name: bool = True
    self_connect_mode: str = "allow"

    @property
    def bool_params(self) -> dict[str, bool]:
        return {
            "jack.show-monitor": self.show_monitor,
            "jack.merge-monitor": self.merge_monitor,
            "jack.show-midi": self.show_midi,
            "jack.short-name": self.short_name,
        }

    @bool_params.setter
    def bool_params(self, mapping: dict[str, bool]) -> None:
        self.show_monitor = mapping.get("jack.show-monitor", self.show_monitor)
        self.merge_monitor = mapping.get("jack.merge-monitor", self.merge_monitor)
        self.show_midi = mapping.get("jack.show-midi", self.show_midi)
        self.short_name = mapping.get("jack.short-name", self.short_name)


@dataclass
class BootParams:
    """Kernel boot parameters."""

    preempt_full: bool = False
    threadirqs: bool = False
    rcu_nocbs_all: bool = False
    nohz_full_all: bool = False

    PARAM_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "preempt=full": "preempt_full",
            "threadirqs": "threadirqs",
            "rcu_nocbs=all": "rcu_nocbs_all",
            "nohz_full=all": "nohz_full_all",
        },
        init=False,
        repr=False,
    )

    PARAM_DESCRIPTIONS: dict[str, str] = field(
        default_factory=lambda: {
            "preempt=full": _(
                "Makes the kernel fully-preemptible, best for lowlatency workloads"
            ),
            "threadirqs": _(
                "Forces interrupt handlers to run in a threaded context, "
                "reducing buffer xruns"
            ),
            "rcu_nocbs=all": _(
                "Offloads Read-Copy-Update (RCU) callbacks from all CPUs to "
                "dedicated kernel threads, improves real-time performance."
            ),
            "nohz_full=all": _(
                "Reduces noise in latency critical applications such as "
                "virtualization"
            ),
        },
        init=False,
        repr=False,
    )

    def as_dict(self) -> dict[str, bool]:
        return {
            param: getattr(self, attr) for param, attr in self.PARAM_MAP.items()
        }

    def as_string_list(self) -> list[str]:
        return [p for p, enabled in self.as_dict().items() if enabled]

    @classmethod
    def from_config(cls, line: str) -> BootParams:
        obj = cls()
        for param, attr in obj.PARAM_MAP.items():
            if param in line:
                setattr(obj, attr, True)
        return obj


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def validate_quantum(buffer_size: int, sample_rate: int) -> bool:
    """Return True if buffer_size and sample_rate are valid."""
    return buffer_size in VALID_BUFFER_SIZES and sample_rate in VALID_SAMPLE_RATES


def _user_conf_path() -> Path:
    """Return the path to the user PipeWire JACK configuration file."""
    return (
        Path.home() / ".config" / "pipewire" / "jack.conf.d" / "fedorajam.conf"
    )


def _read_conf_value(key: str) -> str | None:
    """Read a single value from the user PipeWire JACK configuration."""
    conf = _user_conf_path()
    if not conf.exists():
        return None
    for line in conf.read_text().splitlines():
        if key in line and "=" in line:
            return line.split("=", 1)[1].strip()
    return None


# ---------------------------------------------------------------------------
# System queries
# ---------------------------------------------------------------------------


def get_default_quantum() -> tuple[int, int]:
    """Return (buffer, rate) from /etc/profile.d/fedorajam-pwjack.sh."""
    sh = Path("/etc/profile.d/fedorajam-pwjack.sh")
    if sh.exists():
        for line in sh.read_text().splitlines():
            m = re.search(r"PIPEWIRE_QUANTUM\s*=\s*[\"']?(\d+)/(\d+)", line)
            if m:
                return int(m.group(1)), int(m.group(2))
    return 1024, 48000


def get_user_quantum() -> tuple[int, int]:
    """Return (buffer, rate) from the user config, falling back to defaults."""
    latency = _read_conf_value("node.latency")
    if latency:
        parts = latency.strip('"').strip("'").split("/")
        if len(parts) == 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass
    return get_default_quantum()


def read_jack_config() -> JackConfig:
    """Parse the full JACK config from disk."""
    cfg = JackConfig()
    buf, rate = get_user_quantum()
    cfg.buffer_size = buf
    cfg.sample_rate = rate

    for param in JACK_BOOL_PARAMS:
        val = _read_conf_value(param)
        if val is not None:
            attr = param.replace("jack.", "").replace("-", "_")
            setattr(cfg, attr, val == "true")

    scm = _read_conf_value("jack.self-connect-mode")
    if scm and scm in SELF_CONNECT_MODES:
        cfg.self_connect_mode = scm

    return cfg


def has_user_conf() -> bool:
    return _user_conf_path().exists()


# ---------------------------------------------------------------------------
# Desktop-extension detection
# ---------------------------------------------------------------------------


def has_plasma_pw_widget() -> bool:
    paths = [
        Path("/usr/share/plasma/plasmoids/com.github.magillos.pipewiresettings"),
        Path.home()
        / ".local/share/plasma/plasmoids/com.github.magillos.pipewiresettings",
    ]
    return any(p.exists() for p in paths)


def has_gnome_pw_extension() -> bool:
    ext = "pipewire-settings@gaheldev.github.com"
    paths = [
        Path(f"/usr/share/gnome-shell/extensions/{ext}"),
        Path.home() / f".local/share/gnome-shell/extensions/{ext}",
    ]
    return any(p.exists() for p in paths)


# ---------------------------------------------------------------------------
# Dummy audio device
# ---------------------------------------------------------------------------


def dummy_device_active() -> bool:
    """Return True if the dummy audio service is running."""
    res = subprocess.run(
        ["systemctl", "--user", "status", "fedorajam-dummy-audio.service"],
        capture_output=True,
        text=True,
    )
    for line in res.stdout.splitlines():
        if "active" in line.lower() and "dead" in line.lower():
            return False
    return res.returncode == 0


def dummy_device_start() -> None:
    subprocess.run(
        ["systemctl", "--user", "start", "fedorajam-dummy-audio.service"]
    )


def dummy_device_stop() -> None:
    subprocess.run(
        ["systemctl", "--user", "stop", "fedorajam-dummy-audio.service"]
    )


def dummy_device_enable() -> None:
    subprocess.run(
        ["systemctl", "--user", "enable", "fedorajam-dummy-audio.service"],
        stderr=subprocess.DEVNULL,
    )


def dummy_device_disable() -> None:
    subprocess.run(
        ["systemctl", "--user", "disable", "fedorajam-dummy-audio.service"],
        stderr=subprocess.DEVNULL,
    )


# ---------------------------------------------------------------------------
# Write configuration
# ---------------------------------------------------------------------------

_JACK_CONF_TEMPLATE = """\
#THIS FILE IS AUTOMATICALLY GENERATED BY Fedora Jam Audio Configuration
jack.properties = {{
    #rt.prio             = 88
    node.latency        = {buffer}/{rate}
    #node.lock-quantum   = true
    #node.force-quantum  = 0
    jack.show-monitor   = {show_monitor}
    jack.merge-monitor  = {merge_monitor}
    jack.show-midi      = {show_midi}
    jack.short-name     = {short_name}
    #jack.filter-name    = false
    #jack.filter-char    = " "
    #
    # allow:           Don't restrict self connect requests
    # fail-external:   Fail self connect requests to external ports only
    # ignore-external: Ignore self connect requests to external ports only
    # fail-all:        Fail all self connect requests
    # ignore-all:      Ignore all self connect requests
    #jack.self-connect-mode  = {self_connect}
    #jack.locked-process     = true
    #jack.default-as-system  = false
    #jack.fix-midi-events    = true
    jack.global-buffer-size = true
    #jack.passive-links      = false
    #jack.max-client-ports   = 768
    #jack.fill-aliases       = false
    #jack.writable-input     = false
    #jack.flag-midi2         = false
}}
"""

_JACK_CONF_TEMPLATE_NO_QUANTUM = """\
#THIS FILE IS AUTOMATICALLY GENERATED BY Fedora Jam Audio Configuration
#Buffer and sample rate are managed by the desktop widget / extension.
jack.properties = {{
    #rt.prio             = 88
    #node.lock-quantum   = true
    #node.force-quantum  = 0
    jack.show-monitor   = {show_monitor}
    jack.merge-monitor  = {merge_monitor}
    jack.show-midi      = {show_midi}
    jack.short-name     = {short_name}
    #jack.filter-name    = false
    #jack.filter-char    = " "
    #
    # allow:           Don't restrict self connect requests
    # fail-external:   Fail self connect requests to external ports only
    # ignore-external: Ignore self connect requests to external ports only
    # fail-all:        Fail all self connect requests
    # ignore-all:      Ignore all self connect requests
    #jack.self-connect-mode  = {self_connect}
    #jack.locked-process     = true
    #jack.default-as-system  = false
    #jack.fix-midi-events    = true
    jack.global-buffer-size = true
    #jack.passive-links      = false
    #jack.max-client-ports   = 768
    #jack.fill-aliases       = false
    #jack.writable-input     = false
    #jack.flag-midi2         = false
}}
"""


def write_jack_config(cfg: JackConfig, *, set_quantum: bool = True) -> None:
    """Write the JACK configuration and restart PipeWire.

    If *set_quantum* is False the config file is written **without**
    ``node.latency`` and the ``pw-metadata`` calls are skipped — the
    desktop widget / extension is responsible for quantum persistence.
    """
    conf_path = _user_conf_path()
    conf_path.parent.mkdir(parents=True, exist_ok=True)

    fmt_args = dict(
        show_monitor=str(cfg.show_monitor).lower(),
        merge_monitor=str(cfg.merge_monitor).lower(),
        show_midi=str(cfg.show_midi).lower(),
        short_name=str(cfg.short_name).lower(),
        self_connect=cfg.self_connect_mode,
    )

    if set_quantum:
        fmt_args["buffer"] = cfg.buffer_size
        fmt_args["rate"] = cfg.sample_rate
        text = _JACK_CONF_TEMPLATE.format(**fmt_args)
    else:
        text = _JACK_CONF_TEMPLATE_NO_QUANTUM.format(**fmt_args)

    conf_path.write_text(text)

    subprocess.run(["systemctl", "--user", "restart", "pipewire"])
    if set_quantum:
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-quantum", str(cfg.buffer_size)]
        )
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-rate", str(cfg.sample_rate)]
        )


# ---------------------------------------------------------------------------
# Boot parameters — Fedora uses grubby + grub2-mkconfig
# ---------------------------------------------------------------------------


def read_boot_params() -> BootParams:
    """Parse current boot parameters from /etc/fedorajamboot.cfg."""
    cfg_path = Path("/etc/fedorajamboot.cfg")
    if cfg_path.exists():
        line = cfg_path.read_text().strip()
        return BootParams.from_config(line)
    return BootParams()


def _update_grub() -> None:
    """Regenerate GRUB config (Fedora)."""
    subprocess.run(["grub2-mkconfig", "-o", "/boot/grub2/grub.cfg"])
    if Path("/sys/firmware/efi").is_dir():
        subprocess.run(["dnf", "reinstall", "-y", "grub2-common"])


def write_boot_params(params: BootParams) -> bool:
    """Write boot parameters via pkexec. Returns True on success."""
    param_list = params.as_string_list()
    cmd = [
        "pkexec",
        "/usr/bin/fedorajam-audio-config",
        "writeparams",
        "unused",  # placeholder for grub_cfg positional arg
    ] + param_list
    return subprocess.run(cmd).returncode == 0


# ---------------------------------------------------------------------------
# CLI-only operations (no GUI needed)
# ---------------------------------------------------------------------------


def cli_startup() -> None:
    """Run the 'startup' logic — set PipeWire quantum from config on login."""
    conf = _user_conf_path()
    if not conf.exists():
        buf, rate = get_default_quantum()
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-quantum", str(buf)]
        )
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-rate", str(rate)]
        )
        cfg = JackConfig(buffer_size=buf, sample_rate=rate)
        write_jack_config(cfg)
    else:
        buf, rate = get_user_quantum()
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-quantum", str(buf)]
        )
        subprocess.run(
            ["pw-metadata", "-n", "settings", "0",
             "clock.force-rate", str(rate)]
        )


def cli_dummy_start() -> None:
    subprocess.run([
        "pactl", "load-module", "module-null-sink",
        "media.class=Audio/Sink", "sink_name=Dummy", "channel_map=stereo",
    ])
    subprocess.run([
        "pactl", "load-module", "module-virtual-source",
        "media.class=Audio/Source", "source_name=Dummy", "channel_map=stereo",
    ])


def cli_dummy_stop() -> None:
    subprocess.run(["pactl", "unload-module", "module-null-sink"])
    subprocess.run(["pactl", "unload-module", "module-virtual-source"])


def cli_write_params(extra_params: list[str]) -> None:
    """Write grubby args and update GRUB (runs as root via pkexec)."""
    # Remove old params, then add new ones
    subprocess.run([
        "grubby", "--update-kernel=ALL",
        "--remove-args=preempt=full threadirqs rcu_nocbs=all nohz_full=all",
    ])
    if extra_params:
        subprocess.run([
            "grubby", "--update-kernel=ALL",
            "--args=" + " ".join(extra_params),
        ])

    _update_grub()

    # Persist to fedorajamboot.cfg
    Path("/etc/fedorajamboot.cfg").write_text(
        " ".join(extra_params) + "\n"
    )

    # Handle rEFInd if present
    refind = Path("/boot/refind_linux.conf")
    if refind.exists():
        text = refind.read_text()
        param_str = " ".join(extra_params)
        boot_line = ""
        for line in text.splitlines():
            if "standard" in line.lower():
                parts = line.split('"')
                if len(parts) >= 4:
                    boot_line = parts[3]
                break

        new_entry = (
            '"Boot with lowlatency options" '
            '"{boot_line} {params}"'
        ).format(boot_line=boot_line, params=param_str)

        if "lowlatency" in text.lower():
            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "lowlatency" in line.lower():
                    lines[i] = new_entry
            refind.write_text("\n".join(lines) + "\n")
        else:
            refind.write_text(new_entry + "\n" + text)
