#!/usr/bin/env python
#-*- coding: iso-8859-1 -*-
"""High level classes for Parser (Download, Generator)"""
#When imported, a module's __name__ attribute is set to the module's file name, without ".py". So the code guarded by the if statement above will not run when imported. 
#When executed as a script though, the __name__ attribute is set to "__main__", and the script code will run.

#Libs
import os,sys
import inspect

#3rd party libs
from configobj import ConfigObj

#Own libs 
from Dispatcher import Dispatcher
import Source

__scriptDir__ = os.getcwd()

class Controller:

	def __init__(self):
		self.config = ConfigObj(__scriptDir__+"/conf.ini")
		self.baseDir = __scriptDir__+os.path.sep+self.config['datadir']

	def _createDict(self, classList):
		d = {}
		for c in classList:
			d[c[0]] = c[1]

		return d

	def _getSrcTypes(self):
		result = {'SFS',}
		#Find avilable types

		return result

	def _getCtrl(self, sourceType):
		import Source
		clsMembers = self._createDict(inspect.getmembers(sourceType, inspect.isclass))

		for c in clsMembers.keys():
			#print "Check %s (%s)" % (c, sourceType.__name__)
			#print repr(inspect.getmro(clsMembers[c]))
            #print inspect.getmro(clsMembers[c])
			if (Source.Controller in inspect.getmro(clsMembers[c])
				and c.startswith(sourceType.__name__)):
				#print clsMembers[c]
				return clsMembers[c]

	def _action(self,action,sourceType):
		#print "_action"
		#print sourceType
		if sourceType == 'all':
			#Collect all types of legal sources
			srcTypes = self._getSrcTypes()
		else:
			srcTypes = (sourceType,)
		for s in srcTypes:
			#do action to all types in srcTypes
			src = __import__(s, globals(), locals(), [])
			srcClass = self._getCtrl(src)
			#print srcClass
			
			if srcClass:
				ctrl = srcClass()
				if hasattr(ctrl, action):
					method = getattr(ctrl, action)
					method()
				else:
					#TODO: add warning, "no such method"
					print "No such method"
			else:
				print "Module %s has no Controller class" % m

	def DownloadAll():
		return

	def ParseAll(self, sourceType='all'):
		self._action('ParseAll', sourceType)

	def GenerateAll(self, module='all'):
		self._action('GenerateAll', module)

if __name__ == "__main__":
	Controller.__bases__ += (Dispatcher, )
	ctrl = Controller()
	ctrl.Dispatch(sys.argv)
	#print "Controller"