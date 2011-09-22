#!/usr/bin/env python

import os
import platform
import subprocess
import urllib2

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

def download(url, dst=None):
	if dst:
		size = 1024
		partname = '.%s.part' % dst
		try:
			data = urllib2.urlopen(url)
			with open(partname, 'wb') as dest:
				buffer = data.read(size)
				while buffer:
					dest.write(d)
					buffer = data.read(size)
		finally:
			os.rename(partname, dst)
	else:
		return urllib2.urlopen(url).read()

class WorkingDir(object):
	def __init__(self, path):
		self.oldpath = os.getcwd()
		self.newpath = path
		
	def __enter__(self):
		os.chdir(self.newpath)
		return self.newpath
		
	def __exit__(self, exc_type, exc_value, traceback):
		os.chdir(self.oldpath)

class WinePath(str):
	def __new__(self, path, prefix=None):
		self.prefix = prefix or os.path.expanduser('~/.wine') 
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

class Bottle(object):
	def __init__(self, bottlepath='~/.bottles'):
		self.path = os.path.expanduser(bottlepath)
		
	def open(self, name):
		self.name = name
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
			
	def package(self):
		tar = ['tar', '-C', self.path, '-cv', name]
		subprocess.Popen(tar).communicate()
		
	def parse_conf(self):
		self.confpath = os.path.join(self.wineprefix, 'bottle-settings')
		g = {
			'run': self.run,
			'arch': platform.machine(),
			'execute': self.execute,
			'bash': bash,
			'windowspath': lambda x:WinePath(x, self.wineprefix).toWindows(),
			'unixpath': lambda x:WinePath(x, self.wineprefix).toUnix(),
			'WINEPREFIX': self.wineprefix,
			'download': download,
			'WorkingDir': WorkingDir,
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
		
	def get_environment(self, *args, **kwargs):
		print args
		##TODO: Check if version is installed and download if necessary
		cwd = kwargs.get('cwd', '.')
		if not args:
			#Run the default command (var EXE) using wine
			if 'EXE' not in self.conf_data:
				raise Exception('No default program has been specified')
			EXE = WinePath(self.conf_data['EXE'], self.wineprefix).toUnix()
			args = ['wine', EXE]
			path = os.path.join(self.winepath, 'wine')
			if self.conf_data.get('CHDIR', False):
				cwd = os.path.split(EXE)[0]
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
		return path, args, env, cwd
		
	def execute(self, *args, **kwargs):
		debug=kwargs.get('debug', False)
		data = self.get_environment(*args, **kwargs)
		if data:
			path, args, env, cwd = data
			print 'executing:', ' '.join(map(repr,args))
			print 'in dir', cwd
			if not debug:
				os.chdir(cwd)
				os.execvpe(path, args, env)
			
	def run(self, *args, **kwargs):
		debug=kwargs.get('debug', False)
		data = self.get_environment(*args, **kwargs)
		if data:
			path, args, env, cwd = data
			print 'running:', ' '.join(map(repr,args))
			print 'in dir', cwd
			if not debug:
				return subprocess.Popen(args, executable=path, env=env, cwd=cwd).wait()

class WineVersionManager(object):
	def __init__(self, location):
		self.bottles = location
		self.location = os.path.join(location, '.wineversions')
		
	def install(self, version):
		with WorkingDir(self.location):
			if not os.path.exists('wine-%s.tar.bz2' % version):
				urltemplate = 'http://mulx.playonlinux.com/wine/linux-i386/PlayOnLinux-wine-%s.pol'
				print 'download', urltemplate % version
				download(urltemplate % version)
			untar = ['tar', '-xvjp', '--exclude=files', '--exclude=playonlinux',
			 '--transform', 's|wineversion|.|',
			 '-f', 'wine-%s.tar.bz2' % version]
			subprocess.Popen(untar).communicate()

	def list(self):
		data = urllib2.urlopen('http://mulx.playonlinux.com/wine/linux-i386/LIST')
		return [line.split(';')[1] for line in data]
