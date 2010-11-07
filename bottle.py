#!/usr/bin/env python

import os
import subprocess


def winepath(path, prefix=None, wpath=None):
	env = os.environ
	if wpath:
		env['PATH'] = ':'.join([wpath, env['PATH']])
	if prefix:
		env['WINEPREFIX'] = prefix
	return subprocess.Popen(['winepath', '-u', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env).communicate()[0][:-1]

def winepath(path, prefix=os.path.expanduser('~/.wine'), wpath=None):
	final = os.path.join(prefix, 'dosdevices')
	parts = []
	head, tail = os.path.split(path)
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

def rexec(path, globals0=None):
	l = {}
	if globals0 is None:
		globals0 = globals()
	execfile(path, globals0, l)
	return l

def bash(*args):
	subprocess.Popen(['bash'], stdin=subprocess.PIPE).communicate(' '.join(map(repr,args)))

class Bottle(object):
	def __init__(self, name, bottlepath='~/.bottles'):
		self.path = os.path.expanduser(bottlepath)
		self.wineprefix = os.path.join(self.path, name)
		self.parse_conf()
		print self.conf_data
		self.env = {}
		self.env['WINEPREFIX'] = self.wineprefix
		if 'WINEVERSION' in self.conf_data:
			self.winepath = os.path.join(self.path, '.wineversions', self.conf_data['WINEVERSION'], 'usr', 'bin')
			self.env['PATH'] = ':'.join([self.winepath, os.environ['PATH']])
		else:
			self.winepath = '/usr/bin'
		if 'VARS' in self.env:
			for var in self.conf_data['VARS']:
				self.env[var] = self.conf_data[var]
		
	def parse_conf(self):
		confpath = os.path.join(self.wineprefix, 'bottle-settings')
		g = {
			'run': self.run,
			'bash': bash,
			'winepath': lambda x:winepath(x, self.wineprefix),
			'WINEPREFIX': self.wineprefix,
		}
		if os.path.exists(confpath):
			#Read settings only if they exist
			self.conf_data = rexec(confpath, g)
		else:
			#Create settings file if they don't
			open(confpath, 'wb').close()
			self.conf_data = {}
		
	def run(self, *args):
		print args
		if not args:
			#Run the default command (var EXE) using wine
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
		os.execvpe(path, args, env)

if __name__=='__main__':
	import sys
	basename = os.path.basename(sys.argv[0])
	if basename in ('bottle', 'bottle.py'):
		name = sys.argv[1]
		args = sys.argv[2:]
	else:
		name = basename
		args = sys.argv[1:]
	b = Bottle(name)
	b.run(*args)
