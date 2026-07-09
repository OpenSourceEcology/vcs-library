"""CABIN FLOOR + WALLS + SINGLE TOP PLATE ASSEMBLY Single-file FreeCAD script Includes: framed floor with top/bottom sheathing, standard wall module, window module, single-door module, single 2x6 top plate, and cabin assembly compiler."""

SCHEMA = {
    "schema_name": "Cabin_Floor_Walls_Single_Top_Plate_Assembly",
    "units": "in",
    "document_name": "Cabin_155x144_Floor_Walls_Single_Top_Plate",

    "name": "Cabin_155x144_Floor_Walls_Only",

    "floor": {
        "width_in": 155,
        "depth_in": 144,

        # Framed floor assembly
        # Coordinate convention:
        #   X = left/right, Y = front/back, Z = up
        #   Joists run front-to-back along Y.
        # IRC-style floor joist sizing depends on species, grade, live load, dead load, and span.
        # User-selected floor framing lumber for this assembly.
        "framing_lumber": "2x8",
        "joist_spacing_in": 24,
        "double_rim_joists": True,

        # Sheathing: individual 4x8 sheets, staggered.
        "sheet_width_in": 48,
        "sheet_length_in": 96,
        "top_sheathing_material": "OSB",
        "top_osb_thickness_in": 0.75,
        "bottom_sheathing_material": "Pressure_Treated_Plywood",
        "bottom_osb_thickness_in": 0.75,
    },

    "common_wall": {
        "module_width_in": 48,
        "stud_height_in": 92.625,
        "stud_spacing_in": 24,
        "lumber": "2x6",
        "osb_thickness_in": 0.5,
        "osb_sheet_width_in": 48,
        "osb_sheet_height_in": 96,
        "include_osb": True,
    },

    "single_top_plate": {
        "include": True,
        "lumber": "2x6",
        "thickness_in": 1.5,
        "min_seam_distance_from_module_edge_in": 24,

        # Preferred stock lengths. The compiler uses the longest practical
        # single board for each wall when possible, then falls back to seams
        # that are at least 24 in from module edges.
        "preferred_stock_lengths_in": [240, 192, 168, 144, 120, 96],

        # For this 155 x 144 cabin:
        #   front/back plates are 155 in, cut from 14 ft stock
        #   left/right plates are 133 in, cut from 12 ft stock
        # Plates are added as a separate cap layer above the module top plates.
        # Front/back plates claim the corner intersections.
        # Left/right plates fit between front/back plates to avoid physical overlap.
        "front_back_cut_from_stock_in": 168,
        "left_right_cut_from_stock_in": 144,
    },

    # Coordinate convention:
    # X = left/right, Y = front/back, Z = up.
    # Floor lower-left/front corner is (0, 0, 0).
    # Front wall is at Y=0. Back wall is at Y=144.
    # Left wall is at X=0. Right wall is at X=155.
    # OSB faces outside the cabin.
    "walls": [
        {
            "name": "Left_Wall",
            "side": "left",
            "modules": [
                {"type": "standard", "right_corner_reinforcement": True, "left_corner_reinforcement": False},
                {"type": "standard", "right_corner_reinforcement": False, "left_corner_reinforcement": False},
                {"type": "standard", "right_corner_reinforcement": False, "left_corner_reinforcement": True},
            ],
        },
        {
            "name": "Right_Wall",
            "side": "right",
            "modules": [
                {"type": "standard", "left_corner_reinforcement": True, "right_corner_reinforcement": False},
                {"type": "standard", "left_corner_reinforcement": False, "right_corner_reinforcement": False},
                {"type": "standard", "left_corner_reinforcement": False, "right_corner_reinforcement": True},
            ],
        },
        {
            "name": "Front_Wall",
            "side": "front",
            "start_offset_in": 5.5,
            "modules": [
                {
                    "type": "window",
                    "window_rough_width_in": 30,
                    "window_rough_height_in": 60,
                    "window_sill_height_in": 24,
                    "window_left_in": None,
                },
                {
                    "type": "door",
                    "door_rough_width_in": 38.25,
                    "door_rough_height_in": 82,
                    "door_left_in": None,
                },
                {
                    "type": "window",
                    "window_rough_width_in": 30,
                    "window_rough_height_in": 60,
                    "window_sill_height_in": 24,
                    "window_left_in": None,
                },
            ],
        },
        {
            "name": "Back_Wall",
            "side": "back",
            "start_offset_in": 5.5,
            "modules": [
                {"type": "standard", "left_corner_reinforcement": False, "right_corner_reinforcement": False},
                {
                    "type": "door",
                    "door_rough_width_in": 38.25,
                    "door_rough_height_in": 82,
                    "door_left_in": None,
                },
                {"type": "standard", "left_corner_reinforcement": False, "right_corner_reinforcement": False},
            ],
        },
    ],
}
