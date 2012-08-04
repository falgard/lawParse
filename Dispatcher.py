#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

class Dispatcher:

	def Dispatch(self, argv):
		#print "Dispatcher"
		#print self
		#print argv
		if len(argv) < 2:
			print "No argument given"
			#Add availableArgs() 
			print "Available argumenst: foo, bar, ..."
			return

		action = argv[1]

		func = getattr(self,action)
		func()

		return

	#TODO: List/print available arguments
	def _availableArgs(self, func):
		pass