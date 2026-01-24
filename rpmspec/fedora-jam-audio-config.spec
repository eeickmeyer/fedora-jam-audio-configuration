Name:           fedora-jam-audio-config
Version:        1.1
Release:        1%{?dist}
Summary:        PipeWire-JACK audio configuration scripts for Fedora Jam

%global debug_package %{nil}

License:        GPL-2.0-or-later
URL:            https://pagure.io/fedora-jam-audio-configuration
Source0:        https://releases.pagure.org/fedora-jam-audio-configuration/%{name}-%{version}.tar.gz
BuildRequires:  systemd-rpm-macros
Requires:       grub2-common bash zenity polkit systemd pipewire pipewire-utils pulseaudio-utils

%description
A lightweight set of GUI scripts for manipulating a user's
PipeWire-JACK configuration as well as a system's GRUB configuration
to optimize for low-latency audio performance on Fedora Jam.

%prep
%setup -q

%build
# blank

%check
bash -n usr/bin/fedorajam-audio-config
bash -n usr/sbin/fedorajam-pwjack-config

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

%post
%systemd_user_post fedorajam-dummy-audio.service fedorajam-pwconfig-start.service
if ! [ -f %{_sysconfdir}/profile.d/fedorajam-pwjack.sh ]; then
   %{_sbindir}/fedorajam-pwjack-config 1024 48000
fi

%preun
%systemd_user_preun fedorajam-dummy-audio.service fedorajam-pwconfig-start.service
rm -f %{_sysconfdir}/profile.d/fedorajam-pwjack.sh
rm -f %{_sysconfdir}/fedorajamboot.cfg || true

%postun
%systemd_user_postun_with_restart fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%files
%license COPYING
%{_bindir}/fedorajam-audio-config
%{_sbindir}/fedorajam-pwjack-config
%{_userunitdir}/fedorajam-dummy-audio.service
%{_userunitdir}/fedorajam-pwconfig-start.service
%{_userpresetdir}/90_fedorajam-pwconfig-start.preset
%{_datadir}/applications/fedorajam-audio-config.desktop

%changelog
* Sat Jan 24 2026 Erich Eickmeyer <erich@ericheickmeyer.com>
- Update to version 1.1

* Wed Jan 14 2026 Erich Eickmeyer <erich@ericheickmeyer.com>
- Initial release
