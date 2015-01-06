bl_info = {
	'name' : "City Generator",
	'description' : "Generate random city",
	'author' : "Tim Lenertz / Renzhi Deng",
	'location' : "Toolshelf > Create Tab",
	'category' : "Object"	
}

__all__ = ['city', 'plan', 'terrain', 'assets']

import imp
import math

if 'bpy' in locals():
	import imp
	imp.reload(city)
	imp.reload(plan)
	imp.reload(terrain)
	imp.reload(assets)
else:
	from . import city, plan, terrain, assets
	import bpy


bpy.types.Scene.city_name = bpy.props.StringProperty(
	name="Name",
	description="Name of root object for city",
	default="City",
)

bpy.types.Scene.terrain_roughness = bpy.props.FloatProperty(
	name="Roughness",
	description="Roughness of the terrain",
	default=0.6,
	min=0.0,
	max=4.0,
	subtype='FACTOR', 
	unit='NONE'
)

bpy.types.Scene.terrain_resolution = bpy.props.IntProperty(
	name="Resolution",
	description="Resolution of the terrain, i.e. number of times plane is subdivided",
	default=7,
	min=4,
	max=9,
	subtype='NONE'
)

bpy.types.Scene.terrain_initial_height_min = bpy.props.FloatProperty(
	name="Corner Elevation Min",
	description="Minimal Z coordinate for city corner",
	default=0.0,
	soft_min=-10.0,
	soft_max=10,
	subtype='DISTANCE',
	unit='LENGTH'
)

bpy.types.Scene.terrain_initial_height_max = bpy.props.FloatProperty(
	name="Corner Elevation Max",
	description="Maximal Z coordinate for city corner",
	default=0.0,
	soft_min=-10.0,
	soft_max=10,
	subtype='DISTANCE',
	unit='LENGTH'
)

bpy.types.Scene.terrain_area = bpy.props.FloatProperty(
	name="Area",
	description="Area of square city terrain. Side length will be square root of this",
	default=1000000.0,
	subtype='NONE',
	unit='AREA'
)

bpy.types.Scene.terrain_height = bpy.props.FloatProperty(
	name="Elevation",
	description="Multiplier for terrain elevation",
	default=50.0,
	soft_min=1.0,
	soft_max=250.0,
	subtype='FACTOR',
	unit='NONE'
)


bpy.types.Scene.plan_intersections = bpy.props.IntProperty(
	name="Street Intersections",
	description="Approximate number of primary street intersections",
	default=30,
	min=5,
	max=200,
	subtype='NONE'
)

bpy.types.Scene.plan_intersection_deviation = bpy.props.FloatProperty(
	name="Intersection Deviation",
	description="Controls how much primary street intersection positions deviate from regular grid layout. Smaller value corresponds to greater deviation.",
	default=4.0,
	min=1.0,
	max=30.0,
	subtype='FACTOR'
)


bpy.types.Scene.step_distance = bpy.props.FloatProperty(
	name="Step Distance",
	description="Step distance of primary street segments.",
	default=10.0,
	min=1.0,
	max=30.0,
	subtype='DISTANCE',
	unit='LENGTH'
)

bpy.types.Scene.snap_distance = bpy.props.FloatProperty(
	name="Snap Distance",
	description="Snap distance for primary street segments. Must be greater than step distance.",
	default=15.0,
	min=1.0,
	max=30.0,
	subtype='DISTANCE',
	unit='LENGTH'
)

bpy.types.Scene.deviation_angle = bpy.props.FloatProperty(
	name="Road Deviation",
	description="Angle by which roads can maximally deviate at each step.",
	default=math.radians(8.0),
	min=math.radians(0.0),
	max=math.radians(45.0),
	subtype='ANGLE',
	unit='ROTATION'
)



        
class CityGeneratorPanel(bpy.types.Panel):
	bl_label = "City Generator"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'TOOLS'
	bl_category = "City Generator"

	def draw(self, context):
		layout = self.layout
		scene = context.scene
		
		layout.prop(scene, 'city_name')
		
		box = layout.box()
		box.label("Terrain")
		box.prop(scene, 'terrain_roughness')
		box.prop(scene, 'terrain_resolution')
		box.prop(scene, 'terrain_initial_height_min')
		box.prop(scene, 'terrain_initial_height_max')
		box.prop(scene, 'terrain_area')
		box.prop(scene, 'terrain_height')
		
		box = layout.box()
		box.label("Primary Streets")
		box.prop(scene, 'plan_intersections')
		box.prop(scene, 'plan_intersection_deviation')
		box.prop(scene, 'step_distance')
		box.prop(scene, 'snap_distance')
		box.prop(scene, 'deviation_angle')
			
		layout.operator('city.generate')
		layout.operator('city.delete')


class OBJECT_OT_GenerateCity(bpy.types.Operator):
	bl_idname = 'city.generate'
	bl_label = "Generate new city"
	bl_description = "Generate city with given parameters."
		
	def execute(self, context):
		bpy.ops.city.delete()
	
		scene = context.scene
		cit = city.City()
		cit.terrain.roughness = scene.terrain_roughness
		cit.terrain.resolution = scene.terrain_resolution
		cit.terrain.initial_height_range = (
			scene.terrain_initial_height_min,
			scene.terrain_initial_height_max
		)
		cit.terrain.width = math.sqrt(scene.terrain_area)
		cit.terrain.height = scene.terrain_height
		cit.plan.road_network.approximate_number_of_intersection_points = scene.plan_intersections
		cit.plan.road_network.edges_deviation = scene.plan_intersection_deviation
		cit.plan.road_network.road_step_distance = scene.step_distance
		cit.plan.road_network.road_snap_distance = scene.snap_distance
		cit.plan.road_network.road_deviation_angle = scene.deviation_angle
		
		cit.generate()
		city_root = cit.create_blender_object(scene.city_name)
		bpy.context.scene.objects.link(city_root)
		return { 'FINISHED' }


class OBJECT_OT_DeleteCity(bpy.types.Operator):
	bl_idname = 'city.delete'
	bl_label = "Delete city"
	bl_description = "Delete city with the given name."
	
	def execute(self, context):
		if context.scene.city_name in bpy.data.objects:
			city = bpy.data.objects[context.scene.city_name]
			bpy.ops.object.select_all(action='DESELECT')
			bpy.context.scene.objects.active = city
			city.select = True
			bpy.ops.object.select_grouped(type='CHILDREN_RECURSIVE', extend=True)
			bpy.ops.object.delete(use_global=False)
		
		return { 'FINISHED' }



def register():
	bpy.utils.register_module(__name__)

def unregister():
	bpy.utils.unregister_module(__name__)