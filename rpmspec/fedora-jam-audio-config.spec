Name:           fedora-jam-audio-config
Version:        2.0.1
Release:        1%{?dist}
Summary:        PipeWire-JACK audio configuration tool for Fedora Jam

BuildArch:      noarch

License:        GPL-2.0-or-later
URL:            https://pagure.io/fedora-jam-audio-configuration
Source0:        https://pagure.io/fedora-jam-audio-configuration/archive/%{version}/fedora-jam-audio-configuration-%{version}.tar.gz
BuildRequires:  systemd-rpm-macros
BuildRequires:  gettext
BuildRequires:  make
BuildRequires:  python3
Requires:       grub2-common bash polkit systemd pipewire pipewire-utils pulseaudio-utils
Requires:       python3 >= 3.9
Requires:       (python3-gobject or python3-PyQt6)

%description
A Python application providing a graphical interface for configuring
PipeWire-JACK settings and GRUB kernel parameters to optimize a system
for low-latency audio performance on Fedora Jam. The GUI supports both
GTK (via PyGObject) and Qt (via PyQt6) backends, and includes systemd
user services to apply audio configuration automatically at login.

%prep
%autosetup -C

%check
python3 -c "import py_compile; py_compile.compile('usr/bin/fedorajam-audio-config', doraise=True)"
bash -n usr/sbin/fedorajam-pwjack-config
python3 -m py_compile usr/share/fedorajam-audio-config/__init__.py
python3 -m py_compile usr/share/fedorajam-audio-config/main.py
python3 -m py_compile usr/share/fedorajam-audio-config/i18n.py
python3 -m py_compile usr/share/fedorajam-audio-config/backend/__init__.py
python3 -m py_compile usr/share/fedorajam-audio-config/backend/audio_config.py
python3 -m py_compile usr/share/fedorajam-audio-config/ui/__init__.py
python3 -m py_compile usr/share/fedorajam-audio-config/ui/base.py
python3 -m py_compile usr/share/fedorajam-audio-config/ui/gtk_ui.py
python3 -m py_compile usr/share/fedorajam-audio-config/ui/qt_ui.py

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}%{_bindir} %{buildroot}%{_sbindir} \
  %{buildroot}%{_sysconfdir}/default/grub.d %{buildroot}%{_userunitdir} %{buildroot}%{_userpresetdir} %{buildroot}%{_docdir}/%{name} %{buildroot}%{_datadir}/applications

# Source is the current directory after prep
src="."

install -m 0755 ${src}/usr/bin/fedorajam-audio-config %{buildroot}%{_bindir}/fedorajam-audio-config
install -m 0755 ${src}/usr/sbin/fedorajam-pwjack-config %{buildroot}%{_sbindir}/fedorajam-pwjack-config
install -m 0644 ${src}/usr/lib/systemd/user/fedorajam-dummy-audio.service %{buildroot}%{_userunitdir}/fedorajam-dummy-audio.service
install -m 0644 ${src}/usr/lib/systemd/user/fedorajam-pwconfig-start.service %{buildroot}%{_userunitdir}/fedorajam-pwconfig-start.service
install -m 0644 ${src}/usr/lib/systemd/user-preset/90_fedorajam-pwconfig-start.preset %{buildroot}%{_userpresetdir}/90_fedorajam-pwconfig-start.preset
install -m 0644 ${src}/usr/share/applications/fedorajam-audio-config.desktop %{buildroot}%{_datadir}/applications/fedorajam-audio-config.desktop

# Install minimal manpages
install -d %{buildroot}%{_mandir}/man1
install -m 0644 ${src}/usr/share/man/man1/fedorajam-audio-config.1 %{buildroot}%{_mandir}/man1/fedorajam-audio-config.1
install -m 0644 ${src}/usr/share/man/man1/fedorajam-pwjack-config.1 %{buildroot}%{_mandir}/man1/fedorajam-pwjack-config.1

# Install Python application
install -d %{buildroot}%{_datadir}/fedorajam-audio-config
cp -a ${src}/usr/share/fedorajam-audio-config/* %{buildroot}%{_datadir}/fedorajam-audio-config/

# Build and install translations
make -C ${src}/po all
make -C ${src}/po install DESTDIR=%{buildroot}

%post
%systemd_user_post fedorajam-dummy-audio.service fedorajam-pwconfig-start.service
if ! [ -f %{_sysconfdir}/profile.d/fedorajam-pwjack.sh ]; then
   %{_sbindir}/fedorajam-pwjack-config 1024 48000
fi

%pre
%systemd_user_preun fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%preun
%systemd_user_preun fedorajam-dummy-audio.service fedorajam-pwconfig-start.service
if [ -f %{_sysconfdir}/profile.d/fedorajam-pwjack.sh ]; then
  %{__rm} -f %{_sysconfdir}/profile.d/fedorajam-pwjack.sh
fi
if [ -f %{_sysconfdir}/fedorajamboot.cfg ]; then
  %{__rm} -f %{_sysconfdir}/fedorajamboot.cfg
fi

%postun
%systemd_user_postun_with_restart fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%files
%license COPYING
%{_bindir}/fedorajam-audio-config
%{_sbindir}/fedorajam-pwjack-config
%{_datadir}/fedorajam-audio-config/
%{_datadir}/locale/*/LC_MESSAGES/fedorajam-audio-config.mo
%{_userunitdir}/fedorajam-dummy-audio.service
%{_userunitdir}/fedorajam-pwconfig-start.service
%{_userpresetdir}/90_fedorajam-pwconfig-start.preset
%{_datadir}/applications/fedorajam-audio-config.desktop
%{_mandir}/man1/fedorajam-audio-config.1*
%{_mandir}/man1/fedorajam-pwjack-config.1*
%doc README.md

%changelog
* Sun Feb 22 2026 Erich Eickmeyer <erich@ericheickmeyer.com> 2.0.1-1
- Complete rewrite in Python

* Sat Jan 24 2026 Erich Eickmeyer <erich@ericheickmeyer.com> 1.2-1
- Update to version 1.2
- Fix for rpmlint warnings

* Wed Jan 14 2026 Erich Eickmeyer <erich@ericheickmeyer.com> 1.0-1
- Initial release
