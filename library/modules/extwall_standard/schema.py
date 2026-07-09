"""Wall module schema."""

SCHEMA = {
    "schema_name": "Wall_Module",
    "units": "in",
    "document_name": "Parametric_Wall_Module",

    "module_width_in": 48,
    "stud_height_in": 92.625,
    "stud_spacing_in": 24,

    # Options: "2x4", "2x6", "2x8"
    "lumber": "2x6",

    "osb_thickness_in": 0.5,
    "osb_sheet_height_in": 96,

    # Optional additions
    "left_corner_reinforcement": True,
    "right_corner_reinforcement": True,

    "origin": (0, 0, 0)
}
