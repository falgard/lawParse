#!/usr/bin/env python
#-*- coding: iso-8859-1 -*-
"""High level classes for Parser (Download, Generator)"""
#When imported, a module's __name__ attribute is set to the module's file name, without ".py". So the code guarded by the if statement above will not run when imported. 
#When executed as a script though, the __name__ attribute is set to "__main__", and the script code will run.

#Libs
import os,sys
import getopt
import inspect

#Own libs 
import config
import Source

__scriptDir__ = os.getcwd()

class Controller:

	def __init__(self):
		self.baseDir = __scriptDir__+os.path.sep+config.datadir

		if config.debug:
			print "## Create Controller"
			print "Basedir: ", self.baseDir

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

	def _action(self, action, sourceType):
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
				
				if config.debug:
					print "Control: ", ctrl
					print "Action: ", action
		
				if hasattr(ctrl, action):
					method = getattr(ctrl, action)
					
					if config.debug:
						print "Method: ", method
					
					method()
				else:
					#TODO: add warning, "no such method"
					print "No such method"
			else:
				print "Module %s has no Controller class" % m

	def DownloadAll():
		return

	def ParseAll(self, sourceType='all'):
		
		if config.debug:
			print "## ParseAll in Controller"
		
		self._action('ParseAll', sourceType)

	def GenerateAll(self, module='all'):
		self._action('GenerateAll', module)


	def _validate(self, argv):

		if config.debug:
			print "## Validate user arguments"

		coding = 'utf-8' if sys.stdin.encoding == 'UTF-8' else 'iso-8859-1'
		myArgs = [arg.decode(coding) for arg in argv]

		if len(myArgs) < 1:
			print "No arguments given"
			self.__availableArgs() 
			return
				
		action = myArgs[0]

		try:
			func = getattr(self,action)
		except AttributeError:
			self.__availableArgs()
			sys.exit(2)

		if config.debug:
			print "Function: ", func

		func()

		return

	def __availableArgs(self):
		print "Valid arguments are:", ", ".join(
			[str(m) for m in dir(self) if (not m.startswith("_") 
										   and callable(getattr(self, m)))]
	        )
def usage():
	print "Usage: pyhton Controller.py [-d | -h] [arg]"
	print "Available flags are: -d (debug), -h--help (help)"

def main(args):
	try:                                
		opts, args = getopt.getopt(args, 'dh', 'help')
	except getopt.GetoptError:           
		usage()                          
		sys.exit(2)

	for opt, arg in opts:                
		if opt in ("-h", "--help"):      
			usage()                     
			sys.exit()                  
		elif opt == '-d':                         
			config.debug = 1
	
	ctrl = Controller()
	ctrl._validate(args)


if __name__ == "__main__":
	main(sys.argv[1:])