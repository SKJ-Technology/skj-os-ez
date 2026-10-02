# systemd's rpm macros may be missing in a bare build container
%{!?_userunitdir:%global _userunitdir /usr/lib/systemd/user}
%{!?_userpresetdir:%global _userpresetdir /usr/lib/systemd/user-preset}

Name:           skj-hub
Version:        0.1.0
Release:        1%{?dist}
Summary:        SKJ Hub: apps, updates and help for SKJ OS EZ
License:        MIT
BuildArch:      noarch
# Sources: the hub/ directory (build-rpms.sh passes it as _sourcedir).

Requires:       python3
Requires:       python3-pyside6
Requires:       python3-gobject
Requires:       PackageKit
Requires:       PackageKit-glib
Requires:       flatpak-libs
Requires:       snapd-glib
Requires:       appstream
Recommends:     snapd

%description
The one app for SKJ OS EZ beginners: find and install apps (Flatpak, distro
packages and Snap, one entry per app), update everything with one button,
and get help. Polish and English.

%prep
%build

%install
S=%{_sourcedir}
install -d %{buildroot}%{_datadir}/skj-hub
cp -a $S/skj_hub %{buildroot}%{_datadir}/skj-hub/
find %{buildroot}%{_datadir}/skj-hub -name __pycache__ -prune -exec rm -rf {} +
install -Dpm 0755 $S/data/skj-hub %{buildroot}%{_bindir}/skj-hub
install -Dpm 0644 $S/data/skj-hub.desktop %{buildroot}%{_datadir}/applications/skj-hub.desktop
install -Dpm 0644 $S/data/skj-hub-notify.service %{buildroot}%{_userunitdir}/skj-hub-notify.service
install -Dpm 0644 $S/data/skj-hub-notify.timer %{buildroot}%{_userunitdir}/skj-hub-notify.timer
install -Dpm 0644 $S/data/90-skj-hub.preset %{buildroot}%{_userpresetdir}/90-skj-hub.preset

%files
%{_datadir}/skj-hub/
%{_bindir}/skj-hub
%{_datadir}/applications/skj-hub.desktop
%{_userunitdir}/skj-hub-notify.service
%{_userunitdir}/skj-hub-notify.timer
%{_userpresetdir}/90-skj-hub.preset

%changelog
* Fri Oct 02 2026 SKJ OS <jnowakowski741@gmail.com> - 0.1.0-1
- First build: app store (Flatpak, dnf via PackageKit, Snap), one-button
  updates, update notifier, help page; Polish and English
