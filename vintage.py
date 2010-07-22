#!/usr/bin/env python

import os
import re
import subprocess
import sys
import tempfile
import urllib2

url='http://wine.budgetdedicated.com/archive/'
local=os.path.expanduser('~/.bottles/.wineversions')

def versions(arch='i386',distro='ubuntu'):
	html = urllib2.urlopen(url + "index.html").read()
	urls = {}
	for match in re.finditer(r'<a href=\"(%s/.*?/wine_(?P<version>.*?)~winehq.*?%s.deb)\">' % (distro,arch), html):
		if match.group('version') not in urls:
			urls[match.group('version')] = match.expand(url + '\\1')
	return urls

def is_installed(version):
	return os.path.isdir(os.path.join(local,version))

def system(*args):
	print ' '.join(args)
	return subprocess.Popen(args).wait()

def install(version):
	url = versions()[version]
	deb = tempfile.NamedTemporaryFile(suffix='.deb', delete=False)
	deb.close()
	system('wget', url, '-q', '-O', deb.name)
	system('dpkg-deb', '-x', deb.name, os.path.join(local, version))
	os.unlink(deb.name)

def depend(version):
	if not is_installed(version):
		install(version)

if len(sys.argv) > 1:
	depend(sys.argv[1])
else:
	print '\n'.join(sorted(versions().keys(),reverse=True))
