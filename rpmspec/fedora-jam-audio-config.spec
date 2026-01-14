Name:           fedora-jam-audio-config
Version:        1.0
Release:        1%{?dist}
Summary:        PipeWire-JACK audio configuration scripts for Fedora Jam

License:        GPL-2.0-or-later
URL:            https://pagure.io/fedora-jam-audio-configuration
Source0:        https://pagure.io/fedora-jam-audio-configuration

BuildRequires:  systemd-rpm-macros
Requires:       grub bash zenity polkit systemd pipewire pipewire-utils pulseaudio-utils

%description
A lightweight set of scripts for manipulating a user's
PipeWire-JACK configuration

%prep
%autosetup

%build
# blank

%install
tar cpf - . | tar --directory %{buildroot} -xvpf -
	
if [ %{_prefix} != /usr ] ; then
   pushd %{buildroot}
   mv %{buildroot}/usr %{buildroot}%{_prefix}
   mv %{buildroot}/etc %{buildroot}%{_sysconfdir}
   popd
fi

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
%config(noreplace) %{_sysconfdir}/default/grub.d/fedorajam.cfg
%{_bindir}/fedorajam-audio-config
%{_sbindir}/fedorajam-pwjack-config
%{_libdir}/systemd/user/fedorajam-dummy-audio.service
%{_libdir}/systemd/user/fedorajam-pwconfig-start.service

%changelog
* Wed Jan 14 2026 Erich Eickmeyer <erich@ericheickmeyer.com>
- Initial release
