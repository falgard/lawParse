#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Class for reading text files by line, paragraph, page etc."""

import os
import codecs
import copy

class TextReader:
	UNIX = '\n'
	DOS = '\r\n'
	MAC = '\r'

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
		self.iterFunc = self.readLine
		self.iterArgs = []
		self.iterKwargs = {}

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

		self.currPos = 0
		self.maxpos = len(self.data)
		self.lastread = u''

	def __iter__(self):
		return self

	def __find(self, delimiter, startPos):
		idx = self.data.find(delimiter, startPos)
		if idx == -1:
			res = self.data[startPos:]
			newPos = startPos + len(res)
		else:
			res = self.data[startPos:idx]
			newPos = idx + len(delimiter)
		return (res, newPos)

	def __process(self, s):
		if self.autostrip:
			s = s.strip()
		if self.autodewrap:
			s = s.replace(self.linesep, " ")
		if self.expandtabs:
			s = s.expandtabs(8)
		return s

	def next(self):
		oldPos = self.currPos
		res = self.__process(self.iterFunc(*self.iterArgs, **self.iterKwargs))
		if self.currPos == oldPos:
			raise StopIteration
		else:
			return res

	def readLine(self, size=None):
		return self.readChunk(self.linesep)

	def cue(self, string):
		idx = self.data.find(string, self.currPos)
		if idx == -1:
			raise IOError("Could not find %r in the file" % string)
		self.currPos = idx

	def cuepast(self, string):
		self.cue(string)
		self.currPos += len(string)

	def readTo(self, string):
		idx = self.data.find(string, self.currPos)
		if idx == -1:
			raise IOError("Could not find %r in file" % string)
		res = self.data[self.currPos:idx]
		self.currPos = idx
		return self.__process(res)

	def readParagraph(self):
		return self.readChunk(self.linesep * 2)

	def readChunk(self, delimiter):
		(self.lastread, self.currPos) = self.__find(delimiter, self.currPos)
		return self.__process(self.lastread)

	def getReader(self, callableObj, *args, **kwargs):
		"""Treats the result of a read, peek or prev method as a new
		TextReader. Useful to process pages in page-oriented documents"""
		res = callableObj(*args, **kwargs)
		clone = copy.copy(self)
		clone.data = res
		clone.currPos = 0
		clone.maxpos = len(clone.data)
		return clone

	def getIterator(self, callableObj, *args, **kwargs):
		self.iterFunc = callableObj
		self.iterArgs = args
		self.iterKwargs = kwargs
		return self