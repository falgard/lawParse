#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Module that parse/extracts references to legal sources in plaintext"""

#Libs
import sys
import os
import re

#3rd party libs
from rdflib.Graph import Graph
from rdflib import RDFS, URIRef
from simpleparse.parser import Parser
from simpleparse.stt.TextTools.TextTools import tag

#Own libs
from Dispatcher import Dispatcher
import Util
from DataObjects import UnicodeStructure, PredicateType

SP_CHARSET = 'iso-8859-1'

class Link(UnicodeStructure):
	def __repr__(self):
		return u'Link(\'%s\',uri=%r)' % (unicode.__repr__(self),self.uri)

class LinkSubject(PredicateType, Link):
	pass

class NodeTree:
	"""Encapsulates the node structure from mx.TextTools in a tree interface"""
	def __init__(self, root, data, offset=0, isRoot=True):
		self.data = data
		self.root = root
		self.isRoot = isRoot
		self.offset = offset 

	def __getattr__(self, name):
		if name == 'text':
			return self.data.decode(SP_CHARSET)
		elif name == 'tag':
			return (self.isRoot and 'root' or self.root[0])
		elif name == 'nodes':
			res = []
			l = (self.isRoot and self.root[1] or self.root[3])
			if l:
				for p in l:
					res.append(NodeTree(p, self.data[p[1]-self.offset:p[2]-self.offset], p[1], False))
			return res
		else:
			raise AttributeError

class Reference:
	LAGRUM = 1
	KORTALAGRUM = 2
	FORESKRIFTER = 3

	reUriSegments 		= re.compile(r'([\w]+://[^/]+/[^\d]*)(\d+:(bih\.[_ ]|N|)?\d+([_ ]s\.\d+|))#?(K([a-z0-9]+)|)(P([a-z0-9]+)|)(S(\d+)|)(N(\d+)|)')
	reEscapeCompound 	= re.compile(r'\b(\w+-) (och) (\w+-?)(lagen|förordningen)\b', re.UNICODE)
	reEscapeNamed 		= re.compile(r'\B(lagens?|balkens?|förordningens?|formens?|ordningens?|kungörelsens?|stadgans?)\b', re.UNICODE)

	reDescapeCompound 	= re.compile(r'\b(\w+-)_(och)_(\w+-?)(lagen|förordningen)\b', re.UNICODE)
	reDescapeNamed 		= re.compile(r'\|(lagens?|balkens?|förordningens?|formens?|ordningens?|kungörelsens?|stadgans?)')
	reXmlCharref		= re.compile('&#\d+;')

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
		self.depth 	= 0

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
				self.baseUriAttrs = {'baseUri'	: m.group(1),
									 'law'		: m.group(2),
									 'chapter'	: m.group(6),
									 'section'	: m.group(8),
									 'piece'	: m.group(10),
									 'item'		: m.group(12)}
			else:
				self.baseUriAttrs = {'baseUri':baseUri}
		else:
			self.baseUriAttrs = {}

		fixedIndata = unicode(indata)
		
		if self.LAGRUM in self.args:
			fixedIndata = self.reEscapeCompound.sub(r'\1_\2_\3\4', fixedIndata)
			fixedIndata = self.reEscapeNamed.sub(r'|\1', fixedIndata)

		if isinstance(fixedIndata, unicode):
			fixedIndata = fixedIndata.encode(SP_CHARSET, 'xmlcharrefreplace')

		tagList = tag(fixedIndata, self.tagger,0,len(fixedIndata))
		res = []

		root = NodeTree(tagList, fixedIndata)
		for n in root.nodes:
			if n.tag in self.roots:
				self.clearState()
				res.extend(self.formatterDispatch(n))
			else:
				assert n.tag == 'plain', 'Tag is %s' % n.tag
				res.append(n.text)

			if self.currentLaw != None:
				self.lastLaw = self.currentLaw
			self.currentLaw = None

		if tagList[-1] != len(fixedIndata):
			#TODO: Add Error 
			raise ParseError, 'Parsed %s chars of %s (...%s...)' % (tagList[-1], len(indata), indata[(tagList[-1]-2):tagList[-1]+3])
		
		# Normalize the result, concat and remove '|'
		result = []
		for i in range(len(res)):
			if not self.reDescapeNamed.search(res[i]):
				node = res[i]
			else:
				if self.LAGRUM in self.args:
					text = self.reDescapeNamed.sub(r'\1', res[i])
					text = self.reDescapeCompound.sub(r'\1 \2 \3\4', text)
				if isinstance(res[i], Link):
					# A Link obj is immutable so we have to 
					# create a new and copy its attrs
					if hasattr(res[i], 'predicate'):
						node = LinkSubject(text, predicate=res[i].predicate, uri=res[i].uri)
					else:
						node = Link(text, uri=res[i].uri)
				else:
					node = text
			if (len(result) > 0 
				and not isinstance(result[-1], Link)
					and not isinstance(node, Link)):
				result[-1] += node
			else:
				result.append(node)

		for i in range(len(result)):
			if isinstance(result[i], Link):
				pass
			else:
				result[i] = self.reXmlCharref.sub(self.unescapeXmlCharref, result[i])

		return result

	def unescapeXmlCharref(self, m):
		return unichr(int(m.group(0)[2:-1]))

	def findAttrs(self, parts, extra={}):
		"""Creates a dict of attributes through a tree"""
		d = {}
		self.depth += 1
		if extra:
			d.update(extra)
		for part in parts:
			currentPartTag = part.tag.lower()
			if currentPartTag.endswith('refid'):
				if ((currentPartTag == 'singelsectionrefid') or 
					(currentPartTag == 'lastsectionrefid')):
					currentPartTag = 'sectionrefid'
				d[currentPartTag[:-5]] = part.text.strip()

			if part.nodes:
				d.update(self.findAttrs(part.nodes, d))

		self.depth -= 1

		if self.currentLaw and 'law' not in d:
			d['law'] = self.currentLaw
		if self.currentChapter and 'chapter' not in d:
			d['chapter'] = self.currentChapter
		if self.currentSection and 'section' not in d:
			d['section'] = self.currentSection
		if self.currentPiece and 'piece' not in d:
			d['piece'] = self.currentPiece

		return d

	def formatterDispatch(self, part):
		self.depth += 1
		if 'format' + part.tag in dir(self):
			formatter = getattr(self,'format'+part.tag)
			res = formatter(part)
			assert res != None, 'Custom formatter for %s didnt return anythin' % part.tag
		else:
			res = self.formatTokentree(part)

		self.depth -= 1
		return res

	def formatTokentree(self, part):
		res = []
		if (not part.nodes) and (not part.tag.endswith('RefID')):
			res.append(part.text)
		else:
			if part.tag.endswith('RefID'):
				res.append(self.formatGenericLink(part))
			elif part.tag.endswith('Ref'):
				res.append(self.formatGenericLink(part))
			else:
				for p in part.nodes:
					res.extend(self.formatterDispatch(p))
		return res

	def formatGenericLink(self, part, uriFormatter=None):
		try:
			uri = self.uriFormatter[part.tag](self.findAttrs([part]))			
		except KeyError:
			if uriFormatter:
				uri = uriFormatter(self.findAttrs([part]))	
			else:
				uri = self.sfsFormatUri(self.findAttrs([part]))
		except AttributeError:
			return part.text
		except:
			exc = sys.exc_info()
			return part.text

		if not uri:
			return part.text
		elif self.predicate:
			return LinkSubject(part.text, uri=uri, predicate=self.predicate)
		else:
			return Link(part.text, uri=uri)

	def clearState(self):
		self.currentLaw 	= None
		self.currentChapter	= None
		self.currentSection	= None
		self.currentPiece	= None

	def normalizeSfsId(self, sfsId):
		sfsId = re.sub(r'(\d+:\d+)\.(\d)', r'\1 \2', sfsId)
		return sfsId

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
				res = 'http://rinfo.lagrummet.se/publ/sfs/'
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
