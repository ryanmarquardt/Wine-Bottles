#!/usr/bin/env python

import os
import subprocess

import urllib2

VERSION='0.2.0'

def winepath(path, prefix=None, wpath=None):
	env = os.environ
	if wpath:
		env['PATH'] = ':'.join([wpath, env['PATH']])
	if prefix:
		env['WINEPREFIX'] = prefix
	return subprocess.Popen(['winepath', '-u', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).communicate()[0][:-1]

class WinePath(str):
	def __new__(self, path, prefix=None):
		if prefix is None:
			self.prefix = os.path.expanduser('~/.wine')
		else:
			self.prefix = prefix
		return str.__new__(self, path)
	
	def toUnix(self):
		final = os.path.join(self.prefix, 'dosdevices')
		parts = []
		head, tail = os.path.split(self)
		while head and tail:
			parts.insert(0, tail)
			head, tail = os.path.split(head)
		parts.insert(0, tail)
		while parts:
			dirs = os.listdir(final)
			p = parts.pop(0)
			for d in dirs:
				if d.lower() == p.lower():
					final = os.path.join(final, d)
					break
			else:
				#Non-existent path
				return os.path.join(final, p, *parts)
		return final
		
	def toWindows(self):
		path = os.path.abspath(self)
		devicedir = os.path.join(self.prefix, 'dosdevices')
		drives = dict((d, os.path.realpath(os.path.join(devicedir, d))) for d in os.listdir(devicedir) if not d.endswith('::'))
		for letter in drives:
			if path.startswith(drives[letter]):
				return os.path.join(letter, path[len(drives[letter]):])
		else:
			return path

#print WinePath('c:/Program Files/Microsoft Office', '/home/ryan/.bottles/office').toUnix()
#print WinePath('/home/ryan/Documents/doc.doc', '/home/ryan/.bottles/office').toWindows()

def winepath(path, prefix=os.path.expanduser('~/.wine'), wpath=None):
	pass
	
winepath = lambda path,prefix:WinePath(path,prefix).toUnix()

def rexec(path, globals0=None):
	l = {}
	if globals0 is None:
		globals0 = globals()
	execfile(path, globals0, l)
	return l

def bash(*args):
	subprocess.Popen(['bash'], stdin=subprocess.PIPE).communicate(' '.join(map(repr,args)))
	
def touch(path):
	head, tail = os.path.split(path)
	if os.path.exists(head) and not os.path.isdir(head):
		raise Exception("Oops, somebody's not a folder! %r" % head)
	else:
		os.makedirs(head)
	open(path, 'wb').close()

class Bottle(object):
	def __init__(self, bottlepath='~/.bottles'):
		self.path = os.path.expanduser(bottlepath)
		
	def open(self, name):
		self.wineprefix = os.path.join(self.path, name)
		self.env = {}
		self.env['WINEPREFIX'] = self.wineprefix
		self.parse_conf()
		
	def exists(self):
		return os.path.exists(self.confpath)
				
	def create(self):
		print 'CREATING BOTTLE'
		touch(self.confpath)
		self.run('wineboot', '-u')
		
	def parse_conf(self):
		self.confpath = os.path.join(self.wineprefix, 'bottle-settings')
		g = {
			'run': self.run,
			'bash': bash,
			'windowspath': lambda x:WinePath(x, self.wineprefix).toWindows(),
			'unixpath': lambda x:WinePath(x, self.wineprefix).toUnix(),
			'WINEPREFIX': self.wineprefix,
		}
		self.conf_data = rexec(self.confpath, g) if os.path.exists(self.confpath) else {}
		if 'WINEVERSION' in self.conf_data:
			self.winepath = os.path.join(self.path, '.wineversions', self.conf_data['WINEVERSION'], 'usr', 'bin')
			self.env['PATH'] = ':'.join([self.winepath, os.environ['PATH']])
		else:
			self.winepath = '/usr/bin'
		if 'VARS' in self.env:
			for var in self.conf_data['VARS']:
				self.env[var] = self.conf_data[var]
		
	def run(self, *args, **kwargs):
		debug=kwargs.get('debug', False)
		print args
		if not args:
			#Run the default command (var EXE) using wine
			if 'EXE' not in self.conf_data:
				raise Exception('No default program has been specified')
			EXE = winepath(self.conf_data['EXE'], self.wineprefix)
			args = ['wine', EXE]
			path = os.path.join(self.winepath, 'wine')
		elif args[0] in self.conf_data and hasattr(self.conf_data[args[0]], '__call__'):
			#Run a user-defined command
			f = self.conf_data[args[0]]
			f(*args[1:])
			return
		else:
			#Run whatever is on the command line
			path = args[0]
		env = {}
		env.update(os.environ)
		env.update(self.env)
		print 'executing:', ' '.join(map(repr,args))
		if not debug:
			os.execvpe(path, args, env)

USAGE="""
	-p --package         	Package a bottle for backup or distribution
	-i --install-version 	Downloads an older version of wine
"""

class WineVersionManager(object):
	def __init__(self):
		pass
		
	def install(self, version):
		pass
		
	def list(self):
		data = urllib2.urlopen('http://mulx.playonlinux.com/wine/linux-i386/LIST')
		return [line.split(';')[1] for line in data]
		
def STUB(*args):
	print 'STUB:', ' '.join(map(repr,args))

if __name__=='__main__':
	import sys
	import optparse
	
	parser = optparse.OptionParser(
		usage = "bottle.py [options] <bottle-name> <args...>",
		version = "%%prog %s" % VERSION,
		description = "With no arguments, runs the bottle's default command",
	)
	
	parser.add_option('-d', '--debug', action="store_true",
	 help="Run without actually doing anything")
	parser.add_option('-n', '--create', action='store_const', 
	 const='create', dest='action',
	 help="Creates a new bottle")
	parser.add_option('-c', '--configure', action='store_const',
	 const='configure', dest='action',
	 help="Runs winecfg in the bottle")
	parser.add_option('-p', '--package', action='callback', callback=STUB,
	 help="Package a bottle for backup or distribution")
	parser.add_option('-i', '--install-version', action='store',
	 dest='newversion', type='string', default='',
	 help="Download an older version of wine")
	parser.add_option('-l', '--list', action='store_const',
	 const='list', dest='action',
	 help="Show all bottles already created")
	parser.add_option('--list-versions', action='store_const',
	 const='listversions', dest='action',
	 help="List versions of wine available for download")
	
	parser.set_defaults(debug=False, action='run')
	opts, args = parser.parse_args()
	
	b = Bottle()
	
	#Some options don't take a bottle name
	if parser.values.action == 'list':
		print '\n'.join(sorted(filter(lambda x:x!='.wineversions', os.listdir(b.path))))
	elif parser.values.newversion:
		WineVersionManager().install(parser.values.newversion)
	elif parser.values.action == 'listversions':
		print '\n'.join(WineVersionManager().list())
	else:
		#Others do
		basename = os.path.basename(sys.argv[0])
		if basename in ('bottle', 'bottle.py'):
			if len(args) == 0:
				parser.print_help()
				exit(0)
			name = args.pop(0)
		else:
			name = basename
		print name, args
		b.open(name)
		if parser.values.action == 'create':
			b.create()
		elif parser.values.action == 'configure':
			b.run('winecfg')
		elif parser.values.action == 'run':
			if b.exists():
				b.run(*args, debug=opts.debug)
			else:
				raise Exception('Bottle %r not found' % name)
		else:
			raise Exception('Unexpected value for parser.values.action: %r' % parser.values.action)
