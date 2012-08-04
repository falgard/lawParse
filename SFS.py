#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Libs
import os

# Own libs
import Source
import Util
from Dispatcher import Dispatcher
from DataObjects import CompoundStructure

__moduledir__ = "sfs"

class Forfattning():
	pass

class Rubrik():
	pass

class Stycke(CompoundStructure):
	def __init__(self, *args, **kwargs):
		pass


class SFSParser(Source.Parser):

	def __init__(self):
		Source.Parser.__init__(self)

	def Parse(self, f, files):
		return 

class SFSController(Source.Controller):
	
	__parserClass = SFSParser

	## Controller Interface ##

	def Parse(self, f, v=False):
			
		f = f.replace(":", "/")
		files = {'sfst':self.__listfiles('sfst',f), 
				 'sfsr':self.__listfiles('sfsr',f)}
		if (not files['sfst'] and not files['sfsr']):
			raise Source.NoFiles("No files found for %s" % f)
		filename = self._xmlName(f)

	# Three checks before we start to parse

	# 1: 

	# 2: 

	# 3: 

	# Actual parsing begins here.
	#p = SFSParser()


	def ParseAll(self):
		dlDir = os.path.sep.join([self.baseDir, u'sfs', 'dl', 'sfst'])
		self._runMethod(dlDir, 'html', self.Parse)
		
	## Methods that overrides Controller methods ##

	def _get_module_dir(self):
		return __moduledir__	

	def __listfiles(self, source, name):
		"""Given a SFS id returns filenames from the dir that matches the id. 
		For laws that are broken up in _A and _B, both are returned"""
		tmp = "%s/sfs/dl/%s/%s%%s.html" % (self.baseDir, source, name)
		return [tmp%f for f in ('', '_A','_B') if os.path.exists(tmp%f)]