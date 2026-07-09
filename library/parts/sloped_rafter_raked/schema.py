"""Single sloped roof rafter with raked-wall birdsmouth cuts."""

SCHEMA = {
    "schema_name": "Single_Sloped_Roof_Rafter_With_Raked_Wall_Birdsmouth",
    "units": "in",

    # Document
    "document_name": "Single_Roof_Rafter_Raked_Wall_Birdsmouth",
    "clear_existing_document": False,

    # Building / rake wall assembly geometry
    "building_width_in": 155.0,
    "building_depth_in": 144.0,

    # These heights should describe the TOP BEARING PLANE where the rafter sits.
    # Defaults account for the second top plate:
    #   front wall bearing = 13.5"
    #   back wall bearing  = 49.5"
    # Over 144", that is a 36" rise = 3:12.
    "front_height_in": 13.5,
    "back_height_in": 49.5,

    # Whole-assembly elevation offset. Match rake wall assembly_base_z_in if used.
    "assembly_base_z_in": 0.0,

    # Rafter lumber
    "lumber_size": "2x6",
    "actual_size_in": {
        "2x6": {"thickness_in": 1.5, "depth_in": 5.5}
    },

    # Placement of this single rafter across building width.
    # This is the LEFT FACE of the rafter in global X, matching the wall assembly.
    "rafter_x_in": 0.0,

    # Front/back overhangs, measured as horizontal projection.
    "front_overhang_in": 24.0,
    "back_overhang_in": 24.0,

    # -------------------------------------------------
    # RAKED-WALL BIRDSMOUTH CUTS
    # -------------------------------------------------
    "include_birdsmouth_cuts": True,

    # For a 2x6 actual depth of 5.5", the common max notch depth is 1/4 depth:
    # 5.5 / 4 = 1.375" = 1-3/8".
    # This is the vertical depth below the raked bearing/seat plane.
    "birdsmouth_depth_in": 1.375,

    # This assembly has 2x6 front/back rake walls, so the raked seat should cover
    # the wall/top-plate depth from exterior face to interior face.
    "front_back_wall_depth_in": 5.5,

    # Front wall occupies Y = 0 to wall_depth.
    # Back wall occupies Y = building_depth - wall_depth to building_depth.
    "front_wall_outer_y_in": 0.0,
    "back_wall_outer_y_in": 144.0,

    # Minimum bearing/reference check only. Does not change geometry.
    "minimum_bearing_in": 1.5,

    # Optional vertical adjustment after placement.
    "z_offset_in": 0.0,

    # Optional reference geometry for debugging/placement.
    "show_reference_lines": True,
    "reference_line_size_in": 0.35,
}
