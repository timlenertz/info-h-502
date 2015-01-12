import math
import functools
import networkx as nx


def line_to_point_dist_sq(line, p):
	a, b = line
	num = ( (b[1] - a[1])*p[0] - (b[0] - a[0])*p[1] + b[0]*a[1] - b[1]*a[0] )**2
	den = (b[1] - a[1])**2 + (b[0] - a[0])**2
	return num / den

def distance_sq(a, b):
	return (a[0] - b[0])**2 + (a[1] - b[1])**2

def distance(a, b):
	return math.sqrt(distance_sq(a, b))
	
def projection_is_on_segment(seg, p, seg_length=None):
	if seg_length is None:
		seg_length = distance(*seg)
	a, b = seg
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (dot > 0) and (dot < seg_length)

def project_on_segment(seg, p):
	a, b = seg
	seg_length = distance(*seg)
	ap = (p[0] - a[0], p[1] - a[1])
	ab = (b[0] - a[0], b[1] - a[1])
	ab = (ab[0] / seg_length, ab[1] / seg_length)
	dot = ab[0]*ap[0] + ab[1]*ap[1]
	return (a[0] + dot*ab[0], a[1] + dot*ab[1])

def segment_intersection(seg1, seg2):
	seg1_len = distance(*seg1)
	seg2_len = distance(*seg2)

	test = lambda seg, seg_len, p: projection_is_on_segment(seg, p, seg_length=seg_len)
	
	return test(seg1, seg1_len, seg2[0]) and test(seg1, seg1_len, seg2[1]) and test(seg2, seg2_len, seg1[0]) and test(seg2, seg2_len, seg1[1])


def planar_graph_cycles(graph):
	# from: http://mathoverflow.net/questions/23811/reporting-all-faces-in-a-planar-graph
	def Faces(edges,embedding):
		"""
		edges: is an undirected graph as a set of undirected edges
		embedding: is a combinatorial embedding dictionary. Format: v1:[v2,v3], v2:[v1], v3:[v1] clockwise ordering of neighbors at each vertex.)
		"""

		# Establish set of possible edges
		edgeset = set()
		for edge in edges: # edges is an undirected graph as a set of undirected edges
			edge = list(edge)
			edgeset |= set([(edge[0],edge[1]),(edge[1],edge[0])])

		# Storage for face paths
		faces = []
		path = []
		for edge in edgeset:
			path.append(edge)
			edgeset -= set([edge])
			break # (Only one iteration)

		# Trace faces
		while (len(edgeset) > 0):
			neighbors = embedding[path[-1][-1]]
			next_node = neighbors[(neighbors.index(path[-1][-2])+1)%(len(neighbors))]
			tup = (path[-1][-1],next_node)
			if tup == path[0]:
				faces.append(path)
				path = []
				for edge in edgeset:
					path.append(edge)
					edgeset -= set([edge])
					break # (Only one iteration)
			else:
				path.append(tup)
				edgeset -= set([tup])
		if (len(path) != 0): faces.append(path)
		return iter(faces)

	
	embedding = dict()
	def clockwise(o, a, b):
		oa = (a[0] - o[0], a[1] - o[1])
		ob = (b[0] - o[0], b[1] - o[1])
		cross_z = oa[0]*ob[1] - oa[1]*ob[0]
		return 1 if cross_z > 0 else -1
		
	for node in graph.nodes_iter():
		neighbors = nx.all_neighbors(graph, node)
		compare = lambda a, b: clockwise(node, a, b)
		key = functools.cmp_to_key(compare)
		neighbors = sorted(neighbors, key=key)
		embedding[node] = neighbors
	
	faces_edges = Faces(graph.edges(), embedding)
	
	faces_nodes = []
	for face_edges in faces_edges:
		nodes = []
		for a, b in face_edges:
			nodes.append(a)
		faces_nodes.append(nodes)
	
	return faces_nodes
