import numpy as np
import random
import math
import scipy.spatial
import bpy

from . import assets

class Plan:
	"""Plan of the city, consisting of road map and outlines for buildings."""
	def __init__(self, ter):
		self.terrain = ter
		self.primary_road_network = PrimaryRoadNetwork(ter)
	
	def generate(self):
		self.terrain.generate()
		self.primary_road_network.generate()




class PrimaryRoadNetwork:
	"""High and low level primary road network, generated randomly. Roads are shaped based on terrain."""
	min_number_of_intersection_points = 10
	edges_deviation = 8.0

	road_step_distance = 10.0
	road_number_of_samples = 15
	road_snap_distance = 15.0
	road_deviation_angle = math.radians(10.0)


	def __init__(self, terrain):
		self.terrain = terrain
		
	
	def __create_high_level_graph(self):
		# Subdivide terrain into grid where cell side length is power of 2
		# such that there are at least as many cells as points 
		n = self.min_number_of_intersection_points
		depth = int(math.ceil(math.log(n, 4)))
		side_number_of_cells = 2**depth
		number_of_cells = side_number_of_cells**2
		assert number_of_cells >= n
		cell_side_length = self.terrain.width / side_number_of_cells
		
		def cell_coordinates(i):
			x = i % side_number_of_cells
			y = i // side_number_of_cells
			return (x, y)
			
		def cell_center(x, y):
			center_x = cell_side_length/2.0 + x*cell_side_length
			center_y = cell_side_length/2.0 + y*cell_side_length
			return (center_x, center_y)
		
				
		# Place intersection points near center of these cells cells
		self.intersection_points = []
		intersection_point_grid = np.empty((side_number_of_cells, side_number_of_cells), dtype=int)
		i = 0
		for x in range(side_number_of_cells):
			for y in range(side_number_of_cells):
				center_x, center_y = cell_center(x, y)
				sigma = cell_side_length / self.edges_deviation
				px = random.normalvariate(center_x, sigma)
				py = random.normalvariate(center_y, sigma)
				intersection_point_grid[x, y] = i
				i = i + 1
				self.intersection_points.append((px, py))
		
		# Build roads according to grid, but randomly leave out some segments
		self.adjacency = []
		for i in range(side_number_of_cells * side_number_of_cells):
			self.adjacency.append([])
		
		for x in range(side_number_of_cells):
			last = None
			for y in range(side_number_of_cells):
				c = intersection_point_grid[x, y]
				if last != None:
					self.adjacency[c].append(last)
					self.adjacency[last].append(c)
				last = c
		for y in range(side_number_of_cells):
			last = None
			for x in range(side_number_of_cells):
				c = intersection_point_grid[x, y]
				if last != None:
					self.adjacency[c].append(last)
					self.adjacency[last].append(c)
				last = c


	def __create_road(self, a, b):
		def dist(p1, p2):
			dx = p1[0] - p2[0]
			dy = p1[1] - p2[1]
			return math.sqrt(dx*dx + dy*dy)
		
		src = self.intersection_points[a]
		dst = self.intersection_points[b]
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
	
	
	def __create_low_level_graph(self):
		self.roads = dict()
		for a, adj in enumerate(self.adjacency):
			for b in adj:
				if a < b:
					road = self.__create_road(a, b)
					key = str(a) + ' ' + str(b)
					self.roads[key] = road
	

	def __create_blender_curve_for_road(self, name, road):
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
		return curve_obj
	
	def __create_blender_road(self, name, road):
		curve = self.__create_blender_curve_for_road(name, road)
		bpy.context.scene.objects.link(curve)
		
		road = assets.load_object('primary_road')
		road.name = name
		road.location = (0.0, 0.0, 3.0)
		array_modifier = road.modifiers.new("Array", type='ARRAY')
		array_modifier.fit_type = 'FIT_CURVE'
		array_modifier.curve = curve

		curve_modifier = road.modifiers.new("Curve", type='CURVE')
		curve_modifier.object = curve
		return road
		
		
	def create_blender_roads(self):
		i = 0
		for key in self.roads:
			i = i + 1
			road = self.roads[key]
			obj = self.__create_blender_road("road "+str(i), road)
			bpy.context.scene.objects.link(obj)
			
	def generate(self):
		self.__create_high_level_graph()
		self.__create_low_level_graph()
