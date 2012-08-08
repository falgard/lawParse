#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Handles SFS documents from Regeringskansliet DB"""

#Libs
import os
import sys
import re
import unicodedata
import codecs
import htmlentitydefs
from tempfile import mktemp
from datetime import date, datetime

#3rd party libs
from rdflib import Namespace, RDFS

#Own libs
import Source
from Reference import Reference, Link, LinkSubject
import Util
from Dispatcher import Dispatcher
from DataObjects import CompoundStructure, MapStructure, \
	 UnicodeStructure, PredicateType, DateStructure, TemporalStructure
from TextReader import TextReader

__moduledir__ = "sfs"

class Forfattning(CompoundStructure, TemporalStructure):
	pass

class Rubrik(UnicodeStructure, TemporalStructure):
	"""Headline or sub headline"""
	fragLabel = 'R'
	def __init__(self, *args, **kwargs):
		self.id = kwargs['id'] if 'id' in kwargs else None
		super(Rubrik,self).__init__(*args, **kwargs)

class Stycke(CompoundStructure):
	def __init__(self, *args, **kwargs):
		pass

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

	reSimpleSfsId = re.compile(r'(\d{4}:\d+)\s*$')

	def __init__(self):
		self.lagrumParser = Reference(Reference.LAGRUM)
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
		reg = self._parseSFSR(files['sfsr'])
		
		#Extract the plaintext and create a intermediate file for storage
		try:
			plaintext = self._extractSFST(files['sfst'])
			txtFile = files['sfst'][0].replace('.html', '.txt').replace('dl/sfst', 'intermediate')
			Util.checkDir(txtFile)
			tmpFile = mktemp()
			f = codecs.open(tmpFile, 'w', 'iso-8859-1')
			f.write(plaintext + '\r\n')
			f.close()
			Util.replaceUpdated(tmpFile, txtFile)
			
			meta = self._parseSFST(txtFile, reg)
			
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

	def _parseSFST(self, txtFile, reg):
		self.reader = TextReader(txtFile, encoding='iso-8859-1', linesep=TextReader.DOS)
		self.reader.autostrip = True
		self.reg = reg
		meta = self.makeHeader()
		body = self.makeForfattning()

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
			elif key == u'Department/ myndighet':
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
			if stateHandler == self.makeOvergangsbestemmelse:
				res = self.makeOvergangsbestemmelser(rubrikMissing=True)
			else:
				res = stateHandler()
			if res != None:
				b.append(res)
		
		return b

	def makeAvdelning(self):
		avdNr = self.idOfAvdelning()
		p.Avdelning(rubrik=self.reader.readLine(),
					ordinal=avdNr,
					underRubrik=None)
		if (self.reader.peekLine(1) == '' and 
			self.reader.peekLine(3) == '' and
			not self.isKapitel(self.reader.peekLine(2))):
			self.reader.readLine()
			p.underRubrik = self.reader.readLine()

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeAvdelning,
								self.makeOvergangsbestemmelser,
								self.makeBilaga):
				return p
			else:
				res = stateHandler()
				if res != None:
					p.append(res)
		return p		

	def makeUpphavtKapitel(self):
		kapNr = self.idOfKapitel()
		
		return UpphavtKapitel(self.reader.readLine(), ordinal=kapNr)

	def makeKapitel(self):
		kapNr = self.idOfKapitel()
		paragraf = self.reader.readParagraph()
		(line, upphor, ikrafttrader) = self.andringsDatum(paragraf)

		kwargs = {'rubrik': Util.normalizedSpace(line),
				  'ordinal': kapNr}
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
								self.makeOvergangsbestemmelser,
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
			kwargs['type'] = u'underRubrik'
		elif self.currentHeadlineLevel == 1:
			self.currentHeadlineLevel = 2
		r = Rubrik(line, **kwargs)

		return r

	def makeUpphavdParagraf(self):
		paraNr = self.idOfParagraf(self.reader.peekLine())
		p = UpphavdParagraf(self.reader.readLine(), ordinal=paraNr)
		self.currentSection = paraNr

		return p

	def makeParagraf(self):
		paraNr = self.idOfParagraf(self.reader.peekLine())
		p = UpphavdParagraf(self.reader.readLine(), ordinal=paraNr)
		self.currentSection = paraNr

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
				return self

		return self

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
			if stateHandler in (self.makeBilaga, self.makeOvergangsbestemmelser):
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
		obs = Overgangsbestemmelser(rubrik=rubrik)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler == self.makeBilaga:
				return obs

			res = stateHandler()
			if res != None:
				if stateHandler != self.makeOvergangsbestemmelse:
					if hasattr(self,'id') and '/' in self.id:
						sfsnr = FilenameToSfsNr(self.id)
					else:
						sfsnr = u'0000:000'

					obs.append(Overgangsbestemmelse([res], sfsnr=sfsnr))
				else:
					obs.append(res)
		return obs

	def makeOvergangsbestammelse(self):
		p = self.reader.readLine()
		ob = Overgangsbestemmelse(sfsnr=p)

		while not self.reader.eof():
			stateHandler = self.guesState()
			if stateHandler in (self.makeOvergangsbestemmelse, self.makeBilaga):
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
            elif self.isStrecksatslista():
            	handler = self.makeStrecksatsLista
            elif self.isBokstavslista():
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
    		return unicode(self._sweOrdinal(ordinal))
    	elif p.startswith(u'AVD. ') or p.startswith(u'AVDELNING '):
    		roman = re.split(r'\s+',p)[1]
    		if roman.endswith('.'):
    			roman = roman[:-1]
    		if self.reRomanNumMatcher(roman):
    			return unicode(self._fromRoman(roman))
    	elif p.startswith(u'Avdelning '):
    		roman = re.split(r'\s+',p)[1]
    		if self.reRomanNumMatcher(roman)
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

    	if len(p) > 0 and p[0].lower() == p[0] and not p.startswith('/Ruriken'):
    		return False
    	if len(p) > 110:
    		return False
    	if self.isParagraf(p):
    		return False
    	if isNumreradLista(p):
    		return False
    	if isStrecksatslista(p):
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
    	if cmp(paragrafNr, self.currentSection) < 0:
    		#TODO: Does this cmp work?
    		return False
    	# Special case, if the first char in the paragraph 
    	# is lower case, then it's not a paragraph
    	firstChr = (len(paragrafNr) + len(' § '))
    	if ((len(p) > firstChr) and
    		 p.[len(paragrafNr) + len(' § ')].islower())):
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

	def isStecksatsLista(self, p=None):
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

		except RevokedDoc:
			Util.remove(filename)
			Util.remove(Util.relpath(self._htmlName(f)))
		except NotSFS:
			Util.remove(filename)
			Util.remove(Util.relpath(self._htmlName(f)))

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