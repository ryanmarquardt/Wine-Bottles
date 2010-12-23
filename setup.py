#!/usr/bin/env python

from distutils.core import setup
import os

def find(path='.'):
	r = []
	for f in os.listdir(path):
		if os.path.isdir(f):
			r.extend(find(f))
		else:
			r.append(os.path.join(path, f))
	return r

setup(name='winebottles', version='0.2.1',
	author='Ryan Marquardt',
	author_email='ryan.marquardt@gmail.com',
	description='WineBottles',
	url='http://orbnauticus.github.org/winebottles',
	license='Simplified BSD License',
	scripts=['bottle'] + find('installers'),
	packages=['bottle'],
)
