#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

#Libs
import os, sys

#3rd party libs
from configobj import ConfigObj

#Own libs
import Util

class Downloader(object):
	pass

class Parser(object):
	pass

class Controller(object):
	def __init__(self):
		self.moduleDir = self._get_module_dir()
		self.config = ConfigObj(os.path.dirname(__file__)+"/conf.ini")
		self.baseDir = os.path.dirname(__file__)+os.path.sep+self.config['datadir']

	## Controller Interface def. Subclasses must implement these ##
	
	def ParseAll(self):
		"""Parse all the legal documents that we have downloaded"""
		#TODO: Fixme
		dlDir = os.path.sep.join([self.baseDir, self.moduleDir, u'dl'])
		self._runMethod(dlDir, 'html', self.Parse)
	
	## Useable functions for subclasses, can be overriden ##

	def _trimFileName(self, files):
		"""Transforms a filename to a id, foo/bar/sfs/01.txt becomes sfs/01"""
		for f in files:
			fileName = "/".join(os.path.split(os.path.splitext(
				os.sep.join(os.path.normpath(Util.relpath(f)).split(os.sep)[-2:]))[0]))
			if not fileName:
				continue
			else:
				yield fileName


	def _runMethod(self, dir, suffix, method):
		files = self._trimFileName(Util.listDirs(dir, suffix, reverse=True))		
		for f in files:
			try:
				method(f)
			except KeyboardInterrupt:
				raise

	def _xmlName(self, f):
		"""Returns a XHTML file name for the given file"""
		if not isinstance(f, unicode):
			raise Exception("WARNING: _xmlName called with non unicode name")
		return u'%s/%s/parsed/%s.xht2' % (self.baseDir, self.moduleDir, f)