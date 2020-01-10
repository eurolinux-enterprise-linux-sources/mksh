%define _bindir   /bin
Summary:          MirBSD enhanced version of the Korn Shell
Name:             mksh
Version:          46
Release:          8%{?dist}
# BSD (setmode.c), ISC (strlcpy.c), MirOS (the rest)
License:          MirOS and ISC and BSD
Group:            System Environment/Shells
URL:              https://www.mirbsd.de/%{name}.htm
Source0:          http://www.mirbsd.org/MirOS/dist/mir/%{name}/%{name}-R%{version}.tgz
Source1:          dot-mkshrc
Source2:          rtchecks.expected
Patch0:           mksh-46-lksh.patch
# from upstream, for mksh <= 55, rhbz#1243788
Patch1:           mksh-55-waitfail.patch
# from upstream, for mksh <= 50f, rhbz#1491312
Patch2:           mksh-46-selectopts.patch
# from upstream, for mksh < 47, rhbz#1413023
Patch3:           mksh-46-fixtrace.patch
Requires:         chkconfig
Requires(post):   grep, chkconfig
Requires(postun): sed
BuildRequires:    util-linux, ed
BuildRoot:        %{_tmppath}/%{name}-%{version}-%{release}-root-%(%{__id_u} -n)
#for usage of alternatives
Conflicts:        ksh < 20120801-9

%description
mksh is the MirBSD enhanced version of the Public Domain Korn shell (pdksh),
a bourne-compatible shell which is largely similar to the original AT&T Korn
shell. It includes bug fixes and feature improvements in order to produce a
modern, robust shell good for interactive and especially script use, being a
bourne shell replacement, pdksh successor and an alternative to the C shell.

%prep
%setup -q -n %{name}
%patch0 -p0 -b .lksh
%patch1 -p1 -b .waitfail
%patch2 -p1 -b .selectopts
%patch3 -p1 -b .fixtrace

# we'll need this later
cat >rtchecks <<'EOF'
typeset -i sari=0
typeset -Ui uari=0
typeset -i x=0
print -r -- $((x++)):$sari=$uari. #0
let --sari --uari
print -r -- $((x++)):$sari=$uari. #1
sari=2147483647 uari=2147483647
print -r -- $((x++)):$sari=$uari. #2
let ++sari ++uari
print -r -- $((x++)):$sari=$uari. #3
let --sari --uari
let 'sari *= 2' 'uari *= 2'
let ++sari ++uari
print -r -- $((x++)):$sari=$uari. #4
let ++sari ++uari
print -r -- $((x++)):$sari=$uari. #5
sari=-2147483648 uari=-2147483648
print -r -- $((x++)):$sari=$uari. #6
let --sari --uari
print -r -- $((x++)):$sari=$uari. #7
(( sari = -5 >> 1 ))
((# uari = -5 >> 1 ))
print -r -- $((x++)):$sari=$uari. #8
(( sari = -2 ))
((# uari = sari ))
print -r -- $((x++)):$sari=$uari. #9
EOF

%build
# Work around RHBZ #922974 on Fedora 19 and later
%if 0%{?fedora} >= 19 || 0%{?rhel} > 6
CFLAGS="$RPM_OPT_FLAGS -DMKSH_DISABLE_EXPERIMENTAL" sh Build.sh -r
%else
CFLAGS="$RPM_OPT_FLAGS -DMKSH_DISABLE_EXPERIMENTAL" sh Build.sh -r -c lto
%endif
cp test.sh test_mksh.sh
# Work around RHBZ #922974 on Fedora 19 and later
%if 0%{?fedora} >= 19 || 0%{?rhel} > 6
CFLAGS="$RPM_OPT_FLAGS -DMKSH_DISABLE_EXPERIMENTAL" sh Build.sh -L -r
%else
CFLAGS="$RPM_OPT_FLAGS -DMKSH_DISABLE_EXPERIMENTAL" sh Build.sh -L -r -c lto
%endif
cp test.sh test_lksh.sh

%install
rm -rf $RPM_BUILD_ROOT
install -D -m 755 %{name} $RPM_BUILD_ROOT%{_bindir}/%{name}
install -D -m 755 lksh $RPM_BUILD_ROOT%{_bindir}/lksh
install -D -m 644 %{name}.1 $RPM_BUILD_ROOT%{_mandir}/man1/%{name}.1
install -D -m 644 lksh.1 $RPM_BUILD_ROOT%{_mandir}/man1/lksh.1
install -D -p -m 644 dot.mkshrc $RPM_BUILD_ROOT%{_sysconfdir}/mkshrc
install -D -p -m 644 %{SOURCE1} $RPM_BUILD_ROOT%{_sysconfdir}/skel/.mkshrc

# fool rpmdiff about %ghost files
touch $RPM_BUILD_ROOT/bin/ksh
touch $RPM_BUILD_ROOT%{_mandir}/man1/ksh.1.gz

%check
./mksh rtchecks >rtchecks.got 2>&1
if ! cmp --quiet rtchecks.got %{SOURCE2}
then
  echo "rtchecks failed"
  diff -Naurp %{SOURCE2} rtchecks.got
  exit 1
fi

for tf in test_mksh.sh test_lksh.sh
do
  echo > test.wait
  script -qc "./$tf"' -v; x=$?; rm -f test.wait; exit $x'
  maxwait=0
  while test -e test.wait; do
    sleep 1
    maxwait=$(expr $maxwait + 1)
    test $maxwait -lt 900 || break
  done
done

%post
grep -q "^%{_bindir}/%{name}$" %{_sysconfdir}/shells 2>/dev/null || \
  echo "%{_bindir}/%{name}" >> %{_sysconfdir}/shells

%{_sbindir}/alternatives --install /bin/ksh ksh \
                /bin/mksh 10 \
        --slave %{_mandir}/man1/ksh.1.gz ksh-man \
                %{_mandir}/man1/mksh.1.gz

%preun
if [ $1 = 0 ]; then
        %{_sbindir}/alternatives --remove ksh /bin/mksh
fi

%postun
if [ ! -x %{_bindir}/%{name} ]; then
  sed -e 's@^%{_bindir}/%{name}$@POSTUNREMOVE@' -e '/^POSTUNREMOVE$/d' -i %{_sysconfdir}/shells
fi

%clean
rm -rf $RPM_BUILD_ROOT

%files
%defattr(-,root,root,-)
%doc dot.mkshrc
%{_bindir}/%{name}
%ghost %{_bindir}/ksh
%ghost %{_mandir}/man1/ksh.1.gz
%{_bindir}/lksh
%config(noreplace) %{_sysconfdir}/mkshrc
%config(noreplace) %{_sysconfdir}/skel/.mkshrc
%{_mandir}/man1/%{name}.1*
%{_mandir}/man1/lksh.1*

%changelog
* Tue Oct 10 2017 Michal Hlavinka <mhlavink@redhat.com> - 46-8
- fix infinite recursion in PS4 (#1413023)

* Thu Sep 14 2017 Michal Hlavinka <mhlavink@redhat.com> - 46-7
- fix select setting wrong value on incorrect input (#1491312)

* Wed Aug 09 2017 Michal Hlavinka <mhlavink@redhat.com> - 46-6
- do not forget exit codes of co-processes in interactive mode (#1243788)

* Fri Jan 24 2014 Daniel Mach <dmach@redhat.com> - 46-5
- Mass rebuild 2014-01-24

* Fri Dec 27 2013 Daniel Mach <dmach@redhat.com> - 46-4
- Mass rebuild 2013-12-27

* Fri May 24 2013 Michal Hlavinka <mhlavink@redhat.com> - 46-3
- add alternatives switching with ksh

* Thu May 23 2013 Michal Hlavinka <mhlavink@redhat.com> - 46-2
- add workaround for broken gcc (#960113)

* Fri May 03 2013 Thorsten Glaser <tg@mirbsd.org> 46-1
- Upgrade mksh to R46

* Wed May 01 2013 Thorsten Glaser <tg@mirbsd.org> 45-1
- Upgrade mksh to R45 and the other files to the accompanying versions
- Drop workaround for GCC PR55009 (no longer needed)
- Use https for homepage

* Mon Mar 18 2013 Robert Scheck <robert@fedoraproject.org> 44-1
- Upgrade to 44 and work around bug in GCC 4.8 (#922974)

* Thu Feb 14 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 41-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Mon Dec 03 2012 Michal Hlavinka <mhlavink@redhat.com> - 41-1
- Upgrade to 41

* Fri Jul 20 2012 Michal Hlavinka <mhlavink@redhat.com> - 40i-0.20120630
- Upgrade to pre-release of 40i
- includes new legacy shell lksh for old scripts requiring pdksh or similar old
  ksh-88 shell, see man lksh for differences

* Fri Jul 20 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 40d-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Fri Jan 13 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 40d-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Sun Dec 11 2011 Robert Scheck <robert@fedoraproject.org> 40d-1
- Upgrade to 40d

* Tue Nov 22 2011 Robert Scheck <robert@fedoraproject.org> 40c-1
- Upgrade to 40c

* Thu Jul 28 2011 Robert Scheck <robert@fedoraproject.org> 40b-2
- Use new "Build.sh -r -c lto" rather "Build.sh -r -combine"

* Thu Jul 28 2011 Robert Scheck <robert@fedoraproject.org> 40b-1
- Upgrade to 40b

* Tue Feb 08 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 39c-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Tue Jan 04 2011 Michal Hlavinka <mhlavink@redhat.com> 39c-4
- fix crash when bad substitution is used

* Wed Jul 21 2010 Michal Hlavinka <mhlavink@redhat.com> 39c-3
- fix crash when alias contains alias
- fix crash when xtrace is enabled

* Sun Jul 11 2010 Robert Scheck <robert@fedoraproject.org> 39c-2
- Added default configuration /etc/mkshrc & /etc/skel/.mkshrc
  as default skel (like at bash; thanks to Michal Hlavinka)
- Corrected the license tag (thanks to Michal Hlavinka)
- Removed the arc4random.c file (upstream is phasing it out)

* Sat Feb 27 2010 Robert Scheck <robert@fedoraproject.org> 39c-1
- Upgrade to 39c and updated arc4random.c file

* Thu Aug 13 2009 Robert Scheck <robert@fedoraproject.org> 39-1
- Upgrade to 39 and updated arc4random.c file

* Sat Jul 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 38b-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Sun May 31 2009 Robert Scheck <robert@fedoraproject.org> 38b-1
- Upgrade to 38b

* Sun May 31 2009 Robert Scheck <robert@fedoraproject.org> 38-1
- Upgrade to 38 and updated arc4random.c file
- Used -combine (-fwhole-program) rather the old -j switch

* Sun Apr 05 2009 Robert Scheck <robert@fedoraproject.org> 37b-1
- Upgrade to 37b

* Mon Feb 23 2009 Robert Scheck <robert@fedoraproject.org> 36b-2
- Rebuild against gcc 4.4 and rpm 4.6

* Sun Dec 14 2008 Robert Scheck <robert@fedoraproject.org> 36b-1
- Upgrade to 36b and updated arc4random.c file

* Tue Dec 02 2008 Robert Scheck <robert@fedoraproject.org> 36-2
- Upstream patch for command hang/high cpu workload (#474115)

* Sat Oct 25 2008 Robert Scheck <robert@fedoraproject.org> 36-1
- Upgrade to 36

* Sat Jul 19 2008 Robert Scheck <robert@fedoraproject.org> 35b-1
- Upgrade to 35b

* Sun Jul 13 2008 Robert Scheck <robert@fedoraproject.org> 35-1
- Upgrade to 35

* Sat Apr 12 2008 Robert Scheck <robert@fedoraproject.org> 33d-1
- Upgrade to 33d

* Fri Apr 04 2008 Robert Scheck <robert@fedoraproject.org> 33c-1
- Upgrade to 33c and updated arc4random.c file

* Mon Mar 03 2008 Robert Scheck <robert@fedoraproject.org> 33-1
- Upgrade to 33

* Sun Feb 10 2008 Robert Scheck <robert@fedoraproject.org> 32-2
- Rebuild against gcc 4.3

* Sat Nov 10 2007 Robert Scheck <robert@fedoraproject.org> 32-1
- Upgrade to 32
- Solved fork problems in %%check (thanks to Thorsten Glaser)

* Mon Oct 15 2007 Robert Scheck <robert@fedoraproject.org> 31d-1
- Upgrade to 31d

* Wed Sep 12 2007 Robert Scheck <robert@fedoraproject.org> 31c-1
- Upgrade to 31c
- Added a buildrequirement to ed, added arc4random.c file

* Tue Sep 11 2007 Robert Scheck <robert@fedoraproject.org> 31b-1
- Upgrade to 31b
- Use script to get %%check happy (thanks to Thorsten Glaser)

* Sat Sep 08 2007 Robert Scheck <robert@fedoraproject.org> 31-1
- Upgrade to 31

* Tue Aug 28 2007 Robert Scheck <robert@fedoraproject.org> 30-2
- Updated the license tag according to the guidelines

* Sat Jul 28 2007 Robert Scheck <robert@fedoraproject.org> 30-1
- Upgrade to 30

* Sat Jul 14 2007 Robert Scheck <robert@fedoraproject.org> 29g-1
- Upgrade to 29g

* Sun Jun 03 2007 Robert Scheck <robert@fedoraproject.org> 29f-1
- Upgrade to 29f
- Initial spec file for Fedora and Red Hat Enterprise Linux
