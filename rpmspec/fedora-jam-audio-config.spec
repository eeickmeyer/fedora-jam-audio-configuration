Name:           fedora-jam-audio-config
Version:        1.0
Release:        1%{?dist}
Summary:        PipeWire-JACK audio configuration scripts for Fedora Jam

License:        GPL-2.0-or-later
URL:            https://pagure.io/fedora-jam-audio-configuration
# No upstream tarball; packaging uses the repository files
BuildRequires:  systemd-rpm-macros
Requires:       grub bash zenity polkit systemd pipewire pipewire-utils pulseaudio-utils

%description
A lightweight set of scripts for manipulating a user's
PipeWire-JACK configuration

%prep
# No upstream tarball to unpack; use repository files directly
# Create a source dir so builds that expect %{name}-%{version} succeed
mkdir -p %{name}-%{version}
# Copy repository files into the source dir (ignore errors if none)
cp -a ./* %{name}-%{version}/ 2>/dev/null || :
cd %{name}-%{version} || :

%build
# blank

%install
rm -rf %{buildroot}
install -d -m 0755 %{buildroot}%{_bindir} %{buildroot}%{_sbindir} \
  %{buildroot}%{_sysconfdir}/default/grub.d %{buildroot}%{_userunitdir} %{buildroot}%{_docdir}/%{name}

%post
%{?systemd_requires}
%systemd_user_post fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%preun
%{?systemd_requires}
%systemd_user_preun fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%postun
%{?systemd_requires}
%systemd_user_postun_with_restart fedorajam-dummy-audio.service fedorajam-pwconfig-start.service

%files
%license COPYING
%doc %{_docdir}/%{name}/COPYING
%config(noreplace) %{_sysconfdir}/default/grub.d/fedorajam.cfg
%{_bindir}/fedorajam-audio-config
%{_sbindir}/fedorajam-pwjack-config
%{_userunitdir}/fedorajam-dummy-audio.service
%{_userunitdir}/fedorajam-pwconfig-start.service

%changelog
* Wed Jan 14 2026 Erich Eickmeyer <erich@ericheickmeyer.com>
- Initial release
