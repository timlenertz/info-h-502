import numpy as np
import random
import math
import bpy
import networkx as nx

from . import assets, citycell, util

class Plan(object):
	"""Plan of the city, consisting of road map and outlines for buildings."""
	def __init__(self, ter):
		self.terrain = ter
		self.road_network = RoadNetwork(ter)
	
	def generate(self):
		self.terrain.generate()
		self.road_network.generate()


class RoadNetwork(object):
	"""High and low level primary road network, generated randomly. Roads are shaped based on terrain."""
	approximate_number_of_intersection_points = 30
	edges_deviation = 7.0

	road_step_distance = 10.0
	road_number_of_samples = 15
	road_snap_distance = 15.0
	road_deviation_angle = math.radians(8.0)


	def __init__(self, terrain):
		self.terrain = terrain
		
	
	def __create_high_level_graph(self):
		# Subdivide terrain into grid where cell side length is power of 2
		# such that there are at least as many cells as points 
		number_of_cells_x = int(math.ceil(math.sqrt(self.approximate_number_of_intersection_points)))
		number_of_cells_y = int(math.floor(math.sqrt(self.approximate_number_of_intersection_points)))
		number_of_cells = number_of_cells_x * number_of_cells_y
		cell_side_length_x = self.terrain.width / number_of_cells_x
		cell_side_length_y = self.terrain.width / number_of_cells_y
		
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
			center_x -= self.terrain.width * enlarge / 2.0
			center_y += center_y * enlarge
			center_y -= self.terrain.width * enlarge / 2.0
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
		def dist(p1, p2):
			dx = p1[0] - p2[0]
			dy = p1[1] - p2[1]
			return math.sqrt(dx*dx + dy*dy)
		
		step_distance = self.road_step_distance
		number_of_samples = self.road_number_of_samples
		snap_distance = self.road_snap_distance
		deviation_angle = self.road_deviation_angle
		
		pos = src
		if snap_distance < step_distance:
			deviation_angle = min(deviation_angle, math.acos(snap_distance / step_distance)) 
		
		dst_height = self.terrain.height_at(*dst)
		
		def choose_sample(samples):
			min_diff = np.inf
			best = None
			for p in samples:
				covered_distance = dist(src, p)
				remaining_distance = dist(p, dst)
				p_height = self.terrain.height_at(*p)
				
				diff = abs(p_height/covered_distance - dst_height/remaining_distance)
				if diff < min_diff:
					min_diff = diff
					best = p
			
			return best
		
		road_points = [src]
		max_iterations = 1000
		iterations = 0
			
		while dist(pos, dst) > snap_distance:			
			straight_angle = math.atan2(dst[1] - pos[1], dst[0] - pos[0])
			min_angle = straight_angle - deviation_angle
			angle_difference = (2.0*deviation_angle) / number_of_samples
			samples = []
			for i in range(number_of_samples):
				angle = min_angle + i*angle_difference
				sample_x = pos[0] + math.cos(angle) * step_distance
				sample_y = pos[1] + math.sin(angle) * step_distance
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
		return frozenset([a, b])
		
	def oriented_road_for_edge(self, a, b):
		key = self.__road_key(a, b)
		road = self.roads[key]
		if road[-1] == b:
			road = road[:]
			road.reverse()
		return road

	def road_for_edge(self, a, b):
		key = self.__road_key(a, b)
		return self.roads[key]

	
	def __create_low_level_graph(self):
		self.roads = dict()
		for a, b in self.graph.edges_iter():
			road = self.__create_road(a, b)
			key = str(a) + ' ' + str(b)
			self.roads[self.__road_key(a, b)] = road
	
	
	def __create_city_cell(self, cycle, remoteness):
		if remoteness < 0.3:
			return citycell.RoadsCell(self, cycle)
		else:
			return citycell.Cell(self, cycle)
	
	def __create_city_cells(self):
		# Get cycles in primary road network
		# = minimum cycle basis of graph
		cycles = []
		cells_x, cells_y = self.intersection_point_grid.shape
		for y in range(0, cells_y - 1):
			for x in range(0, cells_x - 1):
				a = self.intersection_points[self.intersection_point_grid[x, y]]
				b = self.intersection_points[self.intersection_point_grid[x + 1, y]]
				c = self.intersection_points[self.intersection_point_grid[x + 1, y + 1]]
				d = self.intersection_points[self.intersection_point_grid[x, y + 1]]
				cycles.append([a, b, c, d])
	
		cycles = util.planar_graph_cycles(self.graph)
	
		# Randomly choose point representing city center near terrain center point
		half_w = self.terrain.width / 2
		city_center_x = half_w + half_w*random.normalvariate(0.0, 0.3)
		city_center_y = half_w + half_w*random.normalvariate(0.0, 0.3)
		city_center = (city_center_x, city_center_y)
	
		self.city_cells = []		
		for cycle in cycles:
			center = (0.0, 0.0)
			for x, y in cycle:
				cent = (center[0] + x, center[1] + y)
			n = float(len(cycle))
			center = (center[0] / n, center[1] / n)
			
			remoteness = util.distance(cent, city_center) / (self.terrain.width * math.sqrt(2.0))
		
			city_cell = self.__create_city_cell(cycle, remoteness)
			city_cell.generate()
			self.city_cells.append(city_cell)

	def __create_blender_curve_for_road(self, parent, name, road):
		curve = bpy.data.curves.new(name=name, type='CURVE')
		curve.dimensions = '3D'
		
		polyline = curve.splines.new('POLY')
		polyline.points.add(len(road) - 1)
		i = 0
		for x, y in road:
			z = self.terrain.height_at(x, y)
			polyline.points[i].co = (x, y, z, 1.0)
			i = i + 1
		
		curve_obj = bpy.data.objects.new(name + "_curve", curve)
		curve_obj.parent = parent
		return curve_obj
	
	def __create_blender_road(self, parent, name, road):
		curve = self.__create_blender_curve_for_road(parent, name, road)
		
		road = assets.load_object('primary_road')
		road.name = name
		road.location = (0.0, 0.0, 0.0)
		road.parent = parent
				
		array_modifier = road.modifiers.new("Array", type='ARRAY')
		array_modifier.fit_type = 'FIT_CURVE'
		array_modifier.curve = curve

		curve_modifier = road.modifiers.new("Curve", type='CURVE')
		curve_modifier.object = curve
		
		bpy.context.scene.objects.link(curve)
		bpy.context.scene.objects.link(road)
		
		
		return road
		
		
	def create_blender_object(self, root):
		parent = bpy.data.objects.new('primary_roads', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)
	
		i = 0
		for key in self.roads:
			i = i + 1
			road = self.roads[key]
			self.__create_blender_road(parent, 'primary_road_' + str(i), road)
		
		i = 0
		for cell in self.city_cells:
			i = i + 1
			cell_parent = bpy.data.objects.new('city_cell_' + str(i), None)
			bpy.context.scene.objects.link(cell_parent)
			cell_parent.parent = root
			cell.create_blender_object(cell_parent)
		
		return parent
	
			
	def generate(self):
		self.__create_high_level_graph()
		self.__create_low_level_graph()
		self.__create_city_cells()
