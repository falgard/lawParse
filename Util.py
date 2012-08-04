#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

import os

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