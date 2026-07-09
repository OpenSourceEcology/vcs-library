"""RAKE WALL ASSEMBLY SCHEMA Modular architecture, compiler included in this file. Includes: - Front wall: corner + 3 standard wall modules + corner, 12" high - Back wall:  corner + 3 standard wall modules + corner, 45.25" high - Left/right side rake walls sandwiched between front/back walls * 3 side rake modules per side * from front to back: 37", 48", 48" * total side clear span = 133" - Whole assembly elevation is parametric via assembly_base_z_in"""

SCHEMA = {
    "schema_name": "Rake_Wall_Assembly_Front_Back_Side_Rake_Modules",
    "units": "in",
    "document_name": "Rake_Wall_Assembly_Front_Back_Side_Rake_Modules_v6_Exact_3in12",

    "name": "Rake_Wall_Assembly_Front_Back_Side_Rake_Modules_v6_Exact_3in12",
    "units": "in",

    # -------------------------------------------------
    # OVERALL ASSEMBLY PARAMETERS
    # -------------------------------------------------
    "building_width_in": 155,
    "clear_span_between_front_back_walls_in": 133,

    # Side rake pitch target. With a 133" clear span, exact 3:12 gives
    # 33.25" rise from front to back.
    "side_rake_pitch_rise_per_12_in": 3.0,

    # Front/back wall heights
    "front_wall_height_in": 12,
    "back_wall_height_in": 45.25,  # exact 3:12 rise over 133" clear span (top of second plate = 46.75")

    # Whole-assembly placement / elevation
    # Example: set to 12 to place the bottom of all modules at Z = 12".
    "assembly_base_z_in": 0,
    "origin": (0, 0, 0),

    # -------------------------------------------------
    # FRONT/BACK MODULE LAYOUT
    # -------------------------------------------------
    # Front/back wall module sequence:
    #   corner + 3 standard wall modules + corner
    # Width math:
    #   5.5 + 48 + 48 + 48 + 5.5 = 155
    "corner_module_width_in": 5.5,
    "standard_module_width_in": 48,
    "standard_modules_per_wall": 3,

    # -------------------------------------------------
    # SIDE RAKE MODULE LAYOUT
    # -------------------------------------------------
    # Side walls are placed between the interior faces of the front/back walls.
    # From front to back:
    #   low module = 37"
    #   middle module = 48"
    #   high/back module = 48"
    # Total = 133" clear span.
    "side_rake_module_lengths_front_to_back_in": [37, 48, 48],

    # -------------------------------------------------
    # LUMBER / FRAMING PARAMETERS
    # -------------------------------------------------
    "wall_lumber": "2x6",
    "corner_long_lumber": "2x6",
    "corner_short_lumber": "2x3",
    "stud_spacing_in": 24,
    "bottom_plate": True,
    "top_plate": True,

    # -------------------------------------------------
    # SECOND / CONTINUOUS TOP PLATE
    # -------------------------------------------------
    # Adds one additional 2x6 plate directly on top of the module top plates:
    #   - front/back plates are 155" long
    #   - left/right side plates are 133" long and span only the clear distance
    #     between the front and back walls.
    "second_top_plate": True,
    "second_top_plate_lumber": "2x6",
    "second_top_plate_thickness_in": 1.5,
    "front_back_second_top_plate_length_in": 155,
    "left_right_second_top_plate_length_in": 133,

    # For the short/low side rake module, locate the interior stud from the
    # tallest/end stud rather than from the shortest/end stud.
    "short_side_rake_module_middle_stud_from_tallest": True,

    # OSB exterior face
    "include_osb": True,
    "osb_thickness_in": 0.5,

    # Optional labels / grouping names
    "front_wall_name": "Front_Wall",
    "back_wall_name": "Back_Wall",
    "left_wall_name": "Left_Rake_Wall",
    "right_wall_name": "Right_Rake_Wall",
}
