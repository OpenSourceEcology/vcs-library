"""RAKE WALL ASSEMBLY SCHEMA"""

SCHEMA = {
    "schema_name": "Rake_Wall_Assembly_Parametric_Base_Z",
    "units": "in",
    "document_name": "Rake_Wall_Assembly_155x144_v10_Parametric_Base_Z",

    "name": "Rake_Wall_Assembly_155x144_v10_Parametric_Base_Z",
    "units": "in",

    # Overall footprint
    "building_width_in": 155,
    "building_depth_in": 144,

    # Wall/module parameters
    "module_width_in": 48,
    "modules_per_wall": 3,
    "wall_lumber": "2x6",
    "stud_spacing_in": 24,
    "osb_thickness_in": 0.5,

    # Heights
    # Front wall is low, back wall is high.
    "front_height_in": 12,
    "back_height_in": 48,

    # Top/bottom plates
    "bottom_plate": True,
    "top_plate": True,

    # -------------------------------------------------
    # SECOND / CONTINUOUS TOP PLATE
    # -------------------------------------------------
    # Adds one additional 2x6 plate directly on top of the
    # module top plates:
    #   - front and back plates are 155" long
    #   - left and right plates are 144" long
    # The plates follow the same global rake plane and sit directly
    # on the upper face of the module top plates.
    "second_top_plate": True,
    "second_top_plate_lumber": "2x6",
    "second_top_plate_thickness_in": 1.5,
    "front_back_second_top_plate_length_in": 155,
    "left_right_second_top_plate_length_in": 144,

    # OSB exterior face
    "include_osb": True,

    # -------------------------------------------------
    # SIDE-WALL U-CORNER REINFORCEMENT
    # -------------------------------------------------
    # Adds U-shaped corner assemblies to the first and last modules
    # of both side walls. Geometry follows the depth/side-rake module
    # U-corner logic:
    #   1) normal stud on edge,
    #   2) flat 2x lumber at the interior side,
    #   3) second 2x lumber on edge.
    # The bottom/closed side of the U faces the inside of the building;
    # the open side faces the exterior OSB.
    "side_wall_u_corner_reinforcement": True,
    "left_wall_front_u_corner_reinforcement": True,
    "left_wall_back_u_corner_reinforcement": True,
    "right_wall_front_u_corner_reinforcement": True,
    "right_wall_back_u_corner_reinforcement": True,

    # -------------------------------------------------
    # ASSEMBLY PLACEMENT / ELEVATION
    # -------------------------------------------------
    # Raises or lowers the entire assembly.
    # Example: set to 12 to place the bottom of all wall modules at Z = 12".
    "assembly_base_z_in": 0,

    # Optional global XYZ translation, also in inches.
    # assembly_base_z_in is added to the Z value here.
    "origin": (0, 0, 0)
}
