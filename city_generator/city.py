import numpy as np
import random
import math
import bpy
import networkx as nx

from . import assets, citycell, util, mcb, terrain

class City(object):
	"""City consisting of terrain, primary road network and city cells with content.
	
	This class represents the entire city, and contains all elements of the city (composition).
	The generation of the primary streets according to the terrain shape and subdivision into city cells it
	implemented by this class.
	
	Usage as follows: After instanciation of City object, parametrize by setting attributes, including those
	of self.terrain. City is then generated in two passes: Call to generate() generates internal representation
	of the city and all its components. Then call to create_blender_object() create the Blender objects and
	adds them to the scene.
	"""
	
	terrain = None # Terrain of the city

	approximate_number_of_intersection_points = 30
	edges_deviation = 7.0

	road_step_distance = 10.0
	road_number_of_samples = 15
	road_snap_distance = 15.0
	road_deviation_angle = math.radians(8.0)
	
	# Primary roads are represented on two levels:
	# High-level = Graph connecting intersection points
	# Low-level = Shape of the roads (not necessarily straight lines)
	
	intersection_points = None # Array of points where primary roads intersect.
	intersection_point_grid = None
	graph = None # NetworkX undirected connecting intersections of primary roads. (High-level graph)
	roads = None # Dict where key = frozenset(A,B), value = list of points forming polyline from road from A to B
	city_cells = None # List of city cells.


	def __init__(self):
		self.terrain = terrain.Terrain()
		
	
	def __create_high_level_graph(self):
		"""Randomly place primary road intersection points and create high level graph."""
	
		# Subdivide terrain into grid where cell side length is power of 2
		# such that there are at least as many cells as points 
		number_of_cells_x = int(math.ceil(math.sqrt(self.approximate_number_of_intersection_points)))
		number_of_cells_y = int(math.floor(math.sqrt(self.approximate_number_of_intersection_points)))
		number_of_cells = number_of_cells_x * number_of_cells_y
		cell_side_length_x = self.terrain.side_length / number_of_cells_x
		cell_side_length_y = self.terrain.side_length / number_of_cells_y
		
		def cell_coordinates(i):
			x = i % side_number_of_cells_x
			y = i // side_number_of_cells_y
			return (x, y)
			
		def cell_center(x, y):
			center_x = cell_side_length_x/2.0 + x*cell_side_length_x
			center_y = cell_side_length_y/2.0 + y*cell_side_length_y
			return (center_x, center_y)
		
		def cell_biased_center(x, y):
			enlarge = 0.35
			center_x, center_y = cell_center(x, y)
			center_x += center_x * enlarge
			center_x -= self.terrain.side_length * enlarge / 2.0
			center_y += center_y * enlarge
			center_y -= self.terrain.side_length * enlarge / 2.0
			return (center_x, center_y)
		
				
		# Place intersection points near center of these cells cells
		self.intersection_points = []
		self.intersection_point_grid = np.empty((number_of_cells_x, number_of_cells_y), dtype=int)
		i = 0
		for x in range(number_of_cells_x):
			for y in range(number_of_cells_y):
				bcenter_x, bcenter_y = cell_biased_center(x, y)
				center_x, center_y = cell_center(x, y)
				clamp = lambda minn, maxn, n: max(min(maxn, n), minn)
				padding = 30.0
				px = clamp(
					center_x - cell_side_length_x / 2.0 + padding,
					center_x + cell_side_length_x / 2.0 - padding,
					random.normalvariate(bcenter_x, cell_side_length_x / self.edges_deviation)
				)
				py = clamp(
					center_y - cell_side_length_y / 2.0 + padding,
					center_y + cell_side_length_y / 2.0 - padding,
					random.normalvariate(bcenter_y, cell_side_length_y / self.edges_deviation)
				)
				p = (px, py)
				self.intersection_point_grid[x, y] = i
				self.intersection_points.append(p)
				i = i + 1
		
		# Build roads graph according to grid
		self.graph = nx.Graph()
		for x in range(number_of_cells_x):
			last = None
			for y in range(number_of_cells_y):
				c = self.intersection_points[self.intersection_point_grid[x, y]]
				if last != None:
					self.graph.add_edge(last, c)
				last = c
		for y in range(number_of_cells_y):
			last = None
			for x in range(number_of_cells_x):
				c = self.intersection_points[self.intersection_point_grid[x, y]]
				if last != None:
					self.graph.add_edge(last, c)
				last = c


	def __create_road(self, src, dst):
		"""Create road shape between two intersection points, according to terrain."""
	
		pos = src
		if self.road_snap_distance < self.road_step_distance:
			deviation_angle = min(deviation_angle, math.acos(self.road_snap_distance / self.road_step_distance)) 
		
		dst_height = self.terrain.elevation_at(*dst)
		
		def choose_sample(samples):
			min_diff = np.inf
			best = None
			for p in samples:
				covered_distance = util.distance(src, p)
				remaining_distance = util.distance(p, dst)
				p_height = self.terrain.elevation_at(*p)
				
				diff = abs(p_height/covered_distance - dst_height/remaining_distance)
				if diff < min_diff:
					min_diff = diff
					best = p
			
			return best
		
		road_points = [src]
		max_iterations = 1000
		iterations = 0
			
		while util.distance(pos, dst) > self.road_snap_distance:			
			straight_angle = math.atan2(dst[1] - pos[1], dst[0] - pos[0])
			min_angle = straight_angle - self.road_deviation_angle
			angle_difference = (2.0*self.road_deviation_angle) / self.road_number_of_samples
			samples = []
			for i in range(self.road_number_of_samples):
				angle = min_angle + i*angle_difference
				sample_x = pos[0] + math.cos(angle) * self.road_step_distance
				sample_y = pos[1] + math.sin(angle) * self.road_step_distance
				samples.append((sample_x, sample_y))
				
			sample = choose_sample(samples)
			
			road_points.append(sample)
			pos = sample
		   
			iterations = iterations + 1
			if iterations >= max_iterations:
				break

		road_points.append(dst)
		return road_points


	@staticmethod
	def __road_key(a, b):
		"""Key in self.roads dictionnary for given road."""
		return frozenset([a, b]) # frozenset with the two intersection points. That way __road_key(A, B) is the same as __road_key(B, A).

	def road_for_edge(self, a, b):
		"""Get road connecting the intersection points a, b. List of road points, in order as they are stored."""
		key = self.__road_key(a, b)
		return self.roads[key]
		
	def oriented_road_for_edge(self, a, b):
		"""Get road connecting the intersection points a, b. List of road points, always in order from a to b."""
		key = self.__road_key(a, b)
		road = self.roads[key]
		if road[-1] == a:
			road = road[:]
			road.reverse()
		return road

	
	def __create_low_level_graph(self):
		"""Create the low level graph from the high level graph.
		
		Fills self.roads with roads for all intersection point pairs."""
		self.roads = dict()
		for a, b in self.graph.edges_iter():
			road = self.__create_road(a, b)
			self.roads[self.__road_key(a, b)] = road
	
	
	def __create_city_cell(self, hi_cycle, lo_cycle, remoteness):		
		if remoteness < 0.2:
			return citycell.BlocksCell(self, hi_cycle, lo_cycle, 'URBAN')
		elif remoteness < 0.4:
			return citycell.BlocksCell(self, hi_cycle, lo_cycle, 'SUBURBAN')
		elif remoteness < 0.7:
			return citycell.BlocksCell(self, hi_cycle, lo_cycle, 'RURAL')
		else:
			return citycell.LakeCell(self, hi_cycle, lo_cycle)


	def __low_level_cycle(self, cycle):
		"""Get low level cycle from high level cycle.

		cycle given as list of vertices. Returns low level cycle as list of vertices."""
	
		low_level_cycle = []
		
		def add_road(a, b):
			road = self.oriented_road_for_edge(a, b)
			for p in road[:-1]:
				low_level_cycle.append(p)
		
		a = cycle[0]
		for b in cycle[1:]:
			add_road(a, b)
			a = b
		add_road(a, cycle[0])
		
		return low_level_cycle

	
	def __create_city_cells(self):
		"""Create city cell for each region enclosed by primary roads."""
	
		# Get cycles in primary road network
		# = minimum cycle basis of graph
		cycles = mcb.planar_graph_cycles(self.graph)
	
		# Randomly choose point representing city center near terrain center point
		half_w = self.terrain.side_length / 2
		city_center = (half_w, half_w)
	
		# Generate city cell for each cycle
		self.city_cells = []		
		for hi_cycle in cycles:
			lo_cycle = self.__low_level_cycle(hi_cycle)
		
			hi_cycle = util.Polygon(hi_cycle)
			lo_cycle = util.Polygon(lo_cycle)
			
			center = lo_cycle.center()
			remoteness = util.distance(center, city_center) / self.terrain.side_length
		
			city_cell = self.__create_city_cell(hi_cycle, lo_cycle, remoteness)
			city_cell.generate()
			self.city_cells.append(city_cell)
	

	@staticmethod
	def __road_length(road):
		len = 0.0
		for edge in util.cycle_pairs(road):
			len += util.distance(*edge)
		return len
	
	
	def __straighten_terrain_for_road(self, key):
		pass


	def __create_blender_curve_for_road(self, parent, name, road):
		curve = bpy.data.curves.new(name=name, type='CURVE')
		curve.dimensions = '3D'
		
		polyline = curve.splines.new('POLY')
		polyline.points.add(len(road) - 1)
		i = 0
		for x, y in road:
			z = self.terrain.elevation_at(x, y)
			polyline.points[i].co = (x, y, z, 1.0)
			i += 1
		
		curve_obj = bpy.data.objects.new(name + "_curve", curve)
		curve_obj.parent = parent
		return curve_obj

	
	def __create_blender_road(self, parent, name, road):
		curve = self.__create_blender_curve_for_road(parent, name, road)
		road_len = self.__road_length(road)
		
		road = assets.load_object('primary_road')
		road.name = name
		road.location = (0.0, 0.0, 0.0)
		road.parent = parent
				
		array_modifier = road.modifiers.new("Array", type='ARRAY')
		array_modifier.fit_type = 'FIT_LENGTH'
		array_modifier.fit_length = road_len

		curve_modifier = road.modifiers.new("Curve", type='CURVE')
		curve_modifier.object = curve
		
		bpy.context.scene.objects.link(curve)
		bpy.context.scene.objects.link(road)
		
		return road
			
			
	def generate(self):
		"""Generate internal representation of whole city."""
	
		# Generate the terrain
		self.terrain.generate()
		
		# High and low level graph for primary roads
		self.__create_high_level_graph()
		self.__create_low_level_graph()
		
		# Straighten the terrain for the primary roads
		for key in self.roads:
			self.__straighten_terrain_for_road(key)
			
		# Create the city cells with their contents
		self.__create_city_cells()
	
	
	def create_blender_object(self, name):
		"""Create blender objects for the whole city.
		
		Must be called after generate(). Creates hiearchy of Blender objects,
		where root is given the provided name."""
	
		scene = bpy.context.scene
						
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		self.terrain.create_blender_object(root)
		
		# Primary Roads
		parent = bpy.data.objects.new('primary_roads', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)
	
		i = 0
		for key in self.roads:
			i += 1
			road = self.roads[key]
			self.__create_blender_road(parent, 'primary_road_' + str(i), road)
		
		# City Cells		
		i = 0
		for cell in self.city_cells:
			i += 1
			cell_parent = bpy.data.objects.new('city_cell_' + str(i), None)
			bpy.context.scene.objects.link(cell_parent)
			cell_parent.parent = root
			cell.create_blender_object(cell_parent)
		
		return root
