import numpy as np
import random
import math
import bpy
import networkx as nx

from . import util


class Building(object):
	lot = None
	footprint = None
	
	def __init__(self, lot):
		self.lot = lot
	
	def __calculate_footprint(self):
		pass
	

class Skyscraper(Building):
	pass

class House(Building):
	pass