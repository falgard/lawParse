#!/usr/bin/env python
# -*- coding: iso-8859-1 -*-

import sys

class Dispatcher:

	def Dispatch(self, argv):

		coding = 'utf-8' if sys.stdin.encoding == 'UTF-8' else 'iso-8859-1'
		myArgs = [arg.decode(coding) for arg in argv]

		if len(myArgs) < 2:
			print "No argument given"
			#Add availableArgs() 
			print "Available argumenst: foo, bar, ..."
			return
			
		action = myArgs[1]

		func = getattr(self,action)
		func()

		return

	#TODO: List/print available arguments
	def _availableArgs(self, func):
		pass