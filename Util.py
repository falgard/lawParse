#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Lib with utility functions"""

#Libs
import os
import codecs
import shutil
import filecmp

#3rd party libs
import BeautifulSoup

#Common namespaces and prefixes for them
ns = {'dc':'http://purl.org/dc/elements/1.1/',
	  'dct':'http://purl.org/dc/terms/',
	  'rdfs':'http://www.w3.org/2000/01/rdf-schema#',
      'rdf':'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
      'skos':'http://www.w3.org/2008/05/skos#',
      'rinfo':'http://rinfo.lagrummet.se/taxo/2007/09/rinfo/pub#',
      'rinfoex':'http://lagen.nu/terms#',
      'eurlex':'http://lagen.nu/eurlex#',
      'xsd':'http://www.w3.org/2001/XMLSchema#',
      'xht2':'http://www.w3.org/2002/06/xhtml2/'}

def mkdir(dirname):
	"""mkdir used when creating intermediate and parsed dirs for storage""" 
	if not os.path.exists(dirname):
		os.makedirs(dirname)

def checkDir(filename):
	"""Check if a dir exists, if not create it"""
	d = os.path.dirname(filename)
	if d and not os.path.exists(d):
		try:
			mkdir(d)
		except:
			pass

def remove(file):
	if os.path.exists(file):
		os.unlink(file)
		
def relpath(path, start=os.curdir):
	"""Relative version of a given path"""
	if not path:
		raise ValueError("No path specified")
	startList = os.path.abspath(start).split(os.path.sep)
	pathList = os.path.abspath(path).split(os.path.sep)

	for i in range(min(len(startList), len(pathList))):
		if startList[i].lower() != pathList[i].lower():
			break
		else:
			i += 1
	relList = [os.pardir] * (len(startList)-i) + pathList[i:]
	if not relList:
		return curdir
	return os.path.sep.join(relList)

def listDirs(d,suffix=None,reverse=False):
	"""A generator that works like os.listdir recursively and returns files instead of dirs."""
	if isinstance(d, str):
		print "WARNING: listDirs was called with str, use unicode."
	dirs = [d]
	while dirs:
		d = dirs.pop()
		for f in sorted(os.listdir(d)):
			f = "%s%s%s" % (d, os.path.sep, f)
			if os.path.isdir(f):
				dirs.insert(0,f)
			elif os.path.isfile:
				if suffix and not f.endswith(suffix):
					continue
				else:
					yield f

def replaceUpdated(newfile, oldfile):
	assert os.path.exists(newfile)
	if not os.path.exists(oldfile):
		forceRename(newfile,oldfile)
		return True
	elif not filecmp.cmp(newfile,oldfile):
		forceRename(newfile,oldfile)
		return True
	else:
		os.unlink(newfile)
		return False

def forceRename(old, new):
	"""Renames old to new, if the file exists, it's removed
	if the target dir doesn't exist, it's created"""
	checkDir(new)
	if os.path.exists(new):
		os.unlink(new)
	try:
		shutil.move(old,new)
	except IOError:
		pass

def elementText(element):
	"""Finds the plaintext in a BeautifulSoup element"""
	return normalizedSpace(
		u''.join(
		[e for e in element.recursiveChildGenerator() 
		if (isinstance(e,unicode) and 
			not isinstance(e, BeautifulSoup.Comment))]))

def normalizedSpace(string):
	return u' '.join(string.split())

def loadSoup(filename, encoding='iso-8859-1'):
	return BeautifulSoup.BeautifulSoup(codecs.open(
		filename,encoding=encoding,errors='replace').read(),convertEntities='html')

	# TODO:
	# since 3.1, BeautifulSoup no longer supports broken HTML. In the
    # future, we should use the html5lib parser instead (which exports
    # a BeautifulSoup interface). However, html5lib has problems of
    # it's own right now:
    # http://www.mail-archive.com/html5lib-discuss@googlegroups.com/msg00346.html
    #
    # The old call to BeautifulSoup had a convertEntities parameter
    # (set to 'html'), html5lib.HTMLParser does not have anything
    # similar. Hope it does right by default.
    #
    # f = codecs.open(filename,encoding=encoding,errors='replace')
    # parser = html5lib.HTMLParser(tree=treebuilders.getTreeBuilder("beautifulsoup"))
    # return parser.parse(f)