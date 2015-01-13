# based on The Minimal Cycle Basis for a Planar Graph (David Eberly)

import networkx as nx
import functools

class Primitive:
	type = None # Can be 'ISOLATED_VERTEX', 'FILAMENT', 'MINIMAL_CYCLE'
	vertices = None

	def __init__(self, type):
		self.vertices = []
		self.type = type
	
	def mark_cycle_edges(self, graph):
		v0 = self.vertices[0]
		for v1 in self.vertices[1:]:
			graph.edge[v0][v1]['cycle_edge'] = True
			v0 = v1
		graph.edge[v0][self.vertices[0]]['cycle_edge'] = True

def vertex_cmp(a, b):
	lower = (a[0] < b[0]) or ((a[0] == b[0]) and (a[1] < b[1]))
	return 1 if lower else -1


def num_adjacent(graph, vertex):
	if not graph.has_node(vertex):
		return 0
	else:
		neighbors = nx.all_neighbors(graph, vertex)
		return len(list(neighbors))

def adjacent(graph, vertex):
	if not graph.has_node(vertex):
		return None
	else:
		neighbors = nx.all_neighbors(graph, vertex)
		return list(neighbors)


def extract_isolated_vertex(graph, v0, heap, primitives):
	primitive = Primitive('ISOLATED_VERTEX')
	primitive.vertices.append(v0)
	heap.remove(v0)
	graph.remove_node(v0)
	primitives.append(v0)

def is_cycle_edge(graph, v0, v1):
	return 'cycle_edge' in graph.edge[v0][v1]

def extract_filament(graph, v0, v1, heap, primitives):
	if is_cycle_edge(graph, v0, v1):
		if num_adjacent(graph, v0) >= 3:
			graph.remove_edge(v0, v1)
			v0 = v1
			if num_adjacent(graph, v0) == 1:
				v1 = adjacent(graph, v0)[0]
		
		while num_adjacent(graph, v0) == 1:
			v1 = adjacent(graph, v0)[0]
			if is_cycle_edge(graph, v0, v1):
				heap.remove(v0)
				graph.remove_edge(v0, v1)
				graph.remove_node(v0)
				v0 = v1
			else:
				break
		
		if num_adjacent(graph, v0) == 0:
			heap.remove(v0)
			graph.remove_node(v0)
	
	else:
		primitive = Primitive('FILAMENT')
		
		if num_adjacent(graph, v0) >= 3:
			primitive.vertices.append(v0)
			graph.remove_edge(v0, v1)
			v0 = v1
			if num_adjacent(graph, v0) == 1:
				v1 = adjacent(graph, v0)[0]

		while num_adjacent(graph, v0) == 1:
			primitive.vertices.append(v0)
			v1 = adjacent(graph, v0)[0]
			heap.remove(v0)
			graph.remove_edge(v0, v1)
			graph.remove_node(v0)
			v0 = v1
		
		primitive.vertices.append(v0)
		if num_adjacent(graph, v0) == 0:
			heap.remove(v0)
			graph.remove_node(v0)

		primitives.append(primitive)

def dot_perp(v0, v1):
	x0, y0 = v0
	x1, y1 = v1
	return x0*y1 - x1*y0


def get_clockwise_most(graph, vprev, vcurr):
	if num_adjacent(graph, vcurr) == 0:
		return None
	
	vnext = None

	adj = adjacent(graph, vcurr)
	for vadj in adj:
		if vadj is not vprev:
			vnext = vadj
			break
	if vnext is None:
		return None
		
	if vprev is not None:
		dcurr = (vcurr[0] - vprev[0], vcurr[1] - vprev[1])
	else:
		dcurr = (0, -1)
	dnext = (vnext[0] - vcurr[0], vnext[1] - vcurr[1])
	
	vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)

	for vadj in adj:
		dadj = (vadj[0] - vcurr[0], vadj[1] - vcurr[1])
		if vcurrIsConvex:
			if (dot_perp(dcurr, dadj) < 0) or (dot_perp(dnext, dadj) < 0):
				vnext = vadj
				dnext = dadj
				vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)
		else:
			if (dot_perp(dcurr, dadj) < 0) and (dot_perp(dnext, dadj) < 0):
				vnext = vadj
				dnext = dadj
				vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)
	
	return vnext


def get_counterclockwise_most(graph, vprev, vcurr):
	if num_adjacent(graph, vcurr) == 0:
		return None
	
	vnext = None

	adj = adjacent(graph, vcurr)
	for vadj in adj:
		if vadj is not vprev:
			vnext = vadj
			break
	if vnext is None:
		return None
	
	if vprev is not None:
		dcurr = (vcurr[0] - vprev[0], vcurr[1] - vprev[1])
	else:
		dcurr = (0, -1)
	dnext = (vnext[0] - vcurr[0], vnext[1] - vcurr[1])
	
	vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)

	for vadj in adj:
		dadj = (vadj[0] - vcurr[0], vadj[1] - vcurr[1])
		if vcurrIsConvex:
			if (dot_perp(dcurr, dadj) > 0) and (dot_perp(dnext, dadj) > 0):
				vnext = vadj
				dnext = dadj
				vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)
		else:
			if (dot_perp(dcurr, dadj) > 0) or (dot_perp(dnext, dadj) > 0):
				vnext = vadj
				dnext = dadj
				vcurrIsConvex = (dot_perp(dnext, dcurr) <= 0)
	
	return vnext



def extract_primitive(graph, v0, heap, primitives):
	visited = set()
	sequence = [v0]
	
	v1 = get_clockwise_most(graph, None, v0)
	vprev = v0
	vcurr = v1
	
	print(v0, v1)
	
	while (vcurr != None) and (vcurr != v0) and (vcurr not in visited):
		sequence.append(vcurr)
		visited.add(vcurr)
		vnext = get_counterclockwise_most(graph, vprev, vcurr)
		vprev = vcurr
		vcurr = vnext
	
	if vcurr is None:
		extract_filament(graph, vprev, adjacent(graph, vprev)[0], heap, primitives)
		
	elif vcurr is v0:
		primitive = Primitive('MINIMAL_CYCLE')
		primitive.vertices = primitive.vertices + sequence
		primitive.mark_cycle_edges(graph)
		primitives.append(primitive)
		graph.remove_edge(v0, v1)
		if num_adjacent(graph, v0) == 1:
			extract_filament(graph, v0, adjacent(graph, v0)[0], heap, primitives)
		if num_adjacent(graph, v1) == 1:
			extract_filament(graph, v1, adjacent(graph, v1)[0], heap, primitives)

	else:
		adj = adjacent(graph, v0)
		while len(adj) == 2:
			if adj[0] is not v1:
				v1 = v0
				v0 = adj[0]
			else:
				v1 = v0
				v0 = adj[1]
			adj = adjacent(graph, v0)
		extract_filament(graph, v0, v1, heap, primitives)


def extract_primitives(graph, primitives):
	heap = sorted(graph.nodes(), key=functools.cmp_to_key(vertex_cmp))
	i = 0
	while len(heap) > 0:
		i += 1
		if i > 1000:
			break

		vertex = heap[-1]
		adj = adjacent(graph, vertex)
		if len(adj) == 0:
			extract_isolated_vertex(graph, vertex, heap, primitives)
		elif len(adj) == 1:
			extract_filament(graph, vertex, adj[0], heap, primitives)
		else:
			extract_primitive(graph, vertex, heap, primitives)


def planar_graph_cycles(graph):
	primitives = []
	cycles = []
	extract_primitives(graph, primitives)
	for primitive in primitives:
		if primitive.type == 'MINIMAL_CYCLE':
			cycles.append(primitive.vertices)
	return cycles