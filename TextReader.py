#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Class for reading text files by line, paragraph, page etc."""

import os
import codecs

class TextReader:
	UNIX = '\n'

	def __init__(self, filename=None, ustring=None, encoding=None, linesep=None):
		if not filename and not ustring:
			raise TypeError("No filename or ustring specified")

		self.closed = False
		self.mode = "r+"
		self.name = filename
		self.newlines = None
		self.softspace = 0

		if encoding:
			self.encoding = encoding
		else:
			self.encoding = 'ascii'

		if linesep:
			self.linesep = linesep
		else:
			self.linesep = os.linesep

		self.autostrip = False
		self.autodewrap = False
		self.expandtabs = True
		#TODO: Add extra options for iteration

		if filename:
			self.f = codecs.open(self.name, "rb", encoding)
			chunks = []
			chunk = self.f.read(1024*1024)
			while (chunk):
				chunks.append(chunk)
				chunk = self.f.read(1024*1024)
			self.data = "".join(chunks)
			self.f.close()
		else:
			assert(isinstance(ustring,unicode))
			self.data = ustring

		self.currpos = 0
		self.maxpos = len(self.data)
		self.lastread = u''

	def __process(self, s):
		if self.autostrip:
			s = s.strip()
		if self.autodewrap:
			s = s.replace(self.linesep, " ")
		if self.expandtabs:
			s = s.expandtabs(8)
		return s

	def cue(self, string):
		idx = self.data.find(string, self.currpos)
		if idx == -1:
			raise IOError("Could not find %r in the file" % string)
		self.currpos = idx

	def cuepast(self, string):
		self.cue(string)
		self.currpos += len(string)

	def readto(self, string):
		idx = self.data.find(string, self.currpos)
		if idx == -1:
			raise IOError("Could not find %r in file" % string)
		res = self.data[self.currpos:idx]
		self.currpos = idx
		return self.__process(res)