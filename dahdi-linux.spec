###################################################################
#
#  dahdi-linux.spec - used to generate dahdi-linux rpms
#  For more info: http://www.rpm.org/max-rpm/ch-rpm-basics.html
#
#  This spec file uses default directories:
#  /usr/src/redhat/SOURCES - orig source, patches, icons, etc.
#  /usr/src/redhat/SPECS - spec files
#  /usr/src/redhat/BUILD - sources unpacked & built here
#  /usr/src/redhat/RPMS - binary package files
#  /usr/src/redhat/SRPMS - source package files
#
###################################################################
#
#  Global Definitions
#
###################################################################
#%{!?kversion: %define kversion 2.6.18-164.2.1.el5}
#%define kversion %(uname -r|sed -e 's/\.\w*$//g')
#%define kversion %(uname -r |/usr/bin/rev | cut -d '.' -f 2- |/usr/bin/rev)
%define kversion %(verrel=$(ls -Ud /usr/src/kernels/* | sort -V | tail -n 1); echo ${verrel##*/})
%global debug_package %{nil}

Source10: kmodtool
%if 0%{?rhel} >= 6
  %define kmodtool /usr/lib/rpm/redhat/kmodtool
%else
  %define kmodtool bash %{SOURCE10}
%endif


%define kmod_name dahdi-linux
%define kverrel %(%{kmodtool} verrel %{?kversion} 2>/dev/null)

%if 0%{?rhel} == 5
  %ifarch i686
    %define kvariants "" xen PAE
  %endif
  %ifarch x86_64
    %define kvariants "" xen
  %endif
%endif

%if 0%{?rhel} >= 6
  %define kvariants ""
%endif

%{!?kvariants: %define kvariants %{?upvar} %{?smpvar} %{?xenvar} %{?kdumpvar} %{?PAEvar}}
# hint: this can he overridden with "--define kvariant foo bar" on the rpmbuild command line, e.g.
# --define 'kvariant "" smp'


#Workaround for 64 bit CPUs
%define _lib lib

###################################################################
#
#  The Preamble
#  information that is displayed when users request info
#
###################################################################
Summary: The DAHDI project
Name: dahdi-linux
Version:          3.1.0
Release:          <RELEASE>1%{?_rc:.rc%{_rc}}%{?_beta:.beta%{_beta}}%{?dist}
License: GPL
Group: Utilities/System
Source: %{name}-%{version}.tar.gz
Source1: oslec-echo-linux-3.10.99.tar.gz
Patch0: dahdi-kmodtoolpath.diff
Patch1: dahdi-no-fwload.diff
BuildRoot: %{_tmppath}/%{name}-%{version}-root
URL: http://www.asterisk.org/
Vendor: Digium, Inc.
Packager: Jason Parker <jparker@digium.com>
#Requires: yum-kmod
Requires: dahdi-firmware
BuildRequires: kernel
BuildRequires: kernel-devel
%if 0%{?rhel} == 6
BuildRequires: kabi-whitelists
%endif
%if 0%{?rhel} == 7
BuildRequires: kernel-abi-whitelists
%endif
%if 0%{?rhel} == 8
BuildRequires: kernel-abi-whitelists
BuildRequires: kernel-rpm-macros
BuildRequires: elfutils-libelf-devel
%endif

#%if 0%{?fedora_version} >= 23
#BuildRequires: sqlite
#BuildRequires: python3-libs python3
#%endif

%description
The open source DAHDI project

%package devel
Summary: DAHDI libraries and header files for development
Group: Development/Libraries
Requires: %{name} = %{version}-%{release}

%description devel
The static libraries and header files needed for building additional plugins/modules

%define kmod_version %{version}
%define kmod_release %{release}

# magic hidden here:
#%{expand:%(%{kmodtool} rpmtemplate_kmp %{kmod_name} %{kverrel} %{kvariants} 2>/dev/null)}
%{expand:%(%{kmodtool} rpmtemplate %{kmod_name} %{kverrel} %{kvariants} 2>/dev/null)}

%global debug_package %{nil}

###################################################################
#
#  The Prep Section
#  If stuff needs to be done before building, this is the section
#  Use shell scripts to do stuff like uncompress and cd into source dir
#  %setup macro - cleans old build trees, uncompress and extracts original source
#
###################################################################
%prep
%setup -c -n %{name}-%{version}

cd %{name}-%{version}/

gzip -dc %{SOURCE1} | tar -xvvf -

%patch0 -p0
%patch1 -p0

echo %{version} > .version
cd ../
for kvariant in %{kvariants} ; do
    cp -a %{name}-%{version} _kmod_build_$kvariant
done
cd %{name}-%{version}

###################################################################
#
#  The Build Section
#  Use shell scripts and do stuff that makes the build happen, i.e. make
#
###################################################################
%build
echo %{version} > .version
echo %{kversion}
for kvariant in %{kvariants}
do
    pushd _kmod_build_$kvariant
    make KVERS="%{kverrel}${kvariant}" modules
    popd
done


###################################################################
#
#  The Install Section
#  Use shell scripts and perform the install, like 'make install',
#  but can also be shell commands, i.e. cp, mv, install, etc..
#
###################################################################
%install
mkdir -p $RPM_BUILD_ROOT/%{_sysconfdir}/udev/rules.d/
cd %{name}-%{version}
make DESTDIR=$RPM_BUILD_ROOT install-include
cd ../

for kvariant in %{kvariants}
do
    pushd _kmod_build_$kvariant
    make DESTDIR=$RPM_BUILD_ROOT KVERS="%{kverrel}${kvariant}" install-modules
    popd
done

###################################################################
#
#  Install and Uninstall
#  This section can have scripts that are run either before/after
#  an install process, or before/after an uninstall process
#  %pre - executes prior to the installation of a package
#  %post - executes after the package is installed
#  %preun - executes prior to the uninstallation of a package
#  %postun - executes after the uninstallation of a package
#
###################################################################
%post
ldconfig

###################################################################
#
#  Verify
#
###################################################################
%verifyscript

###################################################################
#
#  Clean
#
###################################################################
%clean
cd $RPM_BUILD_DIR
%{__rm} -rf %{name}-%{version}
%{__rm} -rf /var/log/%{name}-sources-%{version}-%{release}.make.err
%{__rm} -rf $RPM_BUILD_ROOT

###################################################################
#
#  File List
#
###################################################################
%files
#
#  Documents
#
#%doc UPGRADE.txt

%config %{_sysconfdir}/udev/rules.d/

%files devel
#
#  Header Files
#
%defattr(-, root, root)
%{_includedir}/dahdi/dahdi_config.h
%{_includedir}/dahdi/fasthdlc.h
%{_includedir}/dahdi/kernel.h
%{_includedir}/dahdi/user.h
%{_includedir}/dahdi/wctdm_user.h

#
# Changelog
#
%changelog
* Sat Jun  27 2020 ganapathi.rj@gmail.com
- Initial RPM





