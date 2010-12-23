#!/usr/bin/env python

import optparse
from bottle import *

class Icon(object):
	pass
	
class InstallCommand(object):
	pass

class Desktop(object):
	pass

class Installer(object):
	def __init__(self, name):
		bottle.__init__(self)
		bottle.open(self, name)
		bottle.create(self)
		self.install = []
		self.desktops = []
		self.icos = {}
		self.settings = ''
		
	def AddCommand(self, cmd, *args, **kwargs):
		self.install.append((cmd, args, kwargs))
		
	def AddIco(self, key, file=None, exe=None, name=None):
		self.icos[key] = (file,exe,name)
		
	def download(self, url, dest):
		download(url, dest)
			
	def settings(self, data):
		#TODO
		pass
			
	def extractIco(self, exe, ico, type='group_icon', name=None):
		args = ['wrestool', '-x', exe, '-o', ico, '--type', type]
		if name:
			args.extend(['--name', name])
		subprocess.Popen(args).wait()
	
	def AddDesktop(self, title, icon, exe=None, categories='Application;'):
		if exe:
			exe = ' '.join([self.name, exe])
		else:
			exe = self.name
		template = '''[Desktop Entry]
Encoding=UTF-8
Name=%s
Exec=bottle %s
Icon=%s
Terminal=false
Type=Application
Categories=%s
StartupNotify=false
''' % (title, exe, os.path.abspath(icon), categories)
		open('%s.desktop' % self.name).write(template)

	def Go(self, argv):
		parser = optparse.OptionParser(
			usage = "%prog [options] <bottle-name> <args...>",
			version = "%%prog %s" % VERSION,
			description = '''With no options, runs installation of the program
If source arguments are needed and are not provided on the command line, they
will be prompted for.''',
		)
		
		b = Bottle()
		b.open(self.name)
		
		parser.add_option('-d', '--desktop', action="store",
		 help="Write desktop file(s) to PATH", metavar='PATH')
		parser.add_option('-s', '--settings', action='store_true', 
		 help="Write/restore default bottle-settings file")
		parser.add_option('-i', '--icons', action='store_true',
		 help="Retrieve all icons")
		
		opts, args = parser.parse_args(argv)
		
		if not any([parser.values.desktop, parser.values.settings, parser.values.icons]):
			parser.values.desktop = b.wineprefix
			parser.values.settings = True
			parser.values.icons = True
		
		if parser.values.desktop:
			self.CreateDesktops(parser.values.desktop)
		if parser.values.settings:
			#self.
			pass
		
		#Some options don't take a bottle name
		if parser.values.action == 'list':
			print '\n'.join(sorted(filter(lambda x:x!='.wineversions', os.listdir(b.path))))
		elif parser.values.newversion:
			WineVersionManager(b.path).install(parser.values.newversion)
		elif parser.values.action == 'listversions':
			print '\n'.join(WineVersionManager(b.path).list())
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
			elif parser.values.package:
				b.package()
			elif parser.values.action == 'run':
				if b.exists():
					b.execute(*args, debug=opts.debug)
				else:
					raise Exception('Bottle %r not found' % name)
			else:
				raise Exception('Unexpected value for parser.values.action: %r' % parser.values.action)
			
			parser = optparse.OptionParser(
				usage=""
			)
			
			WriteSettings = True
			RunInstall = True
			ExtractIcos = True
			CreateDesktops = True
			if RunInstall:
				for cmd,args,kwargs in self.install:
					print cmd, args, kwargs
					#self.run(cmd, *args, **kwargs)
			if ExtractIcos:
				for key in self.icos:
					file,exe,name = self.icos[key]
					if file:
						self.icos[key] = file
					else:
						subprocess.Popen(['wrestool', '-x', exe, '--type=group_icon', '--name', name, '-o', key]).wait()
						self.icos[key] = key
			if WriteSettings:
				with open(os.path.join(self.wineprefix, 'bottle-settings'), 'wb') as bs:
					bs.write(data)
			if CreateDesktops:
				self.WriteDesktop()
				for desktop in self.desktops:
					#TODO
					pass
		
