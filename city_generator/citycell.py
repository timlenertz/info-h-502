import numpy as np
import random
import math
import bpy
import networkx as nx

from . import assets, util, mcb, block

class Cell(object):
	hi_cycle = None # High-level cycle of enclosing primary roads: Intersections of primary roads only
	lo_cycle = None # Low-level cycle of enclosing primary roads: Indiv segments constituing primary road trajectory.
	# Both as list of vertices in clockwise order

	"""City cell enclosed by primary road cycle."""
	def __init__(self, road_network, hi_cycle, lo_cycle):
		if not util.polygon_is_clockwise(hi_cycle):
			hi_cycle.reverse()
			lo_cycle.reverse()	

		self.hi_cycle = hi_cycle
		self.lo_cycle = lo_cycle
		self.road_network = road_network
		self.terrain = self.road_network.terrain
	
	def bounding_box(self):
		lo = (+np.inf, +np.inf)
		hi = (-np.inf, -np.inf)
		for p in self.hi_cycle:
			hi = (max(hi[0], p[0]), max(hi[1], p[1]))
			lo = (min(lo[0], p[0]), min(lo[1], p[1]))
		return (lo, hi)
	
	def hi_cycle_edges(self):
		prev = self.hi_cycle[0]
		for curr in self.hi_cycle[1:]:
			yield (prev, curr)
			prev = curr
		yield (prev, self.hi_cycle[0])

	def lo_cycle_edges(self):
		prev = self.lo_cycle[0]
		for curr in self.lo_cycle[1:]:
			yield (prev, curr)
			prev = curr
		yield (prev, self.lo_cycle[0])


	def create_blender_object(self, root):
		pass
	
	def generate(self):
		pass


class LakeCell(Cell):
	"""Cell containing lake. Embosses terrain and adds water surface."""
	def __init__(self, road_network, hi_cycle, lo_cycle):
		super(LakeCell, self).__init__(road_network, hi_cycle, lo_cycle)
	
	def __emboss_terrain(self):
		mn, mx = self.bounding_box()
		
		def dist_to_boundary(p):
			dist = +np.inf
			for edge in self.lo_cycle_edges():
				d = util.line_to_point_dist(edge, p)
				dist = min(dist, d)
			return dist
		
		cell_center = ((mn[0] + mx[0])/2, (mn[1] + mx[1])/2)
		cell_center_to_boundary = dist_to_boundary(cell_center)
		max_dist = (mx[0] - mn[0]) + (mx[1] - mn[1])
		
		centers = []
		num_centers = random.randint(1, 4)
		for i in range(num_centers):
			max_div = 0.3 * cell_center_to_boundary
			dx = max_div * random.uniform(-1.0, 1.0)
			dy = max_div * random.uniform(-1.0, 1.0)
			center = (cell_center[0] + dx, cell_center[1] + dy)
			centers.append( (center, dist_to_boundary(center)) )
		
		mn = self.terrain.to_image(*mn)
		mx = self.terrain.to_image(*mx)
		
		for im_x in range(mn[0], mx[0]):
			for im_y in range(mn[1], mx[1]):
				p = self.terrain.to_terrain(im_x, im_y)
				
				emboss = 0.0
				for center, radius in centers:
					dist = util.distance(center, p)
					if dist < radius:
						emboss += (radius - dist)**2 / radius**2
				
				noise = random.uniform(-1.0, 1.0)
				amplitude = 0.0
				if util.distance(p, cell_center) < cell_center_to_boundary:
					amplitude = util.distance(p, cell_center) / cell_center_to_boundary
				
				self.terrain.image[im_y][im_x] -= 1.3*emboss + 0.3*amplitude*noise
	

	def create_blender_object(self, root):
		# Mesh
		vertices = []
		for a, b in self.lo_cycle_edges():
			vert = (a[0], a[1], self.level)
			vertices.append(vert)
		faces = [[]]
		for i in range(len(vertices)):
			faces[0].append(i)
					
		# Object
		mesh = bpy.data.meshes.new('water')
		mesh.from_pydata(vertices, [], faces)
		mesh.update(calc_edges=True)

		water_obj = bpy.data.objects.new('water', mesh)
		water_obj.parent = root
		bpy.context.scene.objects.link(water_obj)
	
		return water_obj

	
	def generate(self):
		self.__emboss_terrain()
		
		self.level = +np.inf
		for p in self.lo_cycle:
			height = self.terrain.height_at(*p)
			if height < self.level:
				self.level = height
		self.level -= 0.3



class RoadsCell(Cell):
	med_cycle = None # Primary road cycle, hi level + intersections with secondary roads
	# The last point in a road is never marked, but only the first one of the next road (= same point)

	"""City cell which contains secondary roads."""
	def __init__(self, road_network, hi_cycle, lo_cycle):
		super(RoadsCell, self).__init__(road_network, hi_cycle, lo_cycle)
		
		self.__choose_control_parameters('SUBURBAN')
	
	def generate(self):
		self.graph = nx.Graph()
		
		# __in_med_cycle: list of lists of bools.
		# __in_med_cycle[i][j] indicates if point j of road i is included in med cycle graph
		self.__in_med_cycle = dict()
		for a, b in util.cycle_pairs(self.hi_cycle):
			key = frozenset([a, b])
			road = self.road_network.road_for_edge(a, b)
			road_m = np.zeros(len(road), dtype=bool)
			road_m[0] = True
			self.__in_med_cycle[key] = road_m
		
		# Initially include
		starting_points = self.__select_starting_points(2)
		extremities = []
		for s, edge in starting_points:
			a, b = edge
			ab = (b[0] - a[0], b[1] - a[1])
			ap = (ab[1], -ab[0])
			len_ap = math.sqrt(ap[0]**2 + ap[1]**2)
			ap = (self.segment_size * ap[0] / len_ap, self.segment_size * ap[1] / len_ap)
			p = (s[0] + ap[0], s[1] + ap[1])
			self.graph.add_edge(s, p)
			extremities.append(p)
		
		# Grow secondary roads
		grow = True
		i = 0
		max_iterations = 15
		while grow:
			grow = False
			new_extremities = []
			for pt in extremities:
				add_extremities = self.__grow_from(pt)
				if len(add_extremities) > 0:
					grow = True
					new_extremities = new_extremities + add_extremities
			extremities = new_extremities
			i = i + 1
			if i > max_iterations:
				grow = False	

		# Make med cycle
		self.med_cycle = []
		for a, b in util.cycle_pairs(self.hi_cycle):
			road = self.road_network.oriented_road_for_edge(a, b)
			key = frozenset([a, b])
			road_m = self.__in_med_cycle[key]
			for i, p in enumerate(road):
				if road_m[i]:
					self.med_cycle.append(p)


	def __mark_in_med_cycle(self, road_a, road_b, i):
		key = frozenset([road_a, road_b])
		self.__in_med_cycle[key][i] = True

	def __select_starting_points(self, n):	
		# N longest cycle edges
		edge_len = lambda a, b: (a[0] - b[0])**2 + (a[1] - b[1])**2
		hi_cycle_edges = list(self.hi_cycle_edges())
		longest_edges = sorted(hi_cycle_edges, key=lambda e: -edge_len(*e))

		points = []
		for a, b in longest_edges[:n]:
			# Get low level road path for that edge	
			road = self.road_network.oriented_road_for_edge(a, b)		
			
			# Deviated middle segment
			r = random.normalvariate(0.5, 0.2)
			r = min(max(r, 0.0), 0.95)
			n = len(road) - 1
			i = math.floor(n * r)
			
			self.__mark_in_med_cycle(a, b, i)
				
			edge = (road[i], road[i+1])
			points.append((road[i], edge))
		
		return points
	
	
	def __choose_control_parameters(self, profile):
		if profile == 'URBAN':
			self.segment_size = 30.0
			self.snap_size = 20.0
			self.degree = 3
			self.span_angle = 3.0*np.pi/2.0
			self.angle_deviation = 0.0
			self.join_probability = 1.0
		elif profile == 'SUBURBAN':
			self.segment_size = 40.0
			self.snap_size = 30.0
			self.degree = 2
			self.span_angle = 1.2*np.pi
			self.angle_deviation = 0.5
			self.join_probability = 0.4

		
		
	def __grow_from(self, pt):
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
				dist_sq = util.line_to_point_dist_sq(new_edge, c)
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
			dist_sq = util.line_to_point_dist_sq(edge, b)	
			if dist_sq < snap_size_sq:
				if join and (a != edge[0]) and (a != edge[1]):
					proj = util.project_on_segment(edge, b)
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
					proj = util.project_on_segment(edge, b)
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

		for cycle_edge in self.hi_cycle_edges():
			u = vec(cycle_edge[0], cycle_edge[1])
			v = vec(cycle_edge[0], b)
			cross_z = u[0]*v[1] - u[1]*v[0];
			if (cross_z > 0) or (util.line_to_point_dist_sq(cycle_edge, b) < snap_size_sq):
				if join:
					road = self.road_network.oriented_road_for_edge(*cycle_edge)
					def dist(i):
						p = road[i]
						return (p[0] - a[0])**2 + (p[1] - a[1])**2
						
					i = min(range(len(road)), key=dist)
					self.graph.add_edge(a, road[i])
					self.__mark_in_med_cycle(cycle_edge[0], cycle_edge[1], i)
					
				return False
		return True
			
	def __create_blender_road(self, name, parent, edge):
		curve = bpy.data.curves.new(name=name, type='CURVE')
		curve.dimensions = '3D'
		
		a, b = edge
		polyline = curve.splines.new('POLY')
		polyline.points.add(1)
		polyline.points[0].co = (a[0], a[1], self.terrain.height_at(*a), 1.0)
		polyline.points[1].co = (b[0], b[1], self.terrain.height_at(*b), 1.0)
		
		curve_obj = bpy.data.objects.new(name + "_curve", curve)
		curve_obj.parent = parent

		road = assets.load_object('secondary_road')
		road.name = name
		road.parent = parent
		
		length = util.distance(*edge)
		segment_length = road.dimensions.x

		scale = length / segment_length
		road.scale[0] = scale
		road.material_slots[0].material.texture_slots[0].scale[1] = scale
		
		curve_modifier = road.modifiers.new("Curve", type='CURVE')
		curve_modifier.object = curve_obj
		
		bpy.context.scene.objects.link(curve_obj)
		bpy.context.scene.objects.link(road)
		
		return road


	def full_graph(self):
		"""Graph combining secondary roads and surrounding primary road cycle."""
		graph = self.graph.copy()
		for edge in util.cycle_pairs(self.med_cycle):
			graph.add_edge(*edge)
		return graph
	
	
	def create_blender_object(self, root):
		parent = bpy.data.objects.new('secondary_roads', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)

		i = 0
		for edge in self.graph.edges_iter():
			self.__create_blender_road('secondary_road_'+str(i), parent, edge)
			i = i + 1
		
		return parent


class BlocksCell(RoadsCell):
	"""Roads city cell with city blocks containing buildings."""
	blocks = None # List of CityBlock objects
	
	def __init__(self, road_network, hi_cycle, lo_cycle):
		super(BlocksCell, self).__init__(road_network, hi_cycle, lo_cycle)		
	
	def __generate_blocks(self):
		full_graph = self.full_graph()
		self.block_cycles = mcb.planar_graph_cycles(full_graph)

		self.blocks = []
		for cycle in self.block_cycles:
			blk = block.CityBlock(self, cycle)
			blk.generate()
			self.blocks.append(blk)
	
	def generate(self):
		super(BlocksCell, self).generate()
	
		self.__generate_blocks()
		

	def create_blender_object(self, root):
		super(BlocksCell, self).create_blender_object(root)
		
		parent = bpy.data.objects.new('blocks', None)
		parent.parent = root
		bpy.context.scene.objects.link(parent)
		
		for block in self.blocks:
			block.create_blender_object(parent)
