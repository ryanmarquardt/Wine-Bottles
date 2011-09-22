#!/usr/bin/env python

import optparse
import re
import sys
from bottle import *

DEBUG = True

class Paths(object):
	def __init__(self, bottle):
		self.bottle = os.path.expanduser('~/.bottles/%s' % bottle)

	@property
	def resources(self):
		return os.path.join(self.bottle, 'resources')

	def disc(self, letter):
		return os.path.join(self.bottle, 'dosdevices', letter + ':')

class Desktop(dict):
	def go(self):
		pass

	def write(self, f):
		print >>f, '#!/usr/bin/env xdg-open\n'
		if 'Encoding' not in self:
			print >>f, 'Encoding=UTF-8'
		for k in self:
			key = k.title()
			if k.lower() == 'categories':
				value = self[k] if isinstance(self[k], basestring) else ';'.join(self[k])
			else:
				value = self[k]
			if value is not None:
				print >>f, '='.join((key, value))
		if 'Terminal' not in self:
			print >>f, 'Terminal=false'

		#template = '''[Desktop Entry]\nEncoding=UTF-8\nName={name}\nExec=bottle {exe}\nIcon={icon}\nTerminal=false\nType=Application\nCategories={cats}\nStartupNotify=false\n'''
		#open('%s.desktop' % self.name).write(template.format(name=title, exe=exe, icon=os.path.abspath(icon), cats=categories))

class Task(object):
	def __init__(self, paths, *args, **kwargs):
		self.args = args
		self.__dict__.update(kwargs)

	def __str__(self):
		return '%s(%s)' % (
			self.__class__.__name__,
			', '.join(['%s=%r' % i for i in self.__dict__.items()])
		)
	
	def go(self):
		raise NotImplementedError

class Command(Task):
	def __init__(self, paths, cmd, *args, **kwargs):
		self.paths = paths
		self.cmd = cmd
		self.args = args
		self.kwargs = kwargs
	
	def go(self):
		if DEBUG:
			print 'Running command %r %s %s' % (self.cmd, ' '.join(map(str,self.args)), ' '.join(['%s=%r' % i for i in self.kwargs.items()]))
		else:
			raise NotImplementedError

class Icon(Task):
	def __init__(self, paths, path=None, url=None, exe=None, name=1):
		self._paths = paths
		if url:    self.url = url
		elif exe:  self.exe, self.name = exe, name
		elif path: self._path = unixpath(path)

	@property
	def path(self):
		if hasattr(self, 'url'):
			return os.path.join(self._paths.resources, self.url.rpartition('/')[-1])
		elif hasattr(self, 'exe'):
			return os.path.join(self._paths.resources, '%s-%s.ico' % (self.exe, self.name))
		else:
			return WinePath(self._path, self._paths.bottle).toUnix()

	def go(self):
		if DEBUG:
			print 'Use icon from %r' % (self.path)
		else:
			raise NotImplementedError

#	def extractIco(self, exe, ico, type='group_icon', name=None):
#		args = ['wrestool', '-x', exe, '-o', ico, '--type', type]
#		if name:
#			args.extend(['--name', name])
#		subprocess.Popen(args).wait()
class InstallSource(Task):
	def __init__(self, paths, name, url=None, cd=None, **kwargs):
		self.paths = paths
		self.name = name
		if url:
			self.url = url
		elif cd:
			self.cd = cd
			self.copy_file = kwargs.pop('copy_file', False)
			self.copy_disk = kwargs.pop('copy_disk', False)

	@property
	def path(self):
		if hasattr(self, 'url'):
			return os.path.join(self.paths.resources, self.url.rpartition('/')[-1])
		elif hasattr(self, 'cd'):
			return os.path.join(self.paths.disc('d'), self.cd)

	def go(self):
		if DEBUG:
			print 'Use installation source at %r' % (self.path)
		else:
			raise NotImplementedError


class Desktop(Task):
	def __init__(self, paths, Name, Icon, **kwargs):
		self.paths = paths
		self.items = {
			'Name':Name,
			'Icon':Icon,
		}
		self.items.update(kwargs)

	@property
	def path(self):
		return os.path.join(self.paths.resources, '-'.join(re.split('\W', self.items['Name'])))

	def go(self):
		if DEBUG:
			print 'Write desktop file to %r' % (self.path)
		else:
			raise NotImplementedError

class Settings(object):
	def __str__(self):
		items = self.__dict__.copy()
		vars = filter(lambda x:re.match('[A-Z_]+', x), items.keys())
		lines = []
		for k in vars:
			v = items.pop(k)
			lines.append('%s=%r' % (k, v))
		lines.append('')
		for n in items.keys():
			lines.append('def %s(*argv):' % n)
			lines.extend(['\t'+l for l in items[n].split('\n')])
			lines.append('')
		return '\n'.join(lines)

class Installer(object):
	def __init__(self, default_bottle=None, name=None, version='0.0'):
		self.version = version
		self.bottle = default_bottle
		self.paths = Paths(self.bottle)
		self.name = name
		self.tasks = []
		self.settings = Settings()

	def __call__(self, function):
		self.installer = lambda:function(self)
		self.allowed_actions = set()
		self.installer()
		self.Go()
		
	def AddCommand(self, *args, **kwargs):
		self.tasks.append(Command(self.paths, args, kwargs))
		
	def AddIcon(self, **kwargs):
		i = Icon(self.paths, **kwargs)
		self.tasks.append(i)
		return i.path
		
	def AddInstallSource(self, **kwargs):
		'''AddInstallSource describes an installation source:
CDs:
  cd              - Path to an executable on a disc
  name            - Expected label of the disc
  copy_file=False - Installer should be copied to resource directory first
  copy_disc=False - Entire disc should be copied to resource directory first

URLs:
  url             - url to download for installation if it is not provided or
                      found in the resource directory
  name            - Common name used in help information
  extract=False   - Name of a program to extract the downloaded archive
'''
		s = InstallSource(self.paths, **kwargs)
		self.tasks.append(s)
		return s.path
			
	def AddDesktop(self, title, icon, exe=None, categories=('Application',)):
		d = Desktop(self.paths, 
			Name = title,
			Icon = icon,
			Exec = ' '.join(['bottle', self.name] + [exe] if exe else []),
			Categories = categories,
		)
		self.tasks.append(d)
		return d.path

	def Go(self, argv=None):
		class CustomHelpFormatter(optparse.IndentedHelpFormatter):
			def format_epilog(self, epilog):
				return '\n' + epilog + '\n'
		
		args = argv or sys.argv
		
		sources = filter(lambda x:isinstance(x, InstallSource), self.tasks)
		epilog_lines = []
		downloads = ['  %s (%s)' % (s.name, s.url) for s in sources if hasattr(s, 'url')]
		if downloads:
			epilog_lines.append('The following sources will be downloaded automatically if not provided:')
			epilog_lines.append('')
			epilog_lines.extend(downloads)
			epilog_lines.append('')
		cds = ['  [%s]:/%s' % (s.name, s.cd) for s in sources if hasattr(s, 'cd')]
		if cds:
			epilog_lines.append('The following install discs are required for installation to proceed:')
			epilog_lines.append('')
			epilog_lines.extend(cds)
			epilog_lines.append('')
			epilog_lines.append('Alternatively, you may provide a path to these files as arguments to this program.')
			epilog_lines.append('')
		
		epilog = '\n'.join(epilog_lines)
		usage = ' '.join(["%prog [options]"] + ["<%s>" % s.name for s in sources])	
		parser = optparse.OptionParser(
			formatter = CustomHelpFormatter(),
			usage = usage,
			version = "%%prog %s" % self.version,
			description = '''Installs '{name}' in its own wine folder.'''.format(name=self.name),
			epilog = epilog,
		)
		
		b = Bottle()
		b.open(self.name)
		
		parser.add_option('-b', '--bottle', action="store", default=self.bottle,
		 help="Install into bottle NAME instead of '%default'", metavar='NAME')
		parser.add_option('-d', '--desktop', action="store",
		 default=os.path.expanduser('~/.local/share/applications'),
		 help="Place links to any desktop files in PATH", metavar='PATH')
		
		parser.print_version()
		opts, args = parser.parse_args(args)
		self.link_desktops = opts.desktop
		
		try:
			b.create()
		except OSError:
			print 'Bottle folder already exists'
		
		for task in self.tasks:
			task.paths = Paths(opts.bottle)
			task.go()
