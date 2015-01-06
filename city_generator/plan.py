import numpy as np
import random
import math
import scipy.spatial
import bpy
import networkx as nx

from . import assets

class Plan:
	"""Plan of the city, consisting of road map and outlines for buildings."""
	def __init__(self, ter):
		self.terrain = ter
		self.road_network = RoadNetwork(ter)
	
	def generate(self):
		self.terrain.generate()
		self.road_network.generate()



class CityCell:
	"""City cell encloded by primary road cycle. Contains secondary roads, and building blocks."""
	def __init__(self, road_network, cycle):
		self.__choose_control_parameters()

		vec = lambda a, b: (b[0] - a[0], b[1] - a[1])

		u = vec(cycle[0], cycle[1])
		v = vec(cycle[1], cycle[2])
		cross_z = u[0]*v[1] - u[1]*v[0];
		if cross_z > 0:
			cycle.reverse()

		self.cycle = []
		self.road_network = road_network
		first = cycle[0]
		last = first
		for node in cycle[1:]:
			self.cycle.append((last, node))
			last = node
		self.cycle.append((last, first))

		
	@staticmethod
	def __line_to_point_dist_sq(line, p):
		a, b = line
		num = ( (b[1] - a[1])*p[0] - (b[0] - a[0])*p[1] + b[0]*a[1] - b[1]*a[0] )**2
		den = (b[1] - a[1])**2 + (b[0] - a[0])**2
		return num / den
	
	@staticmethod
	def __distance_sq(a, b):
		return (a[0] - b[0])**2 + (a[1] - b[1])**2

	@staticmethod
	def __distance(a, b):
		return math.sqrt(CityCell.__distance_sq(a, b))

	@staticmethod
	def __segment_intersection(seg1, seg2):
		seg1_len = CityCell.__distance(*seg1)
		seg2_len = CityCell.__distance(*seg2)
	
		def project(seg, seg_len, p):
			a, b = seg
			ap = (p[0] - a[0], p[1] - a[1])
			ab = (b[0] - a[0], b[1] - a[1])
			ab = (ab[0] / seg_len, ab[1] / seg_len)
			return ab[0]*ap[0] + ab[1]*ap[1]
	
		def test(seg, seg_len, p):
			d = project(seg, seg_len, p)
			return (d > 0) and (d < seg_len)
		
		return test(seg1, seg1_len, seg2[0]) and test(seg1, seg1_len, seg2[1]) and test(seg2, seg2_len, seg1[0]) and test(seg2, seg2_len, seg1[1])
	

	def __select_starting_points(self, n):	
		# N longest cycle edges
		edge_len = lambda a, b: (a[0] - b[0])**2 + (a[1] - b[1])**2
		longest_edges = sorted(self.cycle, key=lambda e: -edge_len(*e))

		points = []
		for a, b in longest_edges[:n]:
			# Get low level road path for that edge	
			road = self.road_network.oriented_road_for_edge(a, b)		
			
			# Deviated middle segment
			r = random.normalvariate(0.5, 0.2)
			r = min(max(r, 0.0), 0.95)
			n = len(road) - 1
			i = math.floor(n * r)
			a, b = road[i], road[i+1]
				
			# Random position on that segment
			r = random.uniform(0.0, 1.0)
			px = a[0] + r * (b[0] - a[0])
			py = a[1] + r * (b[1] - a[1])
			p = (px, py)
			edge = (a, b)
			points.append((p, edge))
		
		return points
	
	
	def __choose_control_parameters(self):
		self.segment_size = 20.0
		self.snap_size = 10.0
		self.degree = 3
		
		
	def __grow_from(self, pt):
		new_extremities = []
	
		prev = None
		for p in nx.all_neighbors(self.graph, pt):
			prev = p
			break
		
		region_per_branch = np.pi / self.degree
		for i in range(self.degree):
			mn = region_per_branch * i
			mx = mn + region_per_branch
			
			r = random.normalvariate(0.5, 0.1)
			r = min(max(r, 0.0), 1.0)
			
			rel_angle = mn + r * (mx - mn)
			edge_angle = np.arctan2(pt[1] - prev[1], pt[0] - prev[0])
			angle = edge_angle - np.pi/2 + rel_angle
			dx = self.segment_size * np.cos(angle)
			dy = self.segment_size * np.sin(angle)
			new_pt = (pt[0] + dx, pt[1] + dy)
			new_edge = (pt, new_pt)
			snap = self.__snap(new_edge)
			if not snap:
				self.graph.add_edge(*new_edge)
				new_extremities.append(new_pt)
		
		return new_extremities
	
	def __snap(self, new_edge):
		if not self.__inside_cycle_test(new_edge):
			return True
		elif not self.__node_distance_test(new_edge):
			return True
		elif not self.__edge_distance_test(new_edge):
			return True
		elif not self.__edge_intersection_test(new_edge):
			return True
		else:
			return False
		
		
	def __node_distance_test(self, new_edge):
		a, b = new_edge
		snap_size_sq = self.snap_size**2
			
		new_edge_len_sq = (a[0] - b[0])**2 + (a[1] - b[1])**2
			
		for c in self.graph.nodes_iter():
			if c is a:
				continue
		
			r = (c[0] - a[0])*(b[0] - a[0]) + (c[1] - a[1])*(b[1] - a[1])
			r /= new_edge_len_sq
						
			dist_sq = np.inf
			if r < 0.0:
				continue
			elif r < 1.0:
				dist_sq = self.__line_to_point_dist_sq(new_edge, c)
			else:
				dist_sq = (b[0] - c[0])**2 + (b[1] - c[1])**2
				
			if dist_sq < snap_size_sq:
				return False
	
		return True
	
	
	def __edge_distance_test(self, new_edge):
		a, b = new_edge
		snap_size_sq = self.snap_size**2

		for edge in self.graph.edges_iter():
			if (edge[0] is a) or (edge[1] is a):
				print("strange")
				print("dist", self.__line_to_point_dist_sq(edge, b)	)
			dist_sq = self.__line_to_point_dist_sq(edge, b)	
			if dist_sq < snap_size_sq:
				return False

		return True
	
	def __edge_intersection_test(self, new_edge):
		for edge in self.graph.edges_iter():
			if self.__segment_intersection(edge, new_edge):
				return False
		return True

		
	def __inside_cycle_test(self, new_edge):
		a, b = new_edge
		vec = lambda a, b: (b[0] - a[0], b[1] - a[1])

		for cycle_edge in self.cycle:
			u = vec(cycle_edge[0], cycle_edge[1])
			v = vec(cycle_edge[0], b)
			cross_z = u[0]*v[1] - u[1]*v[0];
			if cross_z > 0:
				return False
		return True
			



	def generate(self):
		self.graph = nx.Graph()
	
		starting_points = self.__select_starting_points(2)
		extremities = []
		for s, edge in starting_points:
			a, b = edge
			ab = (b[0] - a[0], b[1] - a[1])
			ap = (-ab[1], ab[0])
			len_ap = math.sqrt(ap[0]**2 + ap[1]**2)
			ap = (self.segment_size * ap[0] / len_ap, self.segment_size * ap[1] / len_ap)
			p = (s[0] + ap[0], s[1] + ap[1])
			self.graph.add_edge(s, p)
			extremities.append(p)
		
		grow = True
		i = 0
		while grow:
			grow = False
			new_extremities = []
			for pt in extremities:
				add_extremities = self.__grow_from(pt)
				if len(add_extremities) > 0:
					grow = True
					new_extremities = new_extremities + add_extremities
			extremities = new_extremities	

	
	def create_blender_curve(self, name, parent):
		curve = bpy.data.curves.new(name=name, type='CURVE')
		curve.dimensions = '3D'

		for a, b in self.graph.edges_iter():
			polyline = curve.splines.new('POLY')
			polyline.points.add(1)
			polyline.points[0].co = (a[0], a[1], 0.0, 1.0)
			polyline.points[1].co = (b[0], b[1], 0.0, 1.0)
		
		curve_obj = bpy.data.objects.new(name + "_curve", curve)
		curve_obj.parent = parent
		bpy.context.scene.objects.link(curve_obj)
		return curve_obj



class RoadNetwork:
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
	
	def __create_low_level_graph(self):
		self.roads = dict()
		for a, b in self.graph.edges_iter():
			road = self.__create_road(a, b)
			key = str(a) + ' ' + str(b)
			self.roads[self.__road_key(a, b)] = road
	
	
	def __create_city_cells(self):
		cycles = []
		cells_x, cells_y = self.intersection_point_grid.shape
		for y in range(0, cells_y - 1):
			for x in range(0, cells_x - 1):
				a = self.intersection_points[self.intersection_point_grid[x, y]]
				b = self.intersection_points[self.intersection_point_grid[x + 1, y]]
				c = self.intersection_points[self.intersection_point_grid[x + 1, y + 1]]
				d = self.intersection_points[self.intersection_point_grid[x, y + 1]]
				cycles.append([a, b, c, d])
	
		self.city_cells = []
		
		for cycle in cycles:
			city_cell = CityCell(self, cycle)
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
		
		#if 'terrain' in bpy.context.scene.objects:
		#	shrinkwrap_modifier = road.modifiers.new("Shrinkwrap", type='SHRINKWRAP')
		#	shrinkwrap_modifier.target = bpy.context.scene.objects['terrain']
		#	shrinkwrap_modifier.use_keep_above_surface = True
		#	shrinkwrap_modifier.offset = 0.2

		bpy.context.scene.objects.link(curve)
		bpy.context.scene.objects.link(road)
		
		
		return road
		
		
	def create_blender_roads(self, root):
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
			cell.create_blender_curve('roads', cell_parent)
		
		return parent
			
	def generate(self):
		self.__create_high_level_graph()
		self.__create_low_level_graph()
		self.__create_city_cells()
