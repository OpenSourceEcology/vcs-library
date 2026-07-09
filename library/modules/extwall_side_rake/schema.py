"""Side rake wall module schema."""

SCHEMA = {
    "schema_name": "Side_Rake_Wall_Module",
    "units": "in",
    "document_name": "Side_Rake_Wall_Module_Parametric_U_Corners_v2",
    "name": "Side_Rake_Wall_Module_Parametric_U_Corners_v2",

    # -------------------------------------------------
    # PRIMARY EDITABLE PARAMETERS
    # -------------------------------------------------

    # Overall module width, left to right
    "module_width_in": 48,

    # Height at the high end of the module
    "high_end_height_in": 60,

    # Roof/wall rake slope, expressed as inches of drop per foot of run
    # Example: 3 = 3 inches of drop per 12 inches of horizontal run
    "slope_drop_per_foot_in": 3,

    # Which side is the high side
    # Options: "left", "right"
    "high_side": "right",

    # Lumber size for studs, plates, and U-corner pieces
    # Options: "2x4", "2x6", "2x8", "2x10", "2x12"
    "lumber": "2x6",

    # Stud spacing
    "stud_spacing_in": 24,

    # -------------------------------------------------
    # CORNER REINFORCEMENT
    # Uses the same U-corner geometry as the standard wall module.
    # -------------------------------------------------

    "left_corner_reinforcement": True,
    "right_corner_reinforcement": True,

    # -------------------------------------------------
    # OSB
    # -------------------------------------------------

    "include_osb": True,
    "osb_thickness_in": 0.5,

    # -------------------------------------------------
    # PLACEMENT
    # -------------------------------------------------

    "origin": (0, 0, 0)
}
