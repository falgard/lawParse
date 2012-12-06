#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Handles SFS documents from Regeringskansliet DB"""

#Libs
import os
import sys
import re
import unicodedata
import codecs
import difflib
import htmlentitydefs
from tempfile import mktemp
from datetime import date, datetime
from collections import defaultdict

#3rd party libs
from rdflib import Graph
from rdflib import Namespace, RDFS, RDF, URIRef, Literal

#Own libs
import Source
import config
from Reference import Reference, Link, LinkSubject, ParseError
import Util
from Dispatcher import Dispatcher
from DataObjects import CompoundStructure, MapStructure, \
	 UnicodeStructure, PredicateType, DateStructure, \
	 TemporalStructure, OrdinalStructure
from TextReader import TextReader

__moduledir__ = "sfs"
__scripDir__ = os.getcwd()

class Forfattning(CompoundStructure, TemporalStructure):
	pass

class Rubrik(UnicodeStructure, TemporalStructure):
	"""Headline or sub headline"""
	fragLabel = 'R'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'id' in kwargs else None
		super(Rubrik,self).__init__(*args, **kwargs)

class Stycke(CompoundStructure):
	fragLabel = 'S'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'id' in kwargs else None
		super(Stycke,self).__init__(*args, **kwargs)

class Listelement(CompoundStructure, OrdinalStructure):
	fragLabel = 'N'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'id' in kwargs else None
		super(Listelement,self).__init__(*args, **kwargs)

class NumreradLista(CompoundStructure):
	pass

class StrecksatsLista(CompoundStructure):
	pass

class BokstavsLista(CompoundStructure):
	pass

class Tabell(CompoundStructure):
	pass

class TabellRad(CompoundStructure, TemporalStructure):
	pass

class TabellCell(CompoundStructure):
	pass

class Avdelning(CompoundStructure, OrdinalStructure):
	fragLabel = 'A'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'id' in kwargs else None
		super(Avdelning, self).__init__(*args, **kwargs)

class UpphavtKapitel(UnicodeStructure, OrdinalStructure):
	"""A 'UpphavtKapitel' is different from a 'upphävt kapitel'
	in that way that the law text is gone, just a place holder"""
	pass

class Kapitel(CompoundStructure, OrdinalStructure):
	fragLabel = 'K'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'if' in kwargs else None
		super(Kapitel, self).__init__(*args, **kwargs)

class UpphavdParagraf(UnicodeStructure, OrdinalStructure):
	pass

class Paragraf(CompoundStructure, OrdinalStructure):
	fragLabel = 'P'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'if' in kwargs else None
		super(Paragraf, self).__init__(*args, **kwargs)	

class Overgangsbestammelser(CompoundStructure):
	def __init__(self, *args, **kwargs):
		self.rubrik = kwargs['rubrik'] if 'rubrik' in kwargs else u'Övergångsbestämmelser'
		super(Overgangsbestammelser, self).__init__(*args, **kwargs)	

class Overgangsbestammelse(CompoundStructure, OrdinalStructure):
	fragLabel = 'L'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'if' in kwargs else None
		super(Overgangsbestammelse, self).__init__(*args, **kwargs)

class Bilaga(CompoundStructure):
	fragLabel = 'B'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'if' in kwargs else None
		super(Bilaga, self).__init__(*args, **kwargs)

class Register(CompoundStructure):
	"""Meta data regarding the documnet and its changes"""
	def __init__(self, *args, **kwargs):
		self.rubrik = kwargs['rubrik'] if 'rubrik' in kwargs else None
		super(Register, self).__init__(*args, **kwargs)

class Registerpost(MapStructure):
	#TODO: Is this needed??
	pass

class ForfattningsInfo(MapStructure):
	pass

class UnicodeSubject(PredicateType, UnicodeStructure):
	pass

class DateSubject(PredicateType, DateStructure):
	pass

def FilenameToSfsNr(filename):
	"""Converts a filename to a SFSnr 1909/bih._29_s.1 to 1909:bih 29 s.1"""
	(dir,file) = filename.split('/')
	if file.startswith('RFS'):
		return re.sub(r'(\d{4})/([A-Z]*)(\d*)( [AB]|)(-(\d+-\d+|first-version)|)',r'\2\1:\3', filename.replace('_',' '))
	else:
		return re.sub(r'(\d{4})/(\d*( s[\. ]\d+|))( [AB]|)(-(\d+-\d+|first-version)|)',r'\1:\2', filename.replace('_',' '))

class RevokedDoc(Exception):
	"""Thrown when a doc that is revoked is being parsed"""
	pass

class NotSFS(Exception):
	"""Thrown when not a real SFS document is being parsed as a SFS document"""
	pass

DCT = Namespace(Util.ns['dct'])
XSD = Namespace(Util.ns['xsd'])
RINFO = Namespace(Util.ns['rinfo'])
RINFOEX = Namespace(Util.ns['rinfoex'])

class SFSParser(Source.Parser):

	# Regexpression for parsing SFS documents
	reSimpleSfsId 		= re.compile(r'(\d{4}:\d+)\s*$')
	reSearchSfsId		= re.compile(r'\((\d{4}:\d+)\)').search
	reElementId 		= re.compile(r'^(\d+) mom\.')
	reChapterId			= re.compile(r'^(\d+( \w|)) [Kk]ap.').match
	reSectionId 		= re.compile(r'^(\d+ ?\w?) §[ \.]')
	reSectionIdOld		= re.compile(r'^§ (\d+ ?\w?).')
	reChangeNote		= re.compile(ur'(Lag|Förordning) \(\d{4}:\d+\)\.?$')
	reChapterRevoked	= re.compile(r'^(\d+( \w|)) [Kk]ap. (upphävd|har upphävts) genom (förordning|lag) \([\d\:\. s]+\)\.?$').match
	reSectionRevoked 	= re.compile(r'^(\d+ ?\w?) §[ \.]([Hh]ar upphävts|[Nn]y beteckning (\d+ ?\w?) §) genom ([Ff]örordning|[Ll]ag) \([\d\:\. s]+\)\.$').match
	
	reDottedNumber		= re.compile(r'^(\d+ ?\w?)\. ')
	reBokstavsLista		= re.compile(r'^(\w)\) ')
	reNumberRightPara	= re.compile(r'^(\d+)\) ').match
	reBullet			= re.compile(ur'^(\-\-?|\x96) ')

	reRevokeDate 		= re.compile(ur'/(?:Rubriken u|U)pphör att gälla U:(\d+)-(\d+)-(\d+)/') 
	reRevokeAuth		= re.compile(ur'/Upphör att gälla U:(den dag regeringen bestämmer)/')
	reEntryIntoForceDate = re.compile(ur'/(?:Rubriken t|T)räder i kraft I:(\d+)-(\d+)-(\d+)/')
	reEntryIntoForceAuth = re.compile(ur'/Träder i kraft I:(den dag regeringen bestämmer)/')

	reDefinitions 		= re.compile(r'^I (lagen|förordningen|balken|denna lag|denna förordning|denna balk|denna paragraf|detta kapitel) (avses med|betyder|används följande)').match
	reBrottsDef 		= re.compile(ur'\b(döms|dömes)(?: han)?(?:,[\w§ ]+,)? för ([\w ]{3,50}) till (böter|fängelse)', re.UNICODE).search
	reBrottsDefAlt 		= re.compile(ur'[Ff]ör ([\w ]{3,50}) (döms|dömas) till (böter|fängelse)', re.UNICODE).search
	reDehypenate		= re.compile(r'\b- (?!(och|eller))',re.UNICODE).sub
	reParantesDef 		= re.compile(ur'\(([\w ]{3,50})\)\.', re.UNICODE).search
	reLoptextDef		= re.compile(ur'^Med ([\w ]{3,50}) (?:avses|förstås) i denna (förordning|lag|balk)', re.UNICODE).search
	# Use this to ensure that strings converted to roman numerals are legal
	reRomanNumMatcher = re.compile('^M?M?M?(CM|CD|D?C?C?C?)(XC|XL|L?X?X?X?)(IX|IV|V?I?I?I?)$').match

	romanMap = (('M', 	1000),
				('CM', 	900),
				('D', 	500),
				('CD', 	400),
				('C', 	100),
				('XC', 	90),
				('L', 	50),
				('XL', 	40),
				('X', 	10),
				('IX', 	9),
				('V', 	5),
				('IV', 	4),
				('I', 	1))

	sweOrdMap = (u'första', u'andra', u'tredje', u'fjärde',
				   u'femte', u'sjätte', u'sjunde', u'åttonde',
				   u'nionde', u'tionde', u'elfte', u'tolfte',)

	sweOrdDict = dict(zip(sweOrdMap, range(1, len(sweOrdMap) + 1 )))

	def __init__(self):
		self.lagrumParser = Reference(Reference.LAGRUM)
		self.forarbeteParser = Reference(Reference.FORARBETEN)

		self.currentSection = u'0'
		self.currentHeadlineLevel = 0
		Source.Parser.__init__(self)

	def Parse(self, f, files):
		self.id = f 
		timestamp = sys.maxint
		for filelist in files.values():
			for file in filelist:
				if os.path.getmtime(file) < timestamp:
					timestamp = os.path.getmtime(file)
		
		# Parse SFSR file
		registry = self._parseSFSR(files['sfsr'])
		
		# Extract the plaintext and create a intermediate file for storage
		try:
			plaintext = self._extractSFST(files['sfst'])
			txtFile = files['sfst'][0].replace('.html', '.txt').replace('dl/sfst', 'intermediate')
			Util.checkDir(txtFile)
			tmpFile = mktemp()
			f = codecs.open(tmpFile, 'w', 'iso-8859-1')
			f.write(plaintext + '\r\n')
			f.close()
			Util.replaceUpdated(tmpFile, txtFile)
			
			# Parse the SFST file 
			(meta, body) = self._parseSFST(txtFile, registry)
			
			#TODO: Add patch handling? 

		except IOError:
			#TODO: Add Warning extracting plaintext failed

			meta = ForfattningsInfo()
			meta['Rubrik'] = registry.rubrik
			meta[u'Utgivare'] = LinkSubject(u'Regeringskansliet',
											uri=self.findAuthRec('Regeringskansliet'),
											predicate=self.labels[u'Utgivare'])
			
			fldmap = {u'SFS-nummer' : u'SFS nr',
					  u'Ansvarig myndighet' : u'Departement/ myndighet'}

			for k,v in registry[0].items():
				if k in fldmap:
					meta[fldmap[k]] = v
			docUri = self.lagrumParser.parse(meta[u'SFS nr'])[0].uri
			meta[u'xml:base'] = docUri
			
			body = Forfattning()

			kwargs = {'id':u'S1'}
			s = Stycke([u'(Lagtext saknas)'], **kwargs)
			body.append(s)

		# Add extra meta info
		meta[u'Konsolideringsunderlag'] = []
		meta[u'Förarbeten'] = []
		for rp in registry:
			uri = self.lagrumParser.parse(rp['SFS-nummer'])[0].uri
			meta[u'Konsolideringsunderlag'].append(uri)
			if u'Förarbeten' in rp:
				for node in rp[u'Förarbeten']:
					if isinstance(node, Link):
						meta[u'Förarbeten'].append(node.uri)
		meta[u'Senast hämtad'] = DateSubject(datetime.fromtimestamp(timestamp), predicate='rinfoex:senastHamtad')

		# Fetch abbreviation if existing
		g = Graph()
		g.load(__scripDir__+'/etc/sfs-extra.n3', format='n3')

		for obj in g.objects(URIRef(meta[u'xml:base']), DCT['alternate']):
			meta[u'Förkortning'] = unicode(obj)
			# print meta[u'Förkortning']
		
		obs = None
		for p in body:
			if isinstance(p, Overgangsbestammelser):
				obs = p
				break
		if obs:
			for ob in obs:
				found = False
				for rp in registry:
					if rp[u'SFS-nummer'] == ob.sfsnr:
						if u'Övergångsbestämmelse' in rp and rp[u'Övergångsbestämmelse'] != None:
							pass
						else:
							rp[u'Övergångsbestämmelse'] = ob
						found = True
						break
				if not found:
					kwargs = {'id':u'L'+ob.sfsnr,
							  'uri':u'http://rinfo.lagrummet.se/publ/sfs/'+ob.sfsnr}
					rp = Registerpost(**kwargs)
					rp[u'SFS-nummer'] = ob.sfsnr
					rp[u'Övergångsbestämmelse'] = ob

		# Generate XHTML file
		xhtml = self.generateXhtml(meta, body, registry, __moduledir__,globals())
		if config .debug:
			print "XHTML: "
			print " "
			print xhtml										  					
		return xhtml
		
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
			  u'Omtryck':                	RINFOEX['omtryck'],
			  u'Tidsbegränsad':          	RINFOEX['tidsbegransad'],
			  u'Ändring införd':			RINFO['konsolideringsunderlag'],
			  u'Övrigt':					RDFS.comment,
			  u'Författningen har upphävts genom': RINFOEX['upphavdAv'],
			  u'Upphävd':                RINFOEX['upphavandedatum']
	}


	def _parseSFSR(self, files):
		"""Parse the SFSR registry with all changes from HTML files"""
		allAttr = []
		r = Register()
		for f in files:
			soup = Util.loadSoup(f)
			r.rubrik = Util.elementText(soup.body('table')[2]('tr')[1]('td')[0])
			changes = soup.body('table')[3:-2]

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
								rp[key] = LinkSubject(val, uri=unicode(authRec),
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
							for changecat in val.split(u'; '):
								if (changecat.startswith(u'ändr.') or 
									changecat.startswith(u'ändr ') or 
									changecat.startswith(u'ändring ')):
									pred = RINFO['ersatter']
								elif (changecat.startswith(u'upph.') or 
									  changecat.startswith(u'utgår')):
									pred = RINFO['upphaver']
								elif (changecat.startswith(u'ny') or 
									  changecat.startswith(u'ikrafttr.') or 
									  changecat.startswith(u'ikrafftr.') or 
									  changecat.startswith(u'ikraftr.') or 
									  changecat.startswith(u'ikraftträd.') or 
									  changecat.startswith(u'tillägg')):
									pred = RINFO['inforsI']
								elif (changecat.startswith(u'nuvarande') or 
									  changecat == 'begr. giltighet' or 
									  changecat == 'Omtryck' or 
									  changecat == 'omtryck' or 
									  changecat == 'forts.giltighet' or 
									  changecat == 'forts. giltighet' or 
									  changecat == 'forts. giltighet av vissa best.'):
									pred = None
								else:
									pred = None

								rp[key].extend(self.lagrumParser.parse(changecat, docUri, pred))
								rp[key].append(u';')
							rp[key] = rp[key][:-1]
						elif key == u'F\xf6rarbeten':
							rp[key] = self.forarbeteParser.parse(val, docUri, RINFO['forarbete'])							
						elif key == u'CELEX-nr':
							rp[key] = self.forarbeteParser.parse(val, docUri, RINFO['forarbete'])							
						elif key == u'Tidsbegränsad':
							rp[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
							if rp[key] < datetime.today():
								raise RevokedDoc()
						else:
							#TODO: Log Warning unknown key
							pass
				if rp:
					if config.debug:
						print "Registerpost: "
						print rp
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


		txt = t.readTo(u'</pre>')
		reEntities = re.compile('&(\w+?);')
		txt = reEntities.sub(self._descapeEntity, txt)

		if not '\r\n' in txt:
			txt = txt.replace('\n','\r\n')
		reTags = re.compile('</?\w{1,3}>')
		txt = reTags.sub(u'',txt)
	
		return txt + self._extractSFST(files[1:], head=False)

	def _descapeEntity(self, m):
		return unichr(htmlentitydefs.name2codepoint[m.group(1)])

	def _termToSubject(self, term):
		cap = term[0].upper() + term[1:]
		return u'http://lagen.nu/concept/%s' % cap.replace(' ', '_')

	# Post process document tree and does three things, 
	# 	1. Finds definitions for terms in the text
	# 	2. Finds linkable objects that have their own URIs (kapitel, paragrafer, etc..)
	# 	3. Finds 'lagrumshänvisningar' in the text
	def _constructIds(self, element, prefix, baseUri, skipFrags=[], findDefs=False):
		findDefsRecursive = findDefs
		counters = defaultdict(int)
		if isinstance(element, CompoundStructure):
			# Step 1
			if isinstance(element, Paragraf):
				if self.reDefinitions(element[0][0]):
					findDefs = 'normal'
				if (self.reBrottsDef(element[0][0]) or 
				   	self.reBrottsDefAlt(element[0][0])):
					findDefs = 'brottsrubricering'
				if self.reParantesDef(element[0][0]):
					findDefs = 'parentes'
				if self.reLoptextDef(element[0][0]):
					findDefs = 'loptext'
				
				findDefsRecursive = findDefs

			# Step 1 + 3
			if (isinstance(element, Stycke) or
				isinstance(element, Listelement) or
				isinstance(element, TabellCell)):
				nodes = []
				term = None

				if findDefs:
					elementText = element[0]

					termDelimiter = ':'

					if isinstance(element, TabellCell):
						if elementText != 'Beteckning':
							term = elementText

					elif isinstance(element, Stycke):
						# There's some special cases when ':' is not
						# the delimiter, ex: "antisladdsystem: ett tekniskt.."
						if findDefs == 'normal':
							if not self.reDefinitions(elementText):
								if ' - ' in elementText:
									if (':' in elementText and
										(elementText.index(':') < elementText.index(' - '))):
										termDelimiter = ':'
									else:
										termDelimiter = ' - '
								m = self.reSearchSfsId(elementText)

								if (termDelimiter == ':' and 
								   m and 
								   m.start() < elementText.index(':')):
									termDelimiter = ' '
								if termDelimiter in elementText:
									term = elementText.split(termDelimiter)[0]

						m = self.reBrottsDef(elementText)
						if m: 
							term = m.group(2)

						m = self.reBrottsDefAlt(elementText)
						if m:
							term = m.group(1)

						m = self.reParantesDef(elementText)
						if m:
							term = m.group(1)

						m = self.reLoptextDef(elementText)
						if m:
							term = m.group(1)

					elif isinstance(element, Listelement):
						for rx in (self.reBullet,
								   self.reDottedNumber,
								   self.reBokstavsLista):
							elementText = rx.sub('', elementText)
						term = elementText.split(termDelimiter)[0]

					# Longest legitimate term is < 68 chars 
					if term and len(term) < 68:
						term = Util.normalizedSpace(term)
						termNode = LinkSubject(term, uri=self._termToSubject(term), predicate='dct:subject')
						findDefsRecursive = False
					else:
						term = None

				for p in element:
					if isinstance(p, unicode):
						s = ' '.join(p.split())
						s = s.replace(u'\x96', '-')
						# Make all links have a dct:references
						# predicate, needed to get useful RDF triples
						
						parsedNodes = self.lagrumParser.parse(s, baseUri+prefix, 'dct:references')

						for n in parsedNodes:
							if term and isinstance(n, unicode) and term in n:
								(head, tail) = n.split(term, 1)
								nodes.extend((head,termNode,tail))
							else:
								nodes.append(n)
						idx = element.index(p)
				element[idx:idx+1] = nodes

			# Construct the IDs
			for p in element:
				counters[type(p)] += 1
				if hasattr(p, 'fragLabel'):
					elementType = p.fragLabel
					if hasattr(p, 'ordinal'):
						elementOrdinal = p.ordinal.replace(' ', '')
					elif hasattr(p, 'sfsnr'):
						elementOrdinal = p.sfsnr
					else:
						elementOrdinal = counters[type(p)]
					fragment = '%s%s%s' % (prefix, elementType, elementOrdinal)
					p.id = fragment
				else:
					fragment = prefix

				if ((hasattr(p, 'fragLabel') and
					 p.fragLabel in skipFrags)):
					self._constructIds(p, prefix, baseUri, skipFrags,findDefsRecursive)
				else:
					self._constructIds(p, fragment, baseUri, skipFrags, findDefsRecursive)

				# After the first row in a table is checked, skip row 2,3,.. 
				if isinstance(element, TabellRad):
					findDefsRecursive = False

	def _countElements(self, element):
		counters = defaultdict(int)
		if isinstance(element, CompoundStructure):
			for p in element:
				if hasattr(p, 'fragLabel'):
					counters[p.fragLabel] += 1
					if hasattr(p, 'ordinal'):
						counters[p.fragLabel + p.ordinal] += 1
					subCounters = self._countElements(p)
					for s in subCounters:
						counters[s] += subCounters[s]
		return counters

	def _fromRoman(self, s):
		"""Convert Roman to int"""
		res = 0
		idx = 0
		for numeral,integer in self.romanMap:
			while s[idx:idx+len(numeral)] == numeral:
				res += integer
				idx += len(numeral)

		return res

	def _sweOrd(self, s):
		sl = s.lower()
		if sl in self.sweOrdDict:
			return self.sweOrdDict[sl]
		return None

	def _parseSFST(self, txtFile, registry):
		self.reader = TextReader(txtFile, encoding='iso-8859-1', linesep=TextReader.DOS)
		self.reader.autostrip = True
		self.registry = registry
		meta = self.makeHeader()
		body = self.makeForfattning()
		elements = self._countElements(body)
		
		if 'K' in elements and elements['P1'] < 2:
			skipFrags = ['A', 'K']
		else:
			skipFrags = ['A']

		self._constructIds(body, u'', u'http://rinfo.lagrummet.se/publ/sfs/%s#' % (FilenameToSfsNr(self.id)), skipFrags)

		return meta,body

	def makeHeader(self):
		subReader = self.reader.getReader(self.reader.readChunk, self.reader.linesep * 4)
		meta = ForfattningsInfo()
		
		for line in subReader.getIterator(subReader.readParagraph):
			if ':' in line:
				(key, val) = [Util.normalizedSpace(x) for x in line.split(':',1)]
			if key == u'Rubrik':
				meta[key] = UnicodeSubject(val, predicate=self.labels[key])							
			elif key == u'Övrigt':
				meta[key] = UnicodeSubject(val, predicate=self.labels[key])
			elif key == u'SFS nr':
				meta[key] = UnicodeSubject(val, predicate=self.labels[key])
			elif key == u'Utfärdad':
				meta[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
			elif key == u'Upphävd':
				meta[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
				if meta[key] < datetime.today():
					raise RevokedDoc()
			elif key == u'Departement/ myndighet':
				authRec = self.findAuthRec(val)
				meta[key] = LinkSubject(val, uri=unicode(authRec), predicate=self.labels[key])
			elif key == u'Ändring införd':
				m = self.reSimpleSfsId.search(val)
				if m:				
					uri = self.lagrumParser.parse(m.group(1))[0].uri
					meta[key] = LinkSubject(val, uri=uri, predicate=self.labels[key])
				else:
					pass
					#TODO: Add warning, could not get the SFS nr of the last change
			elif key == u'Omtryck':
				val = val.replace(u'SFS ', '')
				val = val.replace(u'SFS', '')
				try:
					uri = self.lagrumParser.parse(val)[0].uri
					meta[key] = UnicodeSubject(val, predicate=self.labels[key])
				except AttributeError:
					pass
			elif key == u'Författningen har upphävts genom':
				val = val.replace(u'SFS ', '')
				val = val.replace(u'SFS', '')
				startNode = self.lagrumParser.parse(val)[0]
				if hasattr(startNode, 'uri'):
					uri = startNode.uri
					meta[key] = LinkSubject(val, uri=uri, predicate=self.labels[key])
				else:
					meta[key] = val
					#TODO: Add warning, could not get SFS nr	
			elif key == u'Tidsbegränsad':
				meta[key] = DateSubject(datetime.strptime(val[:10], '%Y-%m-%d'), predicate=self.labels[key])
			else:
				pass
				#TODO: Add warning, unknown key 
			meta[u'Utgivare'] = LinkSubject(u'Regeringskansliet', 
											uri=self.findAuthRec('Regeringskansliet'), 
											predicate=self.labels[u'Utgivare'])

		docUri = self.lagrumParser.parse(meta[u'SFS nr'])[0].uri
		meta[u'xml:base'] = docUri

		if u'Rubrik' not in meta:
			pass
			#TODO: Add warning, Rubrik is missing

		if config.debug:
			print "Result from makeHeader: "
			print meta
			
		return meta

	def makeForfattning(self):
		while self.reader.peekLine() == '':
			self.reader.readLine()

		(line, upphor, ikrafttrader) = self.andringsDatum(self.reader.peekLine())
		if ikrafttrader:
			b = Forfattning(ikrafttrader=ikrafttrader)
			self.reader.readLine()
		else:
			b = Forfattning()

		while not self.reader.eof():
			stateHandler = self.guesState()

			if stateHandler == self.makeOvergangsbestammelse:
				res = self.makeOvergangsbestammelser(rubrikMissing=True)
			else:
				res = stateHandler()
			if res != None:
				b.append(res)
		return b

	def makeAvdelning(self):
		avdNr = self.idOfAvdelning()
		p = Avdelning(rubrik=self.reader.readLine(),
					ordinal=avdNr,
					underrubrik=None)
		if (self.reader.peekLine(1) == '' and 
			self.reader.peekLine(3) == '' and
			not self.isKapitel(self.reader.peekLine(2))):
			self.reader.readLine()
			p.underrubrik = self.reader.readLine()

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeAvdelning,
								self.makeOvergangsbestammelser,
								self.makeBilaga):
				return p
			else:
				res = stateHandler()
				if res != None:
					p.append(res)
		return p		

	def makeUpphavtKapitel(self):
		kapitelnummer = self.idOfKapitel()
		
		return UpphavtKapitel(self.reader.readLine(), ordinal=kapitelnummer)

	def makeKapitel(self):

		kapitelnummer = self.idOfKapitel()
		paragraf = self.reader.readParagraph()

		(line, upphor, ikrafttrader) = self.andringsDatum(paragraf)

		kwargs = {'rubrik': Util.normalizedSpace(line),
				  'ordinal': kapitelnummer}
		if upphor:
			kwargs['upphor'] = upphor
		if ikrafttrader:
			kwargs['ikrafttrader'] = ikrafttrader
		k = Kapitel(**kwargs)
		self.currentHeadlineLevel = 0
		self.currentSection = u'0'

		while not self.reader.eof():
			stateHandler = self.guesState()

			if stateHandler in (self.makeKapitel,
								self.makeUpphavtKapitel,
								self.makeAvdelning,
								self.makeOvergangsbestammelser,
								self.makeBilaga):
				return (k)
			else:
				res = stateHandler()
				if res != None:
					k.append(res)

		return k 

	def makeRubrik(self):
		paragraf = self.reader.readParagraph()
		(line, upphor, ikrafttrader) = self.andringsDatum(paragraf)
		kwargs = {}
		if upphor:
			kwargs['upphor'] = upphor
		if ikrafttrader:
			kwargs['ikrafttrader'] = ikrafttrader
		if self.currentHeadlineLevel == 2:
			kwargs['type'] = u'underrubrik'
		elif self.currentHeadlineLevel == 1:
			self.currentHeadlineLevel = 2
		r = Rubrik(line, **kwargs)

		return r

	def makeUpphavdParagraf(self):
		paragrafnummer = self.idOfParagraf(self.reader.peekLine())
		p = UpphavdParagraf(self.reader.readLine(), ordinal=paragrafnummer)
		self.currentSection = paragrafnummer

		return p

	def makeParagraf(self):
		paragrafnummer = self.idOfParagraf(self.reader.peekLine())
		self.currentSection = paragrafnummer
		firstLine = self.reader.peekLine()
		self.reader.read(len(paragrafnummer) + len(u' § '))

		# Some of the old law are split into elements 
		# called moments, mom. Ex: '1 § 2 mom.'
		match = self.reElementId.match(firstLine)
		if self.reElementId.match(firstLine):
			momentnummer = match.group(1)
			self.reader.read(len(momentnummer) + len(u' mom. '))
		else:
			momentnummer = None

		(fixedLine, upphor, ikrafttrader) = self.andringsDatum(firstLine)
		self.reader.read(len(firstLine) - len(fixedLine))
		kwargs = {'ordinal' : paragrafnummer}
		if upphor:
			kwargs['upphor'] = upphor
		if ikrafttrader:
			kwargs['ikrafttrader'] = ikrafttrader
		if momentnummer:
			kwargs['moment'] = momentnummer

		p = Paragraf(**kwargs)
		
		stateHandler = self.makeStycke
		res = self.makeStycke()

		p.append(res)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeParagraf,
								self.makeUpphavdParagraf,
								self.makeKapitel,
								self.makeUpphavtKapitel,
								self.makeAvdelning,
								self.makeRubrik,
								self.makeOvergangsbestammelser,
								self.makeBilaga):
				return p
			elif stateHandler == self.blankLine:
				stateHandler()
			elif stateHandler == self.makeOvergangsbestammelse:
				return p
			else:
				assert stateHandler == self.makeStycke, 'guessState returned %s, not makeStycke' % stateHandler.__name__
				res = self.makeStycke()
				p.append(res)

		return p

	def makeStycke(self):
		s = Stycke([Util.normalizedSpace(self.reader.readParagraph())])

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeNumreradLista,
								self.makeBokstavsLista,
								self.makeStrecksatsLista,
								self.makeTabell):
				res = stateHandler()
				s.append(res)
			elif stateHandler == self.blankLine:
				stateHandler()
			else:
				return s

		return s

	def makeNumreradLista(self):
		n = NumreradLista()

		while not self.reader.eof():
			if self.isNumreradLista():
				stateHandler = self.makeNumreradLista
			else:
				stateHandler = self.guesState()
			if stateHandler not in (self.blankLine,
									self.makeNumreradLista,
									self.makeBokstavsLista,
									self.makeStrecksatsLista):
				return n
			elif stateHandler == self.blankLine:
				stateHandler()
			else:
				if stateHandler == self.makeNumreradLista:
					listelementOrdinal = self.idOfNumreradLista()
					li = Listelement(ordinal=listelementOrdinal)
					p = self.reader.readParagraph()
					li.append(p)
					n.append(li)
				else:
					res = stateHandler()
					n[-1].append(res)
		return n

	def makeBokstavsLista(self):
		n = BokstavsLista()

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler not in (self.blankLine,
									self.makeBokstavsLista):
				return n
			elif stateHandler == self.blankLine:
				res = stateHandler()
			else:
				listelementOrdinal = self.idOfBokstavsLista()
				li = Listelement(ordinal=listelementOrdinal)
				p = self.reader.readParagraph()
				li.append(p)
				n.append(li)

		return n

	def makeStrecksatsLista(self):
		n = StrecksatsLista()
		count = 0

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler not in (self.blankLine,
									self.makeStrecksatsLista):
				return n
			elif stateHandler == self.blankLine:
				res = stateHandler()
			else:
				count += 1
				p = self.reader.readParagraph()
				li = Listelement(ordinal=unicode(count))
				li.append(p)
				n.append(li)

		return n

	def makeBilaga(self):
		rubrik = self.reader.readParagraph()
		(rubrik, upphor, ikrafttrader) = self.andringsDatum(rubrik)

		kwargs = {'rubrik':rubrik}
		if upphor: 
			kwargs['upphor'] = upphor
		if ikrafttrader:
			kwargs['ikrafttrader'] = ikrafttrader
		b = Bilaga(**kwargs)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeBilaga, self.makeOvergangsbestammelser):
				return b
			res = stateHandler()
			if res != None:
				b.append(res)
		return b

	def makeOvergangsbestammelser(self, rubrikMissing=False):
		if rubrikMissing:
			rubrik = u'[Övergångsbestämmelser]'
		else:
			rubrik = self.reader.readParagraph()
		obs = Overgangsbestammelser(rubrik=rubrik)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler == self.makeBilaga:
				return obs

			res = stateHandler()
			if res != None:
				if stateHandler != self.makeOvergangsbestammelse:
					if hasattr(self,'id') and '/' in self.id:
						sfsnr = FilenameToSfsNr(self.id)
					else:
						sfsnr = u'0000:000'

					obs.append(Overgangsbestammelse([res], sfsnr=sfsnr))
				else:
					obs.append(res)
		return obs

	def makeOvergangsbestammelse(self):
		p = self.reader.readLine()
		ob = Overgangsbestammelse(sfsnr=p)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeOvergangsbestammelse, self.makeBilaga):
				return ob
			res = stateHandler()
			if res != None:
				ob.append(res)

		return ob

	def makeTabell(self):
		pCount = 0
		t = Tabell()
		autostrip = self.reader.autostrip
		self.reader.autostrip = False
		p = self.reader.readParagraph()
		(trs, tabstops) = self.makeTabellRad(p)
		t.extend(trs)

		while not self.reader.eof():
			(l, upphor, ikrafttrader) = self.andringsDatum(self.reader.peekLine(), match=True)
			if upphor:
				currUpphor = upphor
				self.reader.readLine()
				pCount = 1
			elif ikrafttrader:
				currIkrafttrader = ikrafttrader
				currUpphor = None
				self.reader.readLine()
				pCount = -pCount + 1
			elif self.isTabell(assumeTable=True):
				kwargs = {}
				if pCount > 0:
					kwargs['upphor'] = currUpphor
					pCount += 1
				elif pCount < 0:
					kwargs['ikrafttrader'] = currIkrafttrader
					pCount += 1
				elif pCount == 0:
					currIkrafttrader = None
				p = self.reader.readParagraph()
				if p:
					(trs, tabstops) = self.makeTabellRad(p, tabstops,kwargs=kwargs)
					t.extend(trs)
			else:
				self.reader.autostrip = autostrip
				return t

		self.reader.autostrip = autostrip
		return t

	def makeTabellRad(self, p, tabstops=None, kwargs={}):
		def makeTabellCell(text):
			if len(text) > 1:
				text = self.reDehypenate('', text)
			return TabellCell([Util.normalizedSpace(text)])

		cols = [u'', u'',u'', u'',u'', u'',u'', u'']
		if tabstops:
			staticTabstops = True
		else:
			staticTabstops = False
			tabstops = [0,0,0,0,0,0,0,0]
		lines = p.split(self.reader.linesep)
		numLines = len([x for x in lines if x])
		potentialRows = len([x for x in lines if x and (x[0].isupper() or x[0].isdigit())])
		lineCount = 0
		if (numLines > 1 and numLines == potentialRows):
			singleLine = True
		else:
			singleLine = False

		rows = []
		emptyLeft = False
		for l in lines:
			if l == '':
				continue
			lineCount += 1
			charCount = 0
			spaceCount =0
			lastTab = 0
			colCount = 0
			if singleLine:
				cols = [u'', u'',u'', u'',u'', u'',u'', u'']
			if l[0] == ' ':
				emptyLeft = True
			else:
				if emptyLeft:
					rows.append(cols)
					cols = [u'', u'',u'', u'',u'', u'',u'', u'']
					emptyLeft = False

			for c in l:
				charCount += 1
				if c == u' ':
					spaceCount += 1
				else:
					if spaceCount > 1:
						# We have found a new table cell
						cols[colCount] += u'\n' + l[lastTab:charCount-(spaceCount+1)]
						lastTab = charCount -1

						# Handle empty left cells
						if lineCount > 1 or staticTabstops:
							if tabstops[colCount+1] + 7 < charCount:
								if len(tabstops) <= colCount + 2:
									tabstops.append(0)
									cols.append(u'')
								if tabstops[colCount+2] != 0:
									colCount += 1
						colCount += 1
						if len(tabstops) <= charCount:
							tabstops.append(0)
							cols.append(u'')
						tabstops[colCount] = charCount
					spaceCount = 0
			cols[colCount] += u'\n' + l[lastTab:charCount]
			if singleLine:
				rows.append(cols)	

		if not singleLine:
			rows.append(cols)

		res = []
		for r in rows:
			tr = TabellRad(**kwargs)
			emptyOk = True
			for c in r:
				if c or emptyOk:
					tr.append(makeTabellCell(c.replace('\n', ' ')))
					if c.strip() != u'':
						emptyOk = False
			res.append(tr)

		return (res, tabstops)

	def blankLine(self):
		self.reader.readLine()
		
		return None

	def eof(self):
		return None	

	def andringsDatum(self, line, match=False):
		dates = {'ikrafttrader'	: None,
				 'upphor'		: None }

		for (regex, key) in { self.reRevokeDate			: 'upphor',
							  self.reRevokeAuth			: 'upphor',
							  self.reEntryIntoForceDate : 'ikrafttrader',
							  self.reEntryIntoForceAuth	: 'ikrafttrader'}.items():
			if match:
				m = regex.match(line)
			else:
				m = regex.search(line)
			if m:
				if len(m.groups()) == 3:
					dates[key] = datetime(int(m.group(1)),
										  int(m.group(2)),
										  int(m.group(3)))
				else:
					dates[key] = m.group(1)
				line = regex.sub(u'', line)

		return (line.strip(), dates['upphor'], dates['ikrafttrader'])

	def guesState(self):
		try:
			if self.reader.peekLine() == '':
				handler = self.blankLine
			elif self.isAvdelning():
				handler = self.makeAvdelning
			elif self.isUpphavtKapitel():
				handler = self.makeUpphavtKapitel
			elif self.isUpphavdParagraf():
				handler = self.makeUpphavdParagraf
			elif self.isKapitel():
				handler = self.makeKapitel
			elif self.isParagraf():
				handler = self.makeParagraf
			elif self.isTabell():
				handler = self.makeTabell
			elif self.isOvergangsbestammelser():
				handler = self.makeOvergangsbestammelser
			elif self.isOvergangsbestammelse():
				handler = self.makeOvergangsbestammelse
			elif self.isBilaga():
				handler = self.makeBilaga
			elif self.isNumreradLista():
				handler = self.makeNumreradLista
			elif self.isStrecksatsLista():
				handler = self.makeStrecksatsLista
			elif self.isBokstavsLista():
				handler = self.makeBokstavsLista
			elif self.isRubrik():
				handler = self.makeRubrik
			else:
				handler = self.makeStycke
		except IOError:
			handler = self.eof
		
		return handler

	def isAvdelning(self):
		if '\n' in self.reader.peekParagraph() != '':
			return False
		return self.idOfAvdelning() != None

	def idOfAvdelning(self):
		# There's four types of 'Avdelning', this checks for these patterns
		p = self.reader.peekLine()
		if p.lower().endswith(u'avdelningen') and len(p.split()) == 2:
			ordinal = p.split()[0]
			return unicode(self._sweOrd(ordinal))
		elif p.startswith(u'AVD. ') or p.startswith(u'AVDELNING '):
			roman = re.split(r'\s+',p)[1]
			if roman.endswith('.'):
				roman = roman[:-1]
			if self.reRomanNumMatcher(roman):
				return unicode(self._fromRoman(roman))
		elif p.startswith(u'Avdelning '):
			roman = re.split(r'\s+',p)[1]
			if self.reRomanNumMatcher(roman):
				return unicode(self._fromRoman(roman))
		elif p[2:6] == 'avd.':
			if p.isdigit():
				return p[0]
		elif p.startswith(u'Avd. '):
			idStr = re.split(r'\s+',p)[1]
			if idStr.isdigit():
				return idStr
		return None

	def isUpphavtKapitel(self):
		match = self.reChapterRevoked(self.reader.peekLine())
		return match != None

	def isKapitel(self, p=None):
		return self.idOfKapitel(p) != None

	def idOfKapitel(self, p=None):
		if not p:
			p = self.reader.peekParagraph().replace('\n', ' ')
    	
		# Things that might look like the start of a chapter is often
		# the start of a paragraph in a section listing the names of chapters
		m = self.reChapterId(p)
		if m:
			if (p.endswith(',') or
				p.endswith(';') or
				p.endswith(' och') or
				p.endswith(' om') or
				p.endswith(' samt') or
				(p.endswith('.') and not
				 (m.span()[1] == len(p) or 
				  p.endswith(' m.m.') or
				  p.endswith(' m. m.') or
				  p.endswith(' m.fl.') or
				  p.endswith(' m. fl.') or
				  self.reChapterRevoked(p)))):
				return None

			# Sometimes (2005:1207) it's a headline, ref a section
			# somewhere else, if '1 kap. ' is followed by '5 §' then 
			# that's the case
			if (p.endswith(u' §') or
				p.endswith(u' §§') or
				(p.endswith(u' stycket') and u' § ' in p)):
				return None
			else:
				return m.group(1)
		else:
			return None

	def isRubrik(self, p=None):
		if p == None:
			p = self.reader.peekParagraph()
			indirect = False
		else:
			indirect = True

		if len(p) > 0 and p[0].lower() == p[0] and not p.startswith('/Rubriken'):
			return False
		if len(p) > 110:
			return False
		if self.isParagraf(p):
			return False
		if self.isNumreradLista(p):
			return False
		if self.isStrecksatsLista(p):
			return False
		if (p.endswith('.') and 
			not (p.endswith('m.m.') or
				 p.endswith('m. m.') or
				 p.endswith('m.fl.') or
				 p.endswith('m. fl.'))):
			return False
		if (p.endswith(',') or
			p.endswith(':') or
			p.endswith('samt') or
			p.endswith('eller')):
			return False
		if self.reChangeNote.search(p):
			return False
		if p.startswith('/') and p.endswith('./'):
			return False

		try:
			nextp = self.reader.peekParagraph(2)
		except IOError:
			nextp = u''

		if not indirect:
			if (not self.isParagraf(nextp)) and (not self.isRubrik(nextp)):
				return False

		# If this headline is followed by a second headline 
		# then that and following headlines are sub headlines
		if (not indirect) and self.isRubrik(nextp):
			self.currentHeadlineLevel = 1

		return True

	def isUpphavdParagraf(self):
		match = self.reSectionRevoked(self.reader.peekLine())
		return match != None

	def isParagraf(self, p=None):
		if not p:
			p = self.reader.peekParagraph()
    	
		paragrafNr = self.idOfParagraf(p)
		if paragrafNr == None:
			return False
		if paragrafNr == '1':
			return True

		# If the section id is < than the last section id 
		# the section is probably a reference and not a new section
		if (cmp(Util.splitNumAlpha(paragrafNr), Util.splitNumAlpha(self.currentSection)) < 0):
			return False
		# Special case, if the first char in the paragraph 
		# is lower case, then it's not a paragraph
		firstChr = (len(paragrafNr) + len(' § '))
		if ((len(p) > firstChr) and
			 (p[len(paragrafNr) + len(' § ')].islower())):
			return False

		return True

	def idOfParagraf(self, p):
		match = self.reSectionId.match(p)
		if match:
			return match.group(1)
		else:
			match = self.reSectionIdOld.match(p)
			if match:
				return match.group(1)
			else:
				return None

	def isTabell(self, p=None, assumeTable=False, reqCols=False):
		shortLine = 55
		shorterLine = 52
		if not p:
			p = self.reader.peekParagraph()

		# Find tables that formated so the right colum extends an
		# extra row. Two tables that are read as one.
		lines = []
		emptyLeft = False
		for l in p.split(self.reader.linesep):
			if l.startswith(' '):
				emptyLeft = True
				lines.append(l)
			else:
				if emptyLeft:
					break
				else:
					lines.append(l)

		numLines = len(lines)
		# Trying to guess if this section is a table 
		# 1. Could be if it's short: 
		if (assumeTable or numLines > 1) and not reqCols:
			matches = [l for l in lines if len(l) < shortLine]
			if numLines == 1 and '  ' in lines[0]:
				return True
			if len(matches) == numLines:
				try:
					p2 = self.reader.peekParagraph(2)
				except IOError:
					p2 = ''
				try:
					p3 = self.reader.peekParagraph(3)
				except IOError:
					p3 = ''
				if not assumeTable and not self.isTabell(p2, 
														 assumeTable=True,
														 reqCols=True):
					return False
				# If the section has one row, it _could_ be a short headline.
				# If it's followed by a paragraf then the table has ended
				elif numLines == 1:
					if self.isParagraf(p2):
						return False
					if self.isRubrik(p2) and self.isParagraf(p3):
						return False
					# If this is the case, then it's probably the transit from 
					# tabel to 'Övergångsbestämmelserna'
					if self.isOvergangsbestammelser():
						return False
					if self.isBilaga():
						return False
				return True

		# 2. Has more than one space in a row on each row
		matches = [l for l in lines if '  ' in l]
		if numLines > 1 and len(matches) == numLines:
			return True

		# 3. Is short (1.) or has the spaces in (2.)
		if (assumeTable or numLines > 1) and not reqCols:
			matches = [l for l in lines if '  ' in l or len(l) < shorterLine]
			if len(matches) == numLines:
				return True

		# 4. Is one row with clear tabelseperation
		if numLines == 1 and '   ' in l:
			return True

		return False

	def isNumreradLista(self, p=None):
		return self.idOfNumreradLista(p) != None

	def idOfNumreradLista(self, p=None):
		if not p:
			p = self.reader.peekLine()
		match = self.reDottedNumber.match(p)
		if match != None:
			return match.group(1).replace(' ', '')
		else:
			match = self.reNumberRightPara(p)
			if match != None:
				return match.group(1).replace(' ', '')

		return None 

	def isStrecksatsLista(self, p=None):
		if not p:
			p = self.reader.peekLine()

		return (p.startswith('- ') or
				p.startswith(u'\x96') or
				p.startswith('--'))

	def isBokstavsLista(self):
		return self.idOfBokstavsLista() != None

	def idOfBokstavsLista(self):
		p = self.reader.peekLine()
		match = self.reBokstavsLista.match(p)
		if match != None:
			return match.group(1).replace(' ', '')
		return None

	def isOvergangsbestammelser(self):
		sep = [u'Övergångsbestämmelser',
			   u'Ikraftträdande- och övergångsbestämmelser',
			   u'Övergångs- och ikraftträdandebestämmelser']
		l = self.reader.peekLine()
		if l not in sep:
			fuzz = difflib.get_close_matches(l, sep, 1, 0.9)
			if fuzz:
				pass
				#TODO: Log warning, did you mean?
			else:
				return False
		try:
			# If the sep 'Övergångsbestämmelser' is followed by a 
			# regular paragraph, it's probably not a sep, but an 
			# ordinary headline.
			np = self.reader.peekParagraph(2)
			if self.isParagraf(np):
				return False
		except IOError:
			pass

		return True

	def isOvergangsbestammelse(self):
		return self.reSimpleSfsId.match(self.reader.peekLine())

	def isBilaga(self):
		(line, upphor, ikrafttrader) = self.andringsDatum(self.reader.peekLine())
		return (line in (u'Bilaga', 
						 u'Bilaga*',
						 u'Bilaga *',
						 u'Bilaga 1',
						 u'Bilaga 2',
						 u'Bilaga 3',
						 u'Bilaga 4',
						 u'Bilaga 5',
						 u'Bilaga 6'))

class SFSController(Source.Controller):

	if config.debug:
		print "## Create SFS Controller"
	
	__parserClass = SFSParser

	## Controller Interface ##

	def Parse(self, f, v=False):		
		try:
			f = f.replace(":", "/")
			files = {'sfst':self.__listfiles('sfst',f), 
					 'sfsr':self.__listfiles('sfsr',f)}
			if (not files['sfst'] and not files['sfsr']):
				raise Source.NoFiles("No files found for %s" % f)
			filename = self._xmlName(f)

			if config.debug:
				print "All files connected to this file: ",
				print files
				print "XML filename: ",
				print filename

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
			t = TextReader(files['sfsr'][0], encoding="iso-8859-1")
			try:
				t.cuepast(u'<i>Författningen är upphävd/skall upphävas: ')
				datestr = t.readTo(u'</i></b>')
				if datetime.strptime(datestr, '%Y-%m-%d') < datetime.today():
					raise RevokedDoc()
					#TODO: log 'expired' document
			except IOError:
				pass

			# Actual parsing begins here.
			p = SFSParser()
			parsed = p.Parse(f, files)
			tmpFile = mktemp()
			out = file(tmpFile, 'w')
			out.write(parsed)
			out.close()
			Util.replaceUpdated(tmpFile, filename)
			return '(.. sec )'

		except RevokedDoc:
			Util.remove(filename)
			Util.remove(Util.relpath(self._htmlName(f)))
		except NotSFS:
			Util.remove(filename)
			Util.remove(Util.relpath(self._htmlName(f)))

	def ParseAll(self):	
		dlDir = os.path.sep.join([self.baseDir, u'sfs', 'dl', 'sfst'])
		
		if config.debug:
			print "## Run ParseAll in SFS"
			print "Download dir: ", dlDir

		self._runMethod(dlDir, 'html', self.Parse)

	def _generateAnnotations(self, annoFile, f):
		p = Reference(Reference.LAGRUM)
		
		sfsnr 	= FilenameToSfsNr(f)
		baseUri = p.parse(sfsnr)[0].uri
		content = {}

		# TODO: 

		# 1. Add link to rattsfall
		# 2. Add law sections that has a dct:ref that matches
		# 3. Add change entries for each section

	def Generate(self, f):
		f = f.replace(':', '/')
		infile = Util.relpath(self._xmlName(f))
		outfile = Util.relpath(self._htmlName(f))

		annotations = '%s/%s/intermediate/%s.ann.xml' % (self.baseDir, self.moduleDir, f)
		dependencies = self._loadDepends(f)

		if self._fileUpToDate(dependencies, annotations):
			pass
		else:
			#self.generateAnno(annotations, f)
			pass

		Util.mkdir(os.path.dirname(outfile))
		#params = {'annotationfile':'../data/sfs/intermediate/%s.ann.xml' % f}
		params = {}
		Util.transform(__scripDir__ + '/xsl/sfs.xsl',
					   infile,
					   outfile,
					   parameters= params,
					   validate=False)
		return

	## Methods that overrides Controller methods ##

	def _get_module_dir(self):
		return __moduledir__	

	def __listfiles(self, source, name):
		"""Given a SFS id returns filenames from the dir that matches the id. 
		For laws that are broken up in _A and _B, both are returned"""
		tmp = "%s/sfs/dl/%s/%s%%s.html" % (self.baseDir, source, name)
		return [tmp%f for f in ('', '_A','_B') if os.path.exists(tmp%f)]