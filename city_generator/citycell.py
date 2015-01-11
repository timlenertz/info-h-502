import numpy as np
import random
import math
import bpy
import networkx as nx

from . import assets, util	

class Cell(object):
	"""City cell encloded by primary road cycle."""
	def __init__(self, road_network, cycle):
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



class RoadsCell(Cell):
	"""City cell which contains secondary roads."""
	def __init__(self, road_network, cycle):
		super(RoadsCell, self).__init__(road_network, cycle)
		
		self.__choose_control_parameters()
		
	
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
				
			edge = (a, b)
			points.append((a, edge))
		
		return points
	
	
	def __choose_control_parameters(self):
		self.segment_size = 15.0
		self.snap_size = 5.0
		self.degree = 3
		self.join_probability = 0.2
		
		
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
			
			r = random.normalvariate(0.5, 0.4)
			r = min(max(r, 0.0), 1.0)
			
			rel_angle = mn + r * (mx - mn)
			edge_angle = np.arctan2(pt[1] - prev[1], pt[0] - prev[0])
			angle = edge_angle - np.pi/2 + rel_angle
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
		elif not self.__node_distance_test(new_edge, join):
			return True
		elif not self.__edge_distance_test(new_edge, join):
			return True
		elif not self.__edge_intersection_test(new_edge, join):
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

		for cycle_edge in self.cycle:
			u = vec(cycle_edge[0], cycle_edge[1])
			v = vec(cycle_edge[0], b)
			cross_z = u[0]*v[1] - u[1]*v[0];
			if (cross_z > 0) or (util.line_to_point_dist_sq(cycle_edge, b) < snap_size_sq):
				if join:
					road = self.road_network.road_for_edge(*cycle_edge)
					dist = lambda p: (p[0] - a[0])**2 + (p[1] - a[1])**2
					p = min(road, key=dist)
					self.graph.add_edge(a, p)
				return False
		return True
		
	
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