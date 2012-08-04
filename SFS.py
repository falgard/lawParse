#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

# Libs
import os

# Own libs
import Source
import Util
from Dispatcher import Dispatcher
from DataObjects import CompoundStructure
from TextReader import TextReader

__moduledir__ = "sfs"

class Forfattning():
	pass

class Rubrik():
	pass

class Stycke(CompoundStructure):
	def __init__(self, *args, **kwargs):
		pass

class RevokedDoc(Exception):
	"""Thrown when a doc that is revoked is being parsed"""

class NotSFS(Exception):
	"""Thrown when not a real SFS document is being parsed as a SFS document"""
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

		# 1: Filter out stuff that's not a proper SFS document
		# They will look something like "N1992:31"
		if '/N' in f:
			raise NotSFS()

		# 2: If the outfile is newer then all ingoing files, don't parse.
		#TODO: Add force option to config? 
		fList = []
		for x in files.keys():
			if self._fileUpToDate(fList, filename):
				return
			else:
				fList.extend(files[x])

		# 3: Skip the documents that have been revoked and are marked
		# as "Författningen är upphävd/skall upphävas"
		t = TextReader(files['sfsr'][0],encoding="iso-8859-1")
		try:
			t.cuepast(u'<i>Författningen är upphävd/skall upphävas: ')
			datestr = t.readto(u'</i></b>')
			if datetime.strptime(datestr, '%Y-%m-%d') < datetime.today():
				#TODO: log 'expired' document
				raise RevokedDoc()
		except IOError:
			pass

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