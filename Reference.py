#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Module that parse/extracts references to legal sources in plaintext"""

#Libs
import sys
import os
import re

#3rd party libs
from rdflib.Graph import Graph
from rdflib import RDFS
from simpleparse.parser import Parser

#Own libs
from Dispatcher import Dispatcher
import Util

class Reference:
	LAGRUM = 1
	KORTALAGRUM = 2
	FORESKRIFTER = 3

	reUriSegments = re.compile(r'([\w]+://[^/]+/[^\d]*)(\d+:(bih\.[_ ]|N|)?\d+([_ ]s\.\d+|))#?(K([a-z0-9]+)|)(P([a-z0-9]+)|)(S(\d+)|)(N(\d+)|)')

	def __init__(self, *args):
		scriptDir = os.getcwd()

		self.graph = Graph()
		n3File = Util.relpath(scriptDir + '/etc/sfs-extra.n3')
		self.graph.load(n3File, format='n3')

		self.roots = []
		self.uriFormatter = {}
		self.declare = ''
		self.namedLaws = {}
		self.loadEbnf(scriptDir + '/etc/base.ebnf')
		self.args = args
		
		if self.LAGRUM in args:
			prods = self.loadEbnf(scriptDir + '/etc/lagrum.ebnf')
			for p in prods: 
				self.uriFormatter[p] = self.sfsFormatUri
			self.namedLaws.update(self.getRelationship(RDFS.label))
			self.roots.append('sfsrefs')
			self.roots.append('sfsref')

		if self.KORTALAGRUM in args:
			# TODO: Fix korta lagrum also
			pass

		self.declare += 'root ::= (%s/plain)+\n' % '/'.join(self.roots)
		self.parser = Parser(self.declare, 'root')
		self.tagger = self.parser.buildTagger('root')

		#SFS specific settings
		self.currentLaw 		= None
		self.currentChapter 	= None
		self.currentSection 	= None
		self.currentPiece		= None
		self.lastLaw			= None
		self.currentNamedLaws	= {}

	def loadEbnf(self, file):
		"""Loads the syntax from a given EBNF file"""
		f = open(file)
		syntax = f.read()
		self.declare += syntax
		f.close()
		return [x.group(1) for x in re.finditer(r'(\w+(Ref|RefID))\s*::=', syntax)]

	def getRelationship(self, predicate):
		d = {}
		for obj, subj in self.graph.subject_objects(predicate):
			d[unicode(subj)] = unicode(obj)
		return d

	def parse(self, indata, baseUri='http://rinfo.lagrummet.se/publ/sfs/9999:999#K9P9S9P9',predicate=None):
		if indata == '':
			return indata
		self.predicate = predicate
		self.baseUri = baseUri
		if baseUri:
			m = self.reUriSegments.match(baseUri)
			if m:
				self.baseUriAttrs = {}
			else:
				self.baseUriAttrs = {'baseUri':baseUri}
		else:
			self.baseUriAttrs = {}


		return ['',]

	def sfsFormatUri(self, attrs):
		numMap = {u'första'	:'1',
				  u'andra'	:'2',
				  u'tredje'	:'3',
				  u'fjärde'	:'4',
				  u'femte'	:'5',
				  u'sjätte'	:'6',
				  u'sjunde'	:'7',
				  u'åttonde':'8',
				  u'nionde'	:'9'}
		
		keyMap = {u'lawref'	:'L',
				  u'chapter':'K',
				  u'section':'P',
				  u'piece'	:'S',
				  u'item'	:'N',
				  u'element':'O'}
		
		attrOrder = ['law', 'lawref', 'chapter', 'section', 'element', 'piece', 'item']

		if 'law' in attrs:
			if attrs['law'].startswith('http://'):
				res = ''
			else:
				res = 'http://rinfo.lagrummet.se/publ/sfs'
		else:
			if 'baseUri' in self.baseUriAttrs:
				res = self.baseUriAttrs['baseUri']
			else:
				res = ''

		resolveBase = True
		addFragment = False
		justInCase 	= None

		for key in attrOrder:
			if attrs.has_key(key):
				resolveBase = False
				val = attrs[key]
			elif (resolveBase and self.baseUriAttrs.has_key(key)):
				val = self.baseUriAttrs[key]
			else:
				val = None

			if val:
				if addFragment:
					res += '#'
					addFragment = False
				if (key in ['piece', 'itemnumeric', 'sentence'] and val in pieceMap):
					res += '%s%s' % (keyMap[key], pieceMap[val.lower()])
				else:
					if key == 'law':
						val = self.normalizeSfsId(val)
						val = val.replace(' ', '_')
						res += val
						addFragment = True
					else:
						if justInCase:
							res += justInCase
							justInCase = None
						val = val.replace(' ', '')
						val = val.replace('\n', '')
						val = val.replace('\r', '')
						res += '%s%s' % (keyMap[key], val)
			else:
				if key == 'piece':
					justInCase = 'S1'
		return res								
