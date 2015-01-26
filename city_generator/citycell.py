import numpy as np
import random
import math
import bpy
import networkx as nx

from . import assets, util, mcb, block

class Cell(object):
	"""City cell enclosed by primary road cycle."""
	city = None
	terrain = None
	
	# Cycles = The primary roads enclosing this city cell. Given as Polygon object.
	hi_cycle = None # High level: straight edges between primary road intersections
	lo_cycle = None # Low level: actual flow of primary roads instead of straight edges

	def __init__(self, city, hi_cycle, lo_cycle):
		self.hi_cycle = hi_cycle
		self.lo_cycle = lo_cycle
		self.city = city
		self.terrain = city.terrain
		
		self.hi_cycle.make_clockwise()
		self.lo_cycle.make_clockwise()

	def create_blender_object(self, root):
		pass
	
	def generate(self):
		pass
	
	def full_graph_low(self):
		graph = nx.Graph()
		for edge in self.lo_cycle.edges_iter():
			graph.add_edge(*edge)
		return graph


class LakeCell(Cell):
	"""Cell containing lake. Embosses terrain and adds water surface."""
	level = None
	basins = None
	water_outline = None
	
	def __init__(self, city, hi_cycle, lo_cycle):
		super(LakeCell, self).__init__(city, hi_cycle, lo_cycle)
	
	def __create_basins(self):
		cell_center = self.lo_cycle.center()
		cell_center_to_boundary = self.lo_cycle.point_distance(cell_center)
		
		# Randomly choose multiples basins for lake
		# basin = (center point, radius, depth)
		self.basins = []
		num_centers = random.randint(1, 4)
		for i in range(num_centers):
			max_div = 0.7 * cell_center_to_boundary
			dx = max_div * random.uniform(-1.0, 1.0)
			dy = max_div * random.uniform(-1.0, 1.0)
			center = (cell_center[0] + dx, cell_center[1] + dy)
			
			radius = self.lo_cycle.point_distance(center) * random.uniform(0.6, 1.6)
			depth = radius * random.uniform(0.8, 1.2) / num_centers
			self.basins.append( (center, radius, depth ) )
		
	
	def __create_outline(self):
		samples = 100
		expand = 3.0
		
		angle_step = (2.0 * np.pi) / (samples + 1)

		self.level = +np.inf
		points = []
		for basin in self.basins:
			center, radius, depth = basin
			angle = 0.0
			for i in range(samples):
				x = center[0] + (radius + expand)*math.cos(angle)
				y = center[1] + (radius + expand)*math.sin(angle)
				angle += angle_step
				pt = (x, y)
				points.append(pt)
				
				z = self.terrain.elevation_at(x, y)
				self.level = min(self.level, z)
		
		self.water_outline = util.convex_hull(points)
		self.level = self.level - 0.5
			


	def __emboss_terrain(self):		
		# Bounding box in pixel coordinates
		mn, mx = self.lo_cycle.bounding_box()
		mn = self.terrain.to_image(*mn)
		mx = self.terrain.to_image(*mx)
		
		def emboss_for_basin_at_point(basin, p):
			center, radius, depth = basin
			dist = util.distance(p, center)
			if dist > radius:
				return 0.0
			else:
				a = (dist * np.pi) / radius
				return depth * ((1.0 - math.cos(a))/2.0 - 1.0)
		
		# Iterate over these pixels to emboss terrain...
		maxd = self.hi_cycle.maximal_distance()
		for im_x in range(mn[0], mx[0]):
			for im_y in range(mn[1], mx[1]):
				p = self.terrain.to_terrain(im_x, im_y)
				#if not self.lo_cycle.contains_point(p):
				#	continue

				emboss = 0.0
				for basin in self.basins:
					emboss += emboss_for_basin_at_point(basin, p)
				
				d = self.hi_cycle.point_distance(p)
				noise = random.uniform(-1.0, 1.0) * (d / maxd) * 10.0
				
				self.terrain.image[im_y][im_x] += (emboss + noise) / self.terrain.elevation



	def create_blender_object(self, root):
		# Mesh
		vertices = []
		for p in self.water_outline.vertices_iter():
			vert = (p[0], p[1], self.level)
			vertices.append(vert)
		faces = [ list(range(len(vertices))) ]
					
		# Object
		mesh = bpy.data.meshes.new('water')
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)

		water_obj = bpy.data.objects.new('water', mesh)
		water_obj.parent = root
		bpy.context.scene.objects.link(water_obj)
	
		return water_obj

	
	def generate(self):
		self.__create_basins()	
		self.__emboss_terrain()
		self.__create_outline()



class RoadsCell(Cell):
	"""City cell which contains secondary roads."""

	med_cycle = None # Primary road cycle, hi level + intersections with secondary roads
	graph = None # Graph of secondary roads

	segment_size = None
	snap_size = None
	degree = None
	span_angle = None
	angle_deviation = None
	join_probability = None
	starting_points = None

	__in_med_cycle = None
	__original_elevations = None

	def __init__(self, city, hi_cycle, lo_cycle, profile):
		super(RoadsCell, self).__init__(city, hi_cycle, lo_cycle)
		
		if profile == 'URBAN':
			self.starting_points = 2
			self.segment_size = 30.0
			self.snap_size = 20.0
			self.degree = 3
			self.span_angle = 3.0*np.pi/2.0
			self.angle_deviation = 0.0
			self.join_probability = 1.0
		elif profile == 'SUBURBAN':
			self.starting_points = 4
			self.segment_size = 30.0
			self.snap_size = 20.0
			self.degree = 2
			self.span_angle = 1.2*np.pi
			self.angle_deviation = 0.5
			self.join_probability = 0.4	
		elif profile == 'RURAL':
			self.starting_points = 7
			self.segment_size = 50.0
			self.snap_size = 30.0
			self.degree = 2
			self.span_angle = 0.8*np.pi
			self.angle_deviation = 0.5
			self.join_probability = 0.2
		else:
			raise Exception("Invalid city cell profile.")

	def __is_in_med_cycle(self, a, b, i):
		road = self.city.road_for_edge(a, b)
		key = (a, b)
		return self.__in_med_cycle[(a, b)][i] \
			or self.__in_med_cycle[(b, a)][len(road) - i - 1]

	def __mark_in_med_cycle(self, a, b, i):
		if (a, b) not in self.__in_med_cycle:
			road = self.city.road_for_edge(a, b)
			self.__in_med_cycle[(a, b)] = np.zeros(len(road), dtype=bool)
			if (b, a) not in self.__in_med_cycle:
				self.__in_med_cycle[(b, a)] = np.zeros(len(road), dtype=bool)
		self.__in_med_cycle[(a, b)][i] = True
		

	def __select_starting_junctions(self, n):
		"""Select n points on primary road cycle from where the secondary roads should grow inwards."""
		# N longest cycle edges
		hi_cycle_edges = list(self.hi_cycle.edges_iter())
		longest_edges = sorted(hi_cycle_edges, key=lambda e: -util.distance_sq(*e))

		junctions = [] # junction = (point from low level cycle, next point)
		# Next point is included in order to compute perpendicular segment
		
		for a, b in longest_edges[:n]:
			# Get low level road path for that edge	
			road = self.city.oriented_road_for_edge(a, b)		
			
			# Deviated middle segment
			r = random.normalvariate(0.5, 0.2)
			road_n = len(road) - 1
			i = math.floor(road_n * r)
			i = min(max(i, 0), road_n - 1)
			
			self.__mark_in_med_cycle(a, b, i)
				
			junction = (road[i], road[i+1]);
			junctions.append(junction)
		
		return junctions


	def generate(self):
		self.graph = nx.Graph()
		
		# __in_med_cycle: list of lists of bools.
		# __in_med_cycle[i][j] indicates if point j of road i is included in med cycle graph
		# Initially include start point for each road (--> high-level graph intersection points)
		self.__in_med_cycle = dict()
		for a, b in self.hi_cycle.edges_iter():
			self.__mark_in_med_cycle(a, b, 0)
		
		# Select starting points and grow in first segments
		starting_points = self.__select_starting_junctions(self.starting_points)
		extremities = []
		for edge in starting_points:
			a, b = edge
			ab = (b[0] - a[0], b[1] - a[1])
			ap = (ab[1], -ab[0])
			len_ap = math.sqrt(ap[0]**2 + ap[1]**2)
			ap = (self.segment_size * ap[0] / len_ap, self.segment_size * ap[1] / len_ap)
			p = (a[0] + ap[0], a[1] + ap[1])
			self.graph.add_edge(a, p)
			extremities.append(p)
		
		# Grow secondary roads
		grow = True
		i = 0
		max_iterations = 100
		while grow:
			grow = False
			new_extremities = []
			for pt in extremities:
				add_extremities = self.__grow_from(pt)
				if len(add_extremities) > 0:
					grow = True
					new_extremities = new_extremities + add_extremities
			extremities = new_extremities
			i += 1
			if i > max_iterations:
				grow = False	

		# Make med cycle
		med_cycle = []
		for a, b in self.hi_cycle.edges_iter():
			road = self.city.oriented_road_for_edge(a, b)
			for i in range(len(road)):
				if self.__is_in_med_cycle(a, b, i):
					med_cycle.append(road[i])
		self.med_cycle = util.Polygon(med_cycle)
		
		# Flatten terrain
		self.__original_elevations = dict()
		for p in self.graph.nodes_iter():
			self.__original_elevations[p] = self.terrain.elevation_at(*p)
		for a, b in self.graph.edges_iter():
			self.terrain.flatten_segment(a, b, self.__original_elevations[a], self.__original_elevations[b])
		
		
	def __grow_from(self, pt):
		"""Grow secondary roads from given extremity point."""
		new_extremities = []
	
		prev = None
		for p in nx.all_neighbors(self.graph, pt):
			prev = p
			break
		
		region_per_branch = self.span_angle / self.degree
		for i in range(self.degree):
			mn = region_per_branch * i
			mx = mn + region_per_branch
			
			r = random.normalvariate(0.5, self.angle_deviation)
			r = min(max(r, 0.0), 1.0)
			
			rel_angle = mn + r * (mx - mn)
			edge_angle = np.arctan2(pt[1] - prev[1], pt[0] - prev[0])
			angle = edge_angle - self.span_angle/2 + rel_angle
			dx = self.segment_size * np.cos(angle)
			dy = self.segment_size * np.sin(angle)
			new_pt = (pt[0] + dx, pt[1] + dy)
			new_edge = (pt, new_pt)
			join = (random.uniform(0.0, 1.0) < self.join_probability)
			snap = self.__snap(new_edge, join)
			if not snap:
				self.graph.add_edge(*new_edge)
				new_extremities.append(new_pt)
		
		return new_extremities
	
	
	def __snap(self, new_edge, join):
		"""Span algorithm.
		
		Returns True if the proposed new edge should be added. If not it should be rejected.
		If join is set, the algorithm adds a connecting segment to previously existing roads
		before returning False."""
		if not self.__inside_cycle_test(new_edge, join):
			return True
		elif not self.__edge_intersection_test(new_edge, join):
			return True
		elif not self.__node_distance_test(new_edge, join):
			return True
		elif not self.__edge_distance_test(new_edge, join):
			return True
		else:
			return False
		
		
	def __node_distance_test(self, new_edge, join):
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
				dist_sq = util.line_to_point_distance_sq(new_edge, c)
			else:
				dist_sq = (b[0] - c[0])**2 + (b[1] - c[1])**2
				
			if dist_sq < snap_size_sq:
				if join and (c not in nx.all_neighbors(self.graph, a)):
					self.graph.add_edge(a, c)
				return False
	
		return True
	
	
	def __edge_distance_test(self, new_edge, join):
		a, b = new_edge
		snap_size_sq = self.snap_size**2

		for edge in self.graph.edges_iter():
			if not util.projection_is_on_segment(edge, b):
				break
			dist_sq = util.line_to_point_distance_sq(edge, b)	
			if dist_sq < snap_size_sq:
				if join and (a != edge[0]) and (a != edge[1]):
					proj = util.project_on_line(edge, b)
					c, d = edge
					self.graph.remove_edge(c, d)
					self.graph.add_edge(c, proj)
					self.graph.add_edge(proj, d)
					self.graph.add_edge(a, proj)
				return False

		return True
	
	def __edge_intersection_test(self, new_edge, join):
		a, b = new_edge
		for edge in self.graph.edges_iter():
			if util.segment_intersection(edge, new_edge):
				if join and (edge[0] not in nx.all_neighbors(self.graph, a)) and (edge[1] not in nx.all_neighbors(self.graph, a)):
					proj = util.project_on_line(edge, b)
					c, d = edge
					self.graph.remove_edge(c, d)
					self.graph.add_edge(c, proj)
					self.graph.add_edge(proj, d)
					self.graph.add_edge(a, proj)
				return False
		return True

		
	def __inside_cycle_test(self, new_edge, join):
		a, b = new_edge
		vec = lambda a, b: (b[0] - a[0], b[1] - a[1])
		snap_size_sq = self.snap_size**2

		for cycle_edge in self.hi_cycle.edges_iter():
			u = vec(cycle_edge[0], cycle_edge[1])
			v = vec(cycle_edge[0], b)
			cross_z = u[0]*v[1] - u[1]*v[0];
			if (cross_z > 0) or (util.line_to_point_distance_sq(cycle_edge, b) < snap_size_sq):
				if join:
					road = self.city.oriented_road_for_edge(*cycle_edge)
					def dist(i):
						p = road[i]
						return (p[0] - a[0])**2 + (p[1] - a[1])**2
						
					i = min(range(len(road)), key=dist)
					self.graph.add_edge(a, road[i])
					self.__mark_in_med_cycle(cycle_edge[0], cycle_edge[1], i)
					
				return False
		return True
	

	def full_graph_med(self):
		"""Graph combining secondary roads and surrounding primary road cycle."""
		graph = self.graph.copy()
		for edge in self.med_cycle.edges_iter():
			graph.add_edge(*edge)
		return graph
		
	def full_graph_low(self):
		"""Graph combining secondary roads and surrounding primary road cycle, including shape of primary roads."""
		graph = self.graph.copy()
		for edge in self.lo_cycle.edges_iter():
			graph.add_edge(*edge)
		return graph


	def __create_blender_road(self, name, parent, edge):
		curve = bpy.data.curves.new(name=name, type='CURVE')
		curve.dimensions = '3D'
		
		a, b = edge
		polyline = curve.splines.new('POLY')
		polyline.points.add(1)
		polyline.points[0].co = (a[0], a[1], self.__original_elevations[a], 1.0)
		polyline.points[1].co = (b[0], b[1], self.__original_elevations[b], 1.0)
		
		curve_obj = bpy.data.objects.new(name + '_curve', curve)
		curve_obj.parent = parent

		road = assets.load_object('secondary_road')
		road.name = name
		road.parent = parent
		
		length = util.distance(*edge)
		segment_length = road.dimensions.x

		extra_length = segment_length * 0.7
		length += extra_length
		road.location[0] = -extra_length / 2.0

		scale = length / segment_length
		road.scale[0] = scale
		road.material_slots[0].material.texture_slots[0].scale[1] = scale
		
		curve_modifier = road.modifiers.new("Curve", type='CURVE')
		curve_modifier.object = curve_obj
		
		bpy.context.scene.objects.link(curve_obj)
		bpy.context.scene.objects.link(road)
		
		return road

	
	def create_blender_object(self, root):
		parent = bpy.data.objects.new('secondary_roads', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)

		i = 0
		for edge in self.graph.edges_iter():
			self.__create_blender_road('secondary_road_'+str(i), parent, edge)
			i += 1
		
		return parent


class BlocksCell(RoadsCell):
	"""Roads city cell with city blocks containing buildings."""
	blocks = None # List of CityBlock objects
	
	lot_area_range = None
	building_types = None
	sidewalk_width = None
	
	def __init__(self, city, hi_cycle, lo_cycle, profile):
		super(BlocksCell, self).__init__(city, hi_cycle, lo_cycle, profile)		
	
		if profile == 'URBAN':
			self.lot_area_range = (80, 200)
			self.building_types = ['Skyscraper', 'Office']
			self.sidewalk_width = 3.5
		elif profile == 'SUBURBAN':
			self.lot_area_range = (100, 150)
			self.building_types = ['Office', 'House']
			self.sidewalk_width = 5.0
		elif profile == 'RURAL':
			self.lot_area_range = (100, 200)
			self.building_types = ['House']
			self.sidewalk_width = 10.0


	def generate(self):
		super(BlocksCell, self).generate()

		# Blocks = areas enclosed by road graph
		full_graph = self.full_graph_low()
		block_cycles = mcb.planar_graph_cycles(full_graph)

		self.blocks = []
		for cycle in block_cycles:
			poly = util.Polygon(cycle)
			blk = block.Block(self, poly)
			blk.generate()
			self.blocks.append(blk)
		

	def create_blender_object(self, root):
		super(BlocksCell, self).create_blender_object(root)
		
		parent = bpy.data.objects.new('blocks', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)

		for block in self.blocks:
			block.create_blender_object(parent)
