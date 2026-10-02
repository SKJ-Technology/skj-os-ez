%global dist_version 44

Name:           skj-release
Version:        %{dist_version}
Release:        2%{?dist}
Summary:        SKJ OS EZ ISO Edition release files (KDE Plasma)
License:        MIT
BuildArch:      noarch

# Source files live in src/ (build-rpms.sh passes it as _sourcedir).
Source0:        LICENSE
Source1:        os-release
Source2:        skj-release
Source3:        issue
Source4:        issue.net
Source5:        system-release-cpe
Source6:        macros.dist
Source7:        20-skj-defaults.conf
Source8:        skj-release.conf
Source9:        skj-os-ez-kde.conf

Provides:       skj-release-kde = %{version}-%{release}
Provides:       system-release
Provides:       system-release(%{version})

# SKJ OS EZ is based on Fedora: keep Fedora's repositories and keys.
Requires:       fedora-repos(%{version})

Conflicts:      fedora-release-common
Conflicts:      fedora-release-identity
Conflicts:      generic-release-common
Conflicts:      generic-release

%description
Release files for SKJ OS EZ ISO Edition (KDE Plasma), based on Fedora
Linux %{version}: os-release, systemd presets, dnf defaults, rpm dist macros
the Anaconda installer profile and Firefox defaults (homepage, bookmarks).

%prep

%build

%install
install -d %{buildroot}%{_prefix}/lib %{buildroot}%{_sysconfdir}

install -pm 0644 %{SOURCE1} %{buildroot}%{_prefix}/lib/os-release
ln -s ../usr/lib/os-release %{buildroot}%{_sysconfdir}/os-release

install -pm 0644 %{SOURCE2} %{buildroot}%{_prefix}/lib/skj-release
ln -s ../usr/lib/skj-release %{buildroot}%{_sysconfdir}/skj-release
# Many tools still read these names; point them at our release string.
ln -s skj-release %{buildroot}%{_sysconfdir}/system-release
ln -s skj-release %{buildroot}%{_sysconfdir}/redhat-release
ln -s skj-release %{buildroot}%{_sysconfdir}/fedora-release

install -pm 0644 %{SOURCE3} %{buildroot}%{_prefix}/lib/issue
install -pm 0644 %{SOURCE4} %{buildroot}%{_prefix}/lib/issue.net
ln -s ../usr/lib/issue %{buildroot}%{_sysconfdir}/issue
ln -s ../usr/lib/issue.net %{buildroot}%{_sysconfdir}/issue.net

install -pm 0644 %{SOURCE5} %{buildroot}%{_prefix}/lib/system-release-cpe
ln -s ../usr/lib/system-release-cpe %{buildroot}%{_sysconfdir}/system-release-cpe

install -Dpm 0644 %{SOURCE6} %{buildroot}%{_rpmmacrodir}/macros.dist
install -Dpm 0644 %{SOURCE7} %{buildroot}%{_datadir}/dnf5/libdnf.conf.d/20-skj-defaults.conf
install -Dpm 0644 %{SOURCE8} %{buildroot}%{_sysconfdir}/dnf/protected.d/skj-release.conf
install -Dpm 0644 %{SOURCE9} %{buildroot}%{_sysconfdir}/anaconda/profile.d/skj-os-ez-kde.conf

# systemd presets, identical to Fedora 44 KDE Plasma Desktop Edition
install -d %{buildroot}%{_prefix}/lib/systemd/system-preset %{buildroot}%{_prefix}/lib/systemd/user-preset
install -pm 0644 %{_sourcedir}/presets/system/*.preset %{buildroot}%{_prefix}/lib/systemd/system-preset/
install -pm 0644 %{_sourcedir}/presets/user/*.preset %{buildroot}%{_prefix}/lib/systemd/user-preset/

# Firefox defaults: SKJ bookmarks + Firefox start page instead of Fedora's.
# Fedora's firefox lives in /usr/lib64/firefox (x86_64 only, like the ISO).
install -Dpm 0644 %{_sourcedir}/firefox/00-skj-default-prefs.js %{buildroot}/usr/lib64/firefox/browser/defaults/preferences/00-skj-default-prefs.js
install -Dpm 0644 %{_sourcedir}/firefox/bookmarks.html %{buildroot}%{_datadir}/skj/firefox/bookmarks.html

install -Dpm 0644 %{SOURCE0} %{buildroot}%{_licensedir}/%{name}/LICENSE

%files
%license %{_licensedir}/%{name}/LICENSE
%{_prefix}/lib/os-release
%{_sysconfdir}/os-release
%{_prefix}/lib/skj-release
%{_sysconfdir}/skj-release
%{_sysconfdir}/system-release
%{_sysconfdir}/redhat-release
%{_sysconfdir}/fedora-release
%{_prefix}/lib/issue
%{_prefix}/lib/issue.net
%config(noreplace) %{_sysconfdir}/issue
%config(noreplace) %{_sysconfdir}/issue.net
%{_prefix}/lib/system-release-cpe
%{_sysconfdir}/system-release-cpe
%{_rpmmacrodir}/macros.dist
%{_datadir}/dnf5/libdnf.conf.d/20-skj-defaults.conf
%config(noreplace) %{_sysconfdir}/dnf/protected.d/skj-release.conf
%dir %{_sysconfdir}/anaconda
%dir %{_sysconfdir}/anaconda/profile.d
%config(noreplace) %{_sysconfdir}/anaconda/profile.d/skj-os-ez-kde.conf
%{_prefix}/lib/systemd/system-preset/*.preset
%{_prefix}/lib/systemd/user-preset/*.preset
/usr/lib64/firefox/browser/defaults/preferences/00-skj-default-prefs.js
%dir %{_datadir}/skj
%{_datadir}/skj/firefox/

%changelog
* Fri Oct 02 2026 SKJ OS <jnowakowski741@gmail.com> - 44-2
- Firefox defaults: SKJ bookmarks for new profiles instead of Fedora's,
  Firefox's own start page instead of start.fedoraproject.org

* Tue Sep 29 2026 SKJ OS <jnowakowski741@gmail.com> - 44-1
- First release for SKJ OS EZ ISO Edition (KDE Plasma), based on Fedora 44
