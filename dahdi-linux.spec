%define realname dahdi-linux
%define drvver   2.11.1
%define utilver  2.11.1
%define srcext   tar.gz

%define ppp_pkg_version %(rpm -q --qf '%%{version}' ppp-devel)
%define pppd_version    %(sed -r 's/^([0-9.]+[0-9]).*$/\\1/g' <<< %{ppp_pkg_version})

# turn off the generation of debuginfo rpm  (RH9) ??
%global debug_package %{nil}

%if 0%{?suse_version} >= 1310
%undefine build_echo
%else
%define build_echo 1
%endif

Name:          dahdi-linux
Version:       %{drvver}
Release:       <RELEASE>%{?dist}
License:       GPL-2.0 and LGPL-2.1
Group:         System/Kernel
URL:           http://www.asterisk.org/dahdi
Summary:       DAHDI Telephony Interface Driver

# Install-time parameters
Requires:      udev

# Build-time parameters
BuildRequires: perl
%if 0%{?rhel}
%ifarch %ix86
BuildArch:     i686
%endif
%endif
BuildRequires: autoconf automake libtool
BuildRequires: %kernel_module_package_buildreqs
%if 0%{?suse_version}
BuildRequires: kernel-source kernel-syms modutils insserv-compat
%endif

%if 0%{?fedora_version} >= 28 || 0%{?rhel} >=8
BuildRequires: kernel-rpm-macros elfutils-libelf-devel kernel-abi-whitelists
%endif

%if 0%{?fedora_version} >= 23
BuildRequires: sqlite
BuildRequires: python3-libs python3
%endif

BuildRequires: ppp-devel
BuildRequires: libusb-devel libselinux-devel udev
BuildRoot:     %{_tmppath}/%{name}-%{version}-build
Source0:       http://downloads.asterisk.org/pub/telephony/dahdi-linux-complete/releases/%{realname}-%{drvver}.%{srcext}
Source1:      firmware-20180403.tar.xz

# RHEL and derivatives comes without kernel-source package
# This is snapshot of OSLEC from tree of kernel 2.6.32
Source99:      linux-stable-e45c6f7.tar.gz

# Kernel header file for GCC 5.x
Source199:     compiler-gcc5.h

# [PATCH] build fix: external CFLAGS are ignored
#Patch0:        https://github.com/asterisk/dahdi-tools/commit/99e3c572d1ce4b2c3e0195499b84cb56ade94bea.patch

# Support for Linux kernel 4.11+
#Patch11:       https://issues.asterisk.org/jira/secure/attachment/55523/0001-signal_pending-is-now-in-linux-sched-signal.h-includ.patch
#Patch12:       https://issues.asterisk.org/jira/secure/attachment/55524/0002-atomic_read-refcount_read.patch



%description
DAHDI Telephony Interface Driver.

%package KMP
Summary:       Kernel modules of DAHDI Telephony Interface Driver
Group:         System/Kernel

%description KMP
Kernel modules of DAHDI Telephony Interface Driver.

%package -n dahdi-ppp-plugin
Summary:       PPP daemon plugin to implement PPP over DAHDI HDLC channel
Group:         Productivity/Networking/PPP
Requires:      ppp = %{ppp_pkg_version}

%description -n dahdi-ppp-plugin
pppd plugin to implement PPP over DAHDI HDLC channel.

%prep
%setup -n %{realname}-%{drvver}
#%patch11 -p1 -d linux
#%patch12 -p1 -d linux
# GCC >= 5.x support
gcc_header_search_path=(
    /usr/src/linux/include/linux/compiler-gcc4.h
    %{kernel_source default}/include/linux/compiler-gcc4.h
    %{S:199}
)
for gcc_header in "${gcc_header_search_path[@]}"; do
    if [ -f $gcc_header ]; then
        break
    fi
done
for ver in $(seq 5 8); do
    %{__install} -D -m644 $gcc_header drivers/dahdi/linux/compiler-gcc$ver.h
done
# OSLEC echo cancellation
%{__mkdir} drivers/staging
%if 0%{?build_echo}
%if 0%{?suse_version}
%{__cp} -r /usr/src/linux/drivers/staging/echo drivers/staging/
%else
%{__tar} -zxf %{S:99} -C drivers/staging
%{__mv} drivers/staging/linux-* drivers/staging/echo
%endif
echo 'obj-m += echo.o' > drivers/staging/echo/Kbuild
%else
%{__mkdir} drivers/staging/echo
find /usr/src/linux/drivers -name oslec.h -exec cp -v {} drivers/staging/echo/ \;
%endif
# Firmwares
#%{__cp} %{S:1} /
#pushd linux
#%{__tar} -zxf drivers/dahdi/firmware/dahdi-fwload-*.tar.gz
#%{__tar} -xf *.tar.xz
#popd

pushd drivers/dahdi/firmware
%{__tar} -xf *.tar.xz
for fw in *.tar.gz*
do
  %{__tar} -zxf ${fw}
done
popd
DAHDI_VERSION=%{drvver} build_tools/make_version_h > include/dahdi/version.h
%{__sed} -ri '/^man_MANS\s*=.*perl_mans/ d' tools/xpp/Makefile.*

%build
%define topdir %{_builddir}/%{realname}-%{drvver}+%{utilver}
export EXTRA_CFLAGS='-DVERSION=\"%version\"'
pushd drivers
mkdir obj
for flavor in %flavors_to_build; do
    %{__mkdir_p} obj/$flavor
    %{__cp} -r dahdi staging obj/$flavor
    %{__make} -C %{kernel_source $flavor} \
      M=$PWD/obj/$flavor/dahdi/oct612x
    %{__make} -C %{kernel_source $flavor} modules \
      M=$PWD/obj/$flavor/dahdi \
      DAHDI_INCLUDE=%{topdir}/include \
      HOTPLUG_FIRMWARE=yes \
      DAHDI_MODULES_EXTRA="dahdi_echocan_oslec.o %{?build_echo:../staging/echo/echo.o}" \
      DAHDI_BUILD_ALL=m
done
popd
#pushd tools
#%configure \
# --with-dahdi=%{topdir}/linux \
# --with-usb \
# --with-selinux \
# --with-ppp \
# CFLAGS="%{optflags} -Wno-format-truncation" \
# LDFLAGS="-Wl,--as-needed -Wl,--strip-all"
# Disable am--refresh target
#%{__sed} -ri \
# -e 's/^\tam--refresh /\t/' \
# -e '/^am--refresh/,/^$/ d' \
# Makefile
#%{__make} %{?_smp_mflags} all
#popd

%install
export INSTALL_MOD_PATH=$RPM_BUILD_ROOT
%if 0%{?suse_version}
export INSTALL_MOD_DIR=updates
%else
export INSTALL_MOD_DIR=extra/%{name}
%endif
%{__make} \
 install-include \
 install-firmware \
 install-xpp-firm \
 HOTPLUG_FIRMWARE=yes \
 DESTDIR=%{buildroot}
pushd drivers
for flavor in %flavors_to_build; do
    %{__make} -C %{kernel_source $flavor} modules_install \
      M=$PWD/obj/$flavor/dahdi
    [ -f %{buildroot}/lib/modules/*-$flavor/staging/echo/echo.ko ] && \
      %{__mv} -f %{buildroot}/lib/modules/*-$flavor/staging/echo/echo.ko %{buildroot}/lib/modules/*-$flavor/updates
done
popd
export PATH=$PATH:/sbin:/usr/sbin
pushd tools
%{__make} install DESTDIR=%{buildroot}
%{__make} config  DESTDIR=%{buildroot}
popd
#%{__install} -D -m755 tools/dahdi.init    %{buildroot}%{_initrddir}/dahdi
%{__install}    -m644 drivers/dahdi/xpp/xpp.conf  %{buildroot}%{_sysconfdir}/dahdi/xpp.conf
for rules in %{buildroot}%{_sysconfdir}/udev/rules.d/*.rules
do
%if 0%{?suse_version} && ! 0%{?sles_version}
  %{__install} -d -m755 %{buildroot}/usr/lib/udev/rules.d
  %{__mv} -f ${rules} %{buildroot}/usr/lib/udev/rules.d/98-$(basename ${rules})
%else
  %{__mv} -f ${rules} %{buildroot}/etc/udev/rules.d/98-$(basename ${rules})
%endif
done
%{__mkdir_p} %{buildroot}%{perl_vendorlib}
%{__cp} -r %{buildroot}%{perl_sitelib}/* %{buildroot}%{perl_vendorlib}/
%{__rm} -rf %{buildroot}%{perl_sitelib}
%if 0%{?suse_version}
%{__ln_s} %{_initrddir}/dahdi %{buildroot}%{_sbindir}/rcdahdi
%endif

%clean
[ "%{buildroot}" != "/" ] && rm -rf %{buildroot}

%files
%defattr(-,root,root)
%doc LICENSE LICENSE.LGPL README UPGRADE.txt
%doc drivers/dahdi/xpp/firmwares/LICENSE.firmware
%if 0%{?suse_version} && ! 0%{?sles_version}
%dir /usr/lib/udev/rules.d/
%dir /usr/lib/udev/
/usr/lib/udev/rules.d/98-*.rules
%else
%dir %{_sysconfdir}/udev/rules.d/
%dir %{_sysconfdir}/udev/
%config %{_sysconfdir}/udev/rules.d/98-*.rules
%endif
%dir /usr/share/dahdi/handle_device.d
%dir /usr/share/dahdi/span_config.d
%dir /usr/share/dahdi
/lib/firmware/dahdi-fw-*.bin
/usr/share/dahdi/*.hex
/usr/share/dahdi/XppConfig.pm
/usr/share/dahdi/init_card_*
/usr/share/dahdi/dahdi_auto_assign_compat
/usr/share/dahdi/dahdi_handle_device
/usr/share/dahdi/dahdi_span_config
/usr/share/dahdi/handle_device.d/10-span-types
/usr/share/dahdi/handle_device.d/20-span-assignments
/usr/share/dahdi/span_config.d/10-dahdi-cfg
/usr/share/dahdi/span_config.d/20-fxotune
/usr/share/dahdi/span_config.d/50-asterisk
%exclude /lib/firmware/.dahdi-fw*

%files -n dahdi-ppp-plugin
%defattr(-,root,root)
%{_libdir}/pppd/%{pppd_version}/dahdi.so
%exclude %{_libdir}/pppd/%{pppd_version}/dahdi.a
%exclude %{_libdir}/pppd/%{pppd_version}/dahdi.la

%pre
/usr/sbin/groupadd -r asterisk 2> /dev/null || :
/usr/sbin/useradd -r -o -s /bin/false -c "User for Asterisk" -d /var/lib/asterisk -g asterisk asterisk 2> /dev/null || :


%changelog
* Sat Jun  27 2020 ganapathi.rj@gmail.com
- Initial RPM
