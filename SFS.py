#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

#Libs
import os
import sys
import re
import codecs
import htmlentitydefs
from tempfile import mktemp
from datetime import date, datetime

#3rd party libs
from rdflib import Namespace, RDFS

#Own libs
import Source
from Reference import Reference
import Util
from Dispatcher import Dispatcher
from DataObjects import CompoundStructure, MapStructure, \
	 UnicodeStructure, PredicateType, DateStructure
from TextReader import TextReader

__moduledir__ = "sfs"

class Forfattning():
	pass

class Rubrik():
	pass

class Stycke(CompoundStructure):
	def __init__(self, *args, **kwargs):
		pass

class Register(CompoundStructure):
	"""Meta data regarding the documnet and its changes"""
	def __init__(self, *args, **kwargs):
		self.rubrik = kwargs['rubrik'] if 'rubrik' in kwargs else None
		super(Register, self).__init__(*args, **kwargs)

class Registerpost(MapStructure):
	#TODO: Is this needed??
	pass

class DateSubject(PredicateType, DateStructure):
	pass

class UnicodeSubject(PredicateType, UnicodeStructure):
	pass

class RevokedDoc(Exception):
	"""Thrown when a doc that is revoked is being parsed"""
	pass
class NotSFS(Exception):
	"""Thrown when not a real SFS document is being parsed as a SFS document"""
	pass

DCT = Namespace(Util.ns['dct'])
XSD = Namespace(Util.ns['xsd'])
RINFO = Namespace(Util.ns['rinfo'])

class SFSParser(Source.Parser):

	def __init__(self):
		self.lagrumParser = Reference(Reference.LAGRUM)
		self.currentSection = u'0'
		Source.Parser.__init__(self)

	def Parse(self, f, files):
		self.id = f 
		timestamp = sys.maxint
		for filelist in files.values():
			for file in filelist:
				if os.path.getmtime(file) < timestamp:
					timestamp = os.path.getmtime(file)
		reg = self._parseSFSR(files['sfsr'])
		
		#Extract the plaintext and create a intermediate file for storage
		try:
			plaintext = self._extractSFST(files['sfst'])
			txtFile = files['sfst'][0].replace('.htlm', '.txt').replace('dl/sfst', 'intermediate')
			Util.checkDir(txtFile)
			tmpFile = mktemp()
			f = codecs.open(tmpFile, 'w', 'iso-8859-1')
			f.write(plaintext + '\r\n')
			f.close()
			Util.replaceUpdated(tmpFile, txtFile)
			#print reg
			#(meta, body) = self._parseSFST(txtFile, reg)
			#TODO: Add patch handling? 

		except IOError:
			#TODO: Add Warning extracting plaintext failed

			# TODO: Create Forfattningsinfo + forfattning from 
			# what we know from the SFSR data 
			pass

		#Add extra info 

	#Meta data found in both SFST header and SFST data
	labels = {u'Ansvarig myndighet':		DCT['creator'],
			  u'SFS-nummer':				RINFO['fsNummer'],
			  u'SFS nr':					RINFO['fsNummer'],
			  u'Departement/ myndighet': 	DCT['creator'],
			  u'Utgivare':					DCT['publisher'],
			  u'Rubrik':					DCT['title'],
			  u'Utfärdad':					RINFO['utfardandedatum'],
			  u'Ikraft':					RINFO['Ikrafttradandesdatum'],
			  u'Observera':					RDFS.comment,
			  u'Övrigt':					RDFS.comment,
			  u'Ändring införd':			RINFO['konsolideringsunderlag']
	}


	def _parseSFSR(self, files):
		"""Parse the SFSR registry with all changes from HTML files"""
		allAttr = []
		r = Register()
		for f in files:
			soup = Util.loadSoup(f)
			r.rubrik = Util.elementText(soup.body('table')[2]('tr')[1]('td')[0])
			changes = soup.body('table')[3:-2]
			#print changes
			for table in changes:
				kwargs = {'id': 'undefined',
						  'uri': u'http://rinfo.lagrummet.se/publ/sfs/undefined'}
				rp = Registerpost(**kwargs) #TODO: Is this needed?
				for row in table('tr'):
					key = Util.elementText(row('td')[0])
					if key.endswith(':'):
						key = key [:-1]
					if key == '': 
						continue
					val = Util.elementText(row('td')[1]).replace(u'\xa0',' ')
					if val != '':
						if key == u'SFS-nummer':
							if val.startswith('N'):
								raise NotSFS()
							if len(r) == 0:
								startNode = self.lagrumParser.parse(val)[0]
								if hasattr(startNode, 'uri'):
									docUri = startNode.uri
								#else:
									#TODO: Log warning, can't read the SFS nr
							rp[key] = UnicodeSubject(val, predicate=self.labels[key])
							rp.id = u'L' + val #Starts with L cause NCNames has to start with a letter
							startNode = self.lagrumParser.parse(val)[0]
							if hasattr(startNode, 'uri'):
								rp.uri = startNode.uri
							#else:
								#TODO: Log warning, can't read the SFS nr

						elif key == u'Ansvarig myndighet':
							try: 
								authRec = self.findAuthRec(val)
								rp[key] = LinkSubject(val, uri=unicode(authRec[0]),
													  predicate=self.labels[key])
							except Exception, e:
								rp[key] = val
						elif key == u'Rubrik':
							rp[key] = UnicodeSubject(val, predicate=self.labels[key])
						elif key == u'Observera':
							if u'Författningen är upphävd/skall upphävas: ' in val:
								if datetime.strptime(val[41:51], '%Y-%m-%d') < datetime.today():
									raise RevokedDoc()
							rp[key] = UnicodeSubject(val, predicate=self.labels[key])
						elif key == u'Ikraft':
							rp[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
						elif key == u'Omfattning':
							rp[key] = []
							#TODO
							#
							# for ...
						elif key == u'F\xf6rarbeten':
							#TODO
							pass
						elif key == u'CELEX-nr':
							#TODO
							pass
						elif key == u'Tidsbegränsad':
							rp[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
							if rp[key] < datetime.today():
								raise RevokedDoc()
						else:
							#TODO: Log Warning unknown key
							pass
				if rp:
					r.append(rp)
		return r		

	def _extractSFST(self, files=[], head=True):
		"""Extracts the plaintext from a HTML file"""
		if not files:
			return ''

		t = TextReader(files[0], encoding='iso-8859-1')
		if head:
			t.cuepast(u'<pre>')
		else:
			t.cuepast(u'<hr>')

		txt = t.readto(u'</pre>')
		reEntities = re.compile('&(\w+?);')
		txt = reEntities.sub(self._descapeEntity, txt)
		if not '\r\n' in txt:
			txt = txt.replace('\n','\r\n')
		reTags = re.compile('</?\w{1,3}>')
		txt = reTags.sub(u'',txt)
		return txt + self._extractSFST(files[1:], head=False)

	def _descapeEntity(self, m):
		return unichr(htmlentitydefs.name2codepoint[m.group(1)])

	def _parseSFST(self, txtFile, reg):
		self.reader = TextReader(txtFile, encoding='iso-8859-1', linesep=TextReader.DOS)
		self.reader.autostrip = True
		self.registry = reg
		meta = self.makeHeader()
		body = self.makeForfattning()

	def makeHeader(self):
		pass

	def makeForfattning(self):
		pass		

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
		p = SFSParser()
		parsed = p.Parse(f, files)

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