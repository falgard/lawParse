#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Base datatypes that inherit from native types such as 
unicode, list, dict.. But with added with support for other properties
that can be set when instansiated"""

import Util
import datetime

class AbstractStructure(object):

	def __new__(cls):
		obj = super(AbstractStructure, cls).__new__(cls)
		object.__setattr__(obj, '__initialized', False)
		return obj

	def __init__(self, *args, **kwargs):
		for(key, val) in kwargs.items():
			object.__setattr__(self, key, val)

		object.__setattr__(self, '__initialized', True)

	def __setattr__(self, name, value):
		if object.__getattribute__(self, '__initialized'):
			try:
				object.__getattribute__(self, name)
				object.__setattr__(self, name, value)
			except AttributeError:
				raise AttributeError("Can't set attribute '%s' on object '%s' after init" % (name, self.__class__.__name__))
		else:
			object.__setattr__(self, name, value)

class UnicodeStructure(AbstractStructure, unicode):
	"""UnicodeStructure represents a text string but can also have 
	a index or for ex 'ikraftträdande datum'"""
	#Immutable objects (str, unicode etc) must provide a __new__ method
	def __new__(cls, arg=u'', *args, **kwargs):
		if not isinstance(arg, unicode):
			raise TypeError('%r is not unicode' % arg)
		obj = unicode.__new__(cls, arg)
		object.__setattr__(obj, '__initialized', False)
		return obj

class DateStructure(AbstractStructure, datetime.date):
	"""DateStructure is a datetime.date that also can have other
	attributes like 'ikraftträdande datum'"""
	def __new__(cls, arg=datetime.date.today(), *args, **kwargs):
		if not isinstance(arg, datetime.date):
			raise TypeError('%r is not a datetime.date' % arg)
		obj = datetime.date.__new__(cls, arg.year, arg.month, arg.day)
		object.__setattr__(obj, '__initialized', False)
		return obj

class CompoundStructure(AbstractStructure, list):
	"""CompoundStructure works as a list consisting of other 
	structure objects. It can also have properties of its own."""
	def __new__(cls, arg=[], *args, **kwargs):
		obj = list.__new__(cls)
		obj.extend(arg)
		object.__setattr__(obj, '__initialized', False)
		return obj	

class MapStructure(AbstractStructure, dict):
	"""MapStructure is a map/dictionary"""
	def __new__(cls, arg={}, *args, **kwargs):
		obj = dict.__new__(cls, arg)
		obj.update(arg)
		object.__setattr__(obj, '__initialized', False)
		return obj

class TemporalStructure(object):
	"""TemporalStructure has some time properties 'ikraftträdande',
	'upphör' etc"""
	def __init__(self):
		self. entryintoforce = None
		self.expires = None
	def in_effect(self, date=None):
		if not date:
			date = datetime.date.today()
		return (date >= self.entryintoforce) and (date <= self.expires)
		
class PredicateType(object):
	"""Inheriting from this class gives the subclass a predicate
	attribute that describes the RDF predicate to which the class
	is the RDF subject"""
	def __init__(self, *args, **kwargs):
		if 'predicate' in kwargs:
			self.predicate = kwargs['predicate']
			shorten = False
			for (prefix, ns) in Util.ns.items():
				if kwargs['predicate'].startswith(ns):
					predicateUri = kwargs['predicate']
					kwargs['predicate'] = kwargs['predicate'].replace(ns, prefix + ':')	
					shorten = True
		else:
			from rdflib import RDFS
			self.predicate = RDFS.Resource
		super(PredicateType, self).__init__(*args, **kwargs)

