#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Base class for Parser (and unimplemented Downloader)"""

#Libs
import os
import sys
import re

#3rd party libs
from configobj import ConfigObj
from rdflib import RDFS
from rdflib.Graph import Graph
from genshi.template import TemplateLoader

#Own libs
import Util

__scriptDir__ = os.getcwd()

class ParseError(Exception):
	pass

class Downloader(object):
	pass

class Parser(object):
	"""Abstract base class for a document"""

	reNormalizedSpace = re.compile(r'\s+',).sub

	def __init__(self):
		self.authRec = self.loadAuthRec(__scriptDir__ + "/etc/authrec.n3")

	def Parse(self):
		raise NotImplementedError

	def generateXhtml(self, meta, body, registry, module, globals):
		"""Create a XTHML representation of the document"""
		loader = TemplateLoader(['.', os.path.dirname(__file__)],
								variable_lookup='lenient')
		t = loader.load('etc/%s.template.xht2'%module)
		stream = t.generate(meta=meta, body=body, registry=registry, **globals)

		try:
			res = stream.render()
		except Exception, e:
			raise
		if 'class="warning"' in res:
			start = res.index('class="warning">')
			end = res.index('</',start+16)
			msg = Util.normalizedSpace(res[start+16:end].decode('utf-8'))

		return res

	def loadAuthRec(self, n3File):
		"""Load a RDF graph with authority posts in n3-format"""
		g = Graph()
		n3File = Util.relpath(n3File)
		g.load(n3File, format='n3')
		d = {}
		for uri, label in g.subject_objects(RDFS.label):
			d[unicode(label)] = unicode(uri)
		return d

	def findAuthRec(self, label):
		"""Given a string that refers to some type of organisation, person etc 
		return a URI for that"""
		keys = []
		for (key, value) in self.authRec.items():
			if label.lower().startswith(key.lower()):
				return self.storageUri(value)
			else:
				keys.append(key)

		#TODO: Add 'fuzz' to find close matches.
		#fuzz = difflib.get_close_matches(label, keys, 1, 0.8) ...

	def storageUri(self, value):
		return value.replace(" ", '_')

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

	def _fileUpToDate(self, infiles, outfile):
		"""Check if the outfile is up-to-date, then there's no need to regenerate."""
		if not os.path.exists(outfile): 
			return False
		for i in infiles:
			#TODO: Add lib for timeing!
			if os.path.exsits(i) and os.stat(i).st_mtime > os.stat(outfile).st_mtime:
				return False
		return True

	def _htmlName(self, f):
		"""Return a XHTML file name for the given file"""
		if not isinstance(f, unicode):
			raise Exception("WARNING: _htmlName called with non unicode name")
		return u'%s/%s/generated/%s.html' % (self.baseDir, self.moduleDir, f)
		
	def _xmlName(self, f):
		"""Returns a XML file name for the given file"""
		if not isinstance(f, unicode):
			raise Exception("WARNING: _xmlName called with non unicode name")
		return u'%s/%s/parsed/%s.xht2' % (self.baseDir, self.moduleDir, f)