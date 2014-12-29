import numpy as np
import random
import bpy
import math
import scipy.spatial


class PrimaryRoadNetwork:
	number_of_intersection_points = 10
	maximal_removed_edges = 10
	edges_deviation = 20.0

	road_step_distance = 0.05
	road_number_of_samples = 15
	road_snap_distance = 0.1
	road_deviation_angle = math.radians(10.0)


	def __init__(self, terrain):
		self.terrain = terrain
	
	def __choose_intersection_points(self):
		# Subdivide terrain into grid where cell side length is power of 2
		# such that there are at least as many cells as points 
		n = self.number_of_intersection_points
		depth = int(math.ceil(math.log(n, 4)))
		side_number_of_cells = 2**depth
		number_of_cells = side_number_of_cells**2
		assert number_of_cells >= n
		cell_side_length = 1.0 / side_number_of_cells
		def cell_center(i):
			x = i % side_number_of_cells
			y = i // side_number_of_cells
			center_x = cell_side_length/2.0 + x*cell_side_length
			center_y = cell_side_length/2.0 + y*cell_side_length
			return (center_x, center_y)
		
		# Randomly choose cells that will contain intersection
		intersection_cells = []
		for i in range(n):
			cell = random.randint(0, number_of_cells - 1)
			while cell in intersection_cells:
				cell = random.randint(0, number_of_cells - 1)
			intersection_cells.append(cell)
		
		# Randomly place intersection points in these cells
		self.intersection_points = []
		for c in intersection_cells:
			center_x, center_y = cell_center(c)
			sigma = cell_side_length / self.edges_deviation
			x = random.normalvariate(center_x, sigma)
			y = random.normalvariate(center_y, sigma)
			self.intersection_points.append((x, y))
			
		
	
	def __create_high_level_graph(self):
		# Create delaunay triangulation
		triangulation = scipy.spatial.Delaunay(self.intersection_points)
		self.adjacency = []
		indices, indptr = triangulation.vertex_neighbor_vertices
		for k in range(self.number_of_intersection_points):
			neighboring = indptr[indices[k]:indices[k+1]]
			self.adjacency.append(neighboring.tolist())
		
		# Randomly remove some edges such that graph remains connected
		def path_exists(a, b, without_edge, without_vertices):
			if a == b:
				return True
			for adjacent in self.adjacency[a]:
				if adjacent in without_vertices:
					continue
				elif (a, adjacent) == without_edge or (adjacent, a) == without_edge:
					continue
				elif adjacent == b:
					return True
				else:
					exists = path_exists(adjacent, b, without_edge, without_vertices + [adjacent])
					if exists:
						return True
			return False
	
		def alternate_path_exists(a, b):
			return path_exists(a, b, (a, b), [])
		
		def remove_edge(a, b):
			assert (b in self.adjacency[a])
			assert (a in self.adjacency[b])
			self.adjacency[a].remove(b)
			self.adjacency[b].remove(a)
	
		hull = triangulation.convex_hull
		for i in range(self.maximal_removed_edges): 
			a = random.randint(0, len(self.adjacency)-1)
			b = random.choice(self.adjacency[a])
			if len(self.adjacency[a]) <= 1 or len(self.adjacency[b]) <= 1:
				continue
			if (a in hull) and (b in hull):
				continue
			if alternate_path_exists(a, b):
				remove_edge(a, b)
				

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
		max_iterations = 100
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

					
	def plot_high_level(self):
		lines = []
		for a, adj in enumerate(self.adjacency):
			for b in adj:
				line = (self.intersection_points[a], self.intersection_points[b])
				lines.append(line)
		lc = mc.LineCollection(lines)
		fig, ax = plt.subplots()
		ax.add_collection(lc)
		ax.autoscale()

		
	def generate(self):
		self.__choose_intersection_points()
		self.__create_high_level_graph()
		self.plot_high_level()
		self.__create_low_level_graph()
		
		lines = []
		for road in self.roads.values():
			for i in range(len(road)-1):
				lines.append((road[i], road[i+1]))
					
			
		lc = mc.LineCollection(lines)
		fig, ax = plt.subplots()
		ax.add_collection(lc)
		ax.autoscale()





class Terrain:
	"""Generates random terrain height map, using diamond-square algorithm."""

	initial_height_range = (0.0, 1.0)
	roughness = 1.0
	resolution = 8

	def __init__(self):
		pass

	def __square(self, pos, r, d):
		x, y = pos
		positions = [
			(y - r, x - r),
			(y - r, x + r),
			(y + r, x - r),
			(y + r, x + r)
		];
		self.image[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __diamond(self, pos, r, d):
		x, y = pos
		positions = [
			(y - r, x),
			(y, x - r),
			(y, x + r),
			(y + r, x)
		];
		self.image[y, x] = self.__average(positions) + random.uniform(-d, d)


	def __average(self, positions):
		values = []
		for y, x in positions:
			if (0 <= x < self.side_length) and (0 <= y < self.side_length):
				value = self.image[y, x]
				if not np.isnan(value):
					values.append(value)
		return np.mean(values)
	
	
	def __subdivide(self, full, d):
		half = full // 2
		if(half < 1):
			return
			
		for y in range(half, self.side_length, full):
			for x in range(half, self.side_length, full):
				self.__square((x, y), half, d)

		for y in range(0, self.side_length, half):
			for x in range((y + half)%full, self.side_length, full):
				self.__diamond((x, y), half, d)
		
		self.__subdivide(half, d / 2.0)

	def height_at(self, x, y):
		x_ind = int(math.floor(x * self.side_length))
		x_ind = min(x_ind, self.side_length - 1)
		x_ind = max(x_ind, 0)
					
		y_ind = int(math.floor(y * self.side_length))
		y_ind = min(y_ind, self.side_length - 1)
		y_ind = max(y_ind, 0)
	
		return self.image[y_ind, x_ind]
	
	def generate(self):
		self.side_length = 2**self.resolution + 1
		self.image = np.empty((self.side_length, self.side_length))
		self.image.fill(np.nan)

		self.image[0, 0] = random.uniform(*self.initial_height_range)
		self.image[0, -1] = random.uniform(*self.initial_height_range)
		self.image[-1, 0] = random.uniform(*self.initial_height_range)
		self.image[-1, -1] = random.uniform(*self.initial_height_range)

		self.__subdivide(self.side_length - 1, self.roughness)

class City:
	def __init__(self):
		self.terrain = Terrain()
	
	def generate(self):
		self.terrain.generate()
	
	def create_blender_object(self, name="City"):
		scene = bpy.context.scene
	
		# Root
		root = bpy.data.objects.new(name=name, object_data=None)
		
		# Terrain
		scale = (20.0, 20.0, 1.0)
		terrain_mesh = self.terrain.create_blender_mesh(scale)
		terrain_obj = bpy.data.objects.new("Terrain", terrain_mesh)
		terrain_obj.parent = root
		scene.objects.link(terrain_obj)
		
		return root