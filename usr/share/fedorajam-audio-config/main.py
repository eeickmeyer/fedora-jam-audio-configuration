"""Fedora Jam Audio Configuration — main entry point."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Ensure the package directory is importable when launched from /usr/bin
_pkg_dir = Path(__file__).resolve().parent
if str(_pkg_dir) not in sys.path:
    sys.path.insert(0, str(_pkg_dir))

from backend.audio_config import (  # noqa: E402
    APP_TITLE,
    JACK_BOOL_PARAMS,
    JACK_PARAM_DESCRIPTIONS,
    VALID_BUFFER_SIZES,
    VALID_SAMPLE_RATES,
    SELF_CONNECT_DESCRIPTIONS,
    SELF_CONNECT_MODES,
    BootParams,
    FFADODevice,
    JackConfig,
    cli_dummy_start,
    cli_dummy_stop,
    cli_startup,
    cli_write_params,
    dummy_device_active,
    dummy_device_disable,
    dummy_device_enable,
    dummy_device_start,
    dummy_device_stop,
    ffado_pw_configured,
    ffado_tools_installed,
    firewire_controller_present,
    get_default_quantum,
    get_user_quantum,
    has_gnome_pw_extension,
    has_plasma_pw_widget,
    list_ffado_devices,
    read_boot_params,
    read_jack_config,
    remove_ffado_pw_config,
    validate_quantum,
    write_boot_params,
    write_ffado_pw_config,
    write_jack_config,
)
from ui.base import AudioConfigUI, ChecklistItem, ComboItem  # noqa: E402
from i18n import _  # noqa: E402


# ======================================================================
# Desktop-environment detection & toolkit selection
# ======================================================================


def _detect_toolkit() -> str:
    """Return ``"qt"`` or ``"gtk"`` based on the running DE.

    Qt desktops:  KDE Plasma (Fedora KDE Spin, Fedora Jam,
                  Fedora Astronomy, Fedora Scientific),
                  LXQt (Fedora LXQt Spin)
    GTK desktops: GNOME (Fedora Workstation, Fedora Design Suite,
                  Fedora Games, Fedora Python Classroom),
                  Xfce (Fedora Xfce Spin, Fedora Security Lab),
                  MATE (Fedora MATE-Compiz Spin),
                  Budgie (Fedora Budgie Spin),
                  Cinnamon (Fedora Cinnamon Spin),
                  LXDE (Fedora LXDE Spin),
                  Sway (Fedora Sway Spin), i3 (Fedora i3 Spin)
    """
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    if any(tok in desktop for tok in ("kde", "plasma", "lxqt")):
        return "qt"
    if "plasma" in session or "lxqt" in session:
        return "qt"
    return "gtk"


def _create_ui() -> AudioConfigUI:
    """Instantiate the correct UI backend, with fallback."""
    preferred = _detect_toolkit()
    if preferred == "qt":
        try:
            from ui.qt_ui import QtUI
            ui = QtUI()
            ui.init()
            return ui
        except ImportError:
            pass  # fall through to GTK
    try:
        from ui.gtk_ui import GtkUI
        ui = GtkUI()
        ui.init()
        return ui
    except ImportError:
        pass
    # Last resort: try Qt even on non-KDE desktops
    try:
        from ui.qt_ui import QtUI
        ui = QtUI()
        ui.init()
        return ui
    except ImportError:
        print(
            _("ERROR: Neither GTK 4 (python3-gi + gir1.2-adw-1) nor "
              "PyQt6 (python3-pyqt6) is available."),
            file=sys.stderr,
        )
        sys.exit(1)


# ======================================================================
# Application controller
# ======================================================================


def _configure_audio(ui: AudioConfigUI) -> None:
    """The 'Configure Current Audio Configuration' flow."""

    # --- Check for desktop-specific PipeWire widgets ---
    has_pw_widget = has_plasma_pw_widget()
    has_gnome_ext = has_gnome_pw_extension()

    if has_pw_widget:
        ui.show_info(
            APP_TITLE,
            _("You have the PipeWire Settings Plasma Widget installed.\n"
              "Use that to change the PipeWire Quantum & Sample Rate.\n"
              "(This is recommended if you are using KDE Plasma Desktop)\n"
              "You can find it in your system tray or add it to your panel."),
        )

    elif has_gnome_ext:
        ui.show_info(
            APP_TITLE,
            _("You have the PipeWire Settings GNOME Shell Extension installed.\n"
              "Use that to change the PipeWire Quantum & Sample Rate.\n"
              "(This is recommended if you are using GNOME Shell)\n"
              "You can find it in Extension Manager if it's not already\n"
              "on your panel."),
        )

    # --- Buffer / sample rate dropdowns ---
    default_buf, default_rate = get_default_quantum()
    user_buf, user_rate = get_user_quantum()

    if has_pw_widget or has_gnome_ext:
        # Widget / extension handles quantum; keep current values.
        buf, rate = user_buf, user_rate
    else:
        combo_result = ui.show_combo_dialog(
            APP_TITLE,
            _("Select the Buffer Size and Sample Rate for PipeWire\n"
              "Quantum configuration.\n\n"
              "If you're not sure what to do here, it's best to leave\n"
              "the current settings in place.\n\n"
              "Note: Defaults are controlled via the\n"
              "fedorajam-pwjack-config terminal command"),
            combos=[
                ComboItem(
                    label=_("Buffer Size"),
                    options=[str(s) for s in VALID_BUFFER_SIZES],
                    default=str(user_buf),
                ),
                ComboItem(
                    label=_("Sample Rate (Hz)"),
                    options=[str(r) for r in VALID_SAMPLE_RATES],
                    default=str(user_rate),
                ),
            ],
            ok_label=_("Next"),
            cancel_label=_("Cancel"),
        )

        if combo_result is None:
            return  # user cancelled

        buf, rate = int(combo_result[0]), int(combo_result[1])

    # --- JACK boolean parameters ---
    cfg = read_jack_config()
    jack_items = [
        ChecklistItem(
            key=param,
            label=param,
            description=JACK_PARAM_DESCRIPTIONS[param],
            checked=cfg.bool_params.get(param, False),
        )
        for param in JACK_BOOL_PARAMS
    ]

    selected = ui.show_checklist(
        APP_TITLE,
        _("Select which JACK plugin options you would like"),
        jack_items,
        ok_label=_("Next"),
        cancel_label=_("Cancel"),
    )
    if selected is None:
        return

    new_bool_params = {p: (p in selected) for p in JACK_BOOL_PARAMS}

    # --- Self-connect mode ---
    sc_items = [
        ChecklistItem(
            key=mode,
            label=mode,
            description=SELF_CONNECT_DESCRIPTIONS[mode],
            checked=(mode == cfg.self_connect_mode),
        )
        for mode in SELF_CONNECT_MODES
    ]

    sc_mode = ui.show_radiolist(
        APP_TITLE,
        _("Select the self-connect mode. If you don't know what "
          "this is, leave it alone."),
        sc_items,
        ok_label=_("Apply"),
        cancel_label=_("Cancel"),
    )
    if sc_mode is None:
        return

    # --- Write configuration ---
    new_cfg = JackConfig(
        buffer_size=buf,
        sample_rate=rate,
        show_monitor=new_bool_params["jack.show-monitor"],
        merge_monitor=new_bool_params["jack.merge-monitor"],
        show_midi=new_bool_params["jack.show-midi"],
        short_name=new_bool_params["jack.short-name"],
        self_connect_mode=sc_mode,
    )
    widget_manages_quantum = has_pw_widget or has_gnome_ext
    write_jack_config(new_cfg, set_quantum=not widget_manages_quantum)

    # Restart dummy if active
    if dummy_device_active():
        subprocess.run(
            ["systemctl", "--user", "restart",
             "fedorajam-dummy-audio.service"]
        )

    if widget_manages_quantum:
        ui.show_info(
            APP_TITLE,
            _("JACK configuration applied.\n\n"
              "Buffer and Sample Rate are managed by your\n"
              "desktop widget / extension."),
        )
    else:
        ui.show_info(
            APP_TITLE,
            _("Configuration applied.\n\n"
              "Buffer Size: {buf}\n"
              "Sample Rate: {rate} Hz").format(buf=buf, rate=rate),
        )


def _change_boot_params(ui: AudioConfigUI) -> None:
    """The 'Change Kernel Boot Parameters' flow."""
    params = read_boot_params()

    items = [
        ChecklistItem(
            key="preempt=full",
            label="preempt=full",
            description=params.PARAM_DESCRIPTIONS["preempt=full"],
            checked=params.preempt_full,
        ),
        ChecklistItem(
            key="threadirqs",
            label="threadirqs",
            description=params.PARAM_DESCRIPTIONS["threadirqs"],
            checked=params.threadirqs,
        ),
        ChecklistItem(
            key="rcu_nocbs=all",
            label="rcu_nocbs=all",
            description=params.PARAM_DESCRIPTIONS["rcu_nocbs=all"],
            checked=params.rcu_nocbs_all,
        ),
        ChecklistItem(
            key="nohz_full=all",
            label="nohz_full=all",
            description=params.PARAM_DESCRIPTIONS["nohz_full=all"],
            checked=params.nohz_full_all,
        ),
    ]

    selected = ui.show_checklist(
        APP_TITLE,
        _("Select which kernel boot parameters you would like. "
          "Default is first three."),
        items,
        ok_label=_("Apply (Password Required)"),
        cancel_label=_("Back"),
    )
    if selected is None:
        return

    new_params = BootParams(
        preempt_full="preempt=full" in selected,
        threadirqs="threadirqs" in selected,
        rcu_nocbs_all="rcu_nocbs=all" in selected,
        nohz_full_all="nohz_full=all" in selected,
    )

    ok = ui.show_progress(
        APP_TITLE,
        _("Applying boot parameters…"),
        lambda: write_boot_params(new_params),
    )
    if ok:
        ui.show_info(
            APP_TITLE,
            _("You must restart your computer for these changes "
              "to take effect."),
        )
    else:
        ui.show_error(
            APP_TITLE,
            _("An error has occurred or action was cancelled."),
        )


def _toggle_dummy(ui: AudioConfigUI) -> None:
    """Start / stop the dummy audio device."""
    active = dummy_device_active()

    if not active:
        text = _(
            "Sometimes, you may wish to enable a dummy audio device for "
            "your system audio or an audio application so that you don't "
            "inadvertently feed that to your main output or draw from your "
            "main input. This can be useful when you wish to send a music "
            "application to your DAW or other mixer without sending to "
            "your main system output. There may be other workflow reasons "
            "as well.\n\nDo you wish to start a stereo dummy audio device?"
        )
        if ui.show_question(
            APP_TITLE, text,
            ok_label=_("Yes"),
            cancel_label=_("Go Back"),
        ):
            dummy_device_start()
            if ui.show_question(
                APP_TITLE,
                _("Would you like the dummy audio device to start "
                  "at login?"),
            ):
                dummy_device_enable()
            else:
                dummy_device_disable()
    else:
        if ui.show_question(
            APP_TITLE,
            _("Would you like to stop the dummy audio device?"),
        ):
            dummy_device_stop()
            if ui.show_question(
                APP_TITLE,
                _("Would you like the dummy audio device to start "
                  "at login?"),
            ):
                dummy_device_enable()
            else:
                dummy_device_disable()


def _configure_firewire(ui: AudioConfigUI) -> None:
    """Configure or remove FireWire (FFADO) audio support in PipeWire."""

    # If already configured, offer to reconfigure or remove
    if ffado_pw_configured():
        keep = ui.show_question(
            APP_TITLE,
            _("A FireWire (FFADO) PipeWire configuration already exists.\n\n"
              "Would you like to reconfigure it?\n"
              "(Choose 'No' to remove the existing configuration)"),
            ok_label=_("Reconfigure"),
            cancel_label=_("Remove"),
        )
        if not keep:
            remove_ffado_pw_config()
            ui.show_info(
                APP_TITLE,
                _("FireWire (FFADO) PipeWire configuration removed.\n"
                  "PipeWire has been restarted."),
            )
            return

    # Ensure ffado package is installed
    if not ffado_tools_installed():
        install = ui.show_question(
            APP_TITLE,
            _("FireWire (FFADO) audio support requires the 'ffado' "
              "package to be installed.\n\n"
              "Would you like to install it now?"),
            ok_label=_("Install"),
            cancel_label=_("Cancel"),
        )
        if not install:
            return
        ok = ui.show_progress(
            APP_TITLE,
            _("Installing ffado\u2026"),
            lambda: subprocess.run(
                ["pkexec", "dnf", "install", "-y", "ffado", "libffado"]
            ),
        )
        if not ok:
            ui.show_error(APP_TITLE, _("Failed to install ffado."))
            return

    # Enumerate connected devices
    devices = list_ffado_devices()
    if not devices:
        ui.show_warning(
            APP_TITLE,
            _("No FireWire audio devices were detected.\n\n"
              "Make sure your FireWire device is connected and powered on, "
              "and that the firewire_ohci and firewire_core kernel modules "
              "are loaded."),
        )
        return

    # Device selection (skip radio if only one device)
    if len(devices) == 1:
        device_index = 0
    else:
        device_items = [
            ChecklistItem(
                key=str(dev.index),
                label=dev.display_name,
                description=_("GUID: {guid}").format(guid=dev.guid),
                checked=(dev.index == 0),
            )
            for dev in devices
        ]
        selected_key = ui.show_radiolist(
            APP_TITLE,
            _("Select the FireWire audio device to use with PipeWire:"),
            device_items,
            ok_label=_("Next"),
            cancel_label=_("Cancel"),
        )
        if selected_key is None:
            return
        device_index = int(selected_key)

    # Buffer size / sample rate
    combo_result = ui.show_combo_dialog(
        APP_TITLE,
        _("Select the Buffer Size and Sample Rate for the FireWire device.\n\n"
          "Note: Many FireWire devices require a buffer size of 256 or larger."),
        combos=[
            ComboItem(
                label=_("Buffer Size"),
                options=[str(s) for s in VALID_BUFFER_SIZES],
                default="256",
            ),
            ComboItem(
                label=_("Sample Rate (Hz)"),
                options=[str(r) for r in VALID_SAMPLE_RATES],
                default="48000",
            ),
        ],
        ok_label=_("Apply"),
        cancel_label=_("Cancel"),
    )
    if combo_result is None:
        return

    buf, rate = int(combo_result[0]), int(combo_result[1])

    write_ffado_pw_config(buf, rate, device_index)

    ui.show_info(
        APP_TITLE,
        _("FireWire audio configured.\n\n"
          "Device:      {device}\n"
          "Buffer Size: {buf}\n"
          "Sample Rate: {rate} Hz\n\n"
          "PipeWire has been restarted.").format(
            device=devices[device_index].display_name,
            buf=buf,
            rate=rate,
        ),
    )


# ======================================================================
# Main menu loop
# ======================================================================


def _main_loop(ui: AudioConfigUI) -> None:
    """Run the main menu in a loop until the user closes it."""

    while True:
        active = dummy_device_active()
        dummy_label = (
            _("STOP Dummy Audio Device") if active
            else _("START Dummy Audio Device")
        )

        fw_present = firewire_controller_present() or ffado_pw_configured()
        fw_label = (
            _("Reconfigure / Remove FireWire (FFADO) Audio Device")
            if ffado_pw_configured()
            else _("Configure FireWire (FFADO) Audio Device")
        )

        items = [
            ChecklistItem(
                key="configure",
                label=_("Configure Current Audio Configuration"),
                description="",
            ),
            ChecklistItem(
                key="boot",
                label=_("Change Kernel Boot Parameters"),
                description="",
            ),
            ChecklistItem(
                key="dummy",
                label=dummy_label,
                description="",
            ),
        ]

        if fw_present:
            items.append(
                ChecklistItem(
                    key="firewire",
                    label=fw_label,
                    description="",
                )
            )

        choice = ui.show_radiolist(
            APP_TITLE,
            _("What would you like to do?"),
            items,
            ok_label=_("Continue"),
            cancel_label=_("Close"),
        )

        if choice is None:
            return  # user closed

        if choice == "configure":
            _configure_audio(ui)
        elif choice == "boot":
            _change_boot_params(ui)
        elif choice == "dummy":
            _toggle_dummy(ui)
        elif choice == "firewire":
            _configure_firewire(ui)


# ======================================================================
# CLI entry points (no GUI)
# ======================================================================


def _handle_cli(args: list[str]) -> int:
    """Handle CLI-only sub-commands that need no UI.  Returns exit code."""
    cmd = args[0] if args else ""

    if cmd == "startup":
        cli_startup()
        return 0

    if cmd == "dummystart":
        cli_dummy_start()
        return 0

    if cmd == "dummystop":
        cli_dummy_stop()
        return 0

    if cmd == "writeparams":
        # args: writeparams <unused> [param1 param2 ...]
        cli_write_params(args[2:] if len(args) > 2 else [])
        return 0

    return -1  # not a CLI command


# ======================================================================
# Entry point
# ======================================================================


def main() -> None:
    args = sys.argv[1:]

    # CLI sub-commands run without a toolkit
    if args:
        rc = _handle_cli(args)
        if rc >= 0:
            sys.exit(rc)

    # GUI path
    ui = _create_ui()
    _main_loop(ui)
    ui.quit()


if __name__ == "__main__":
    main()
