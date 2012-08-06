#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Module that parse/extracts references to legal sources in plaintext"""

#Libs
import sys
import os

class Reference:
	LAGRUM = 1
	KORTALAGRUM = 2
	FORESKRIFTER = 3

	def __init__(self, *args):
		scriptDir = os.getcwd()
		#self.g = Graph()
		#n3File = Util.relpath(scriptDir + '/etc/sfs-extra.n3')
		#self.graph.load(n3File, format='n3')

	def parse(self, indata, baseUri='http://rinfo.lagrummet.se/publ/sfs/9999:999#K9P9S9P9',predicate=None):
		print indata
		if indata == '':
			return indata
		self.predicate = predicate
		self.baseUri = baseUri
		if baseUri:
			pass		
		return ['',]