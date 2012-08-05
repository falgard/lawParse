#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-
"""Base datatypes that inherit from native types such as 
unicode, list, dict.. But with added with support for other properties
that can be set when instansiated"""

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