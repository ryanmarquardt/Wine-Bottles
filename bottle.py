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
		}
		self.conf_data = rexec(confpath, g)
		
	def run(self, *args):
		args = list(args)
		print args
		if not args:
			args.append('wine')
			EXE = winepath(self.conf_data['EXE'], self.env['WINEPREFIX'])
			args.append(EXE)
			path = os.path.join(self.winepath, 'wine')
		elif args[0] in self.conf_data and hasattr(self.conf_data[args[0]], '__call__'):
			f = self.conf_data[args[0]]
			f(*args[1:])
			return
		else:
			path = args[0]
		env = {}
		env.update(os.environ)
		env.update(self.env)
		print 'executing:', ' '.join(map(repr,args))
		print 'os.execvpe(path, args, env)'

if __name__=='__main__':
	import sys
	b = Bottle(sys.argv[1])
	b.run(*sys.argv[2:])
