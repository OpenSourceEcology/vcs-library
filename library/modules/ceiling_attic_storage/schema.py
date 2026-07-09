"""Ceiling schema."""

SCHEMA = {
    "schema_name": "Ceiling_With_Limited_Attic_Storage",
    "units": "in",
    "document_name": "Ceiling_Parametric_With_OSB_Decking",
    "name": "Ceiling_Parametric_With_OSB_Decking",

    # Overall finished outside dimensions of the entire ceiling assembly
    "width_in": 155,   # left to right
    "depth_in": 144,   # front to back

    # Options: "2x4", "2x6", "2x8", "2x10", "2x12"
    "lumber": "2x6",

    # Joists run front to back, between the doubled front/back rim joists
    "joist_spacing_in": 24,
    "first_joist_center_from_left_edge_in": 24,

    # Doubled rim joists on all four sides
    "rim_joist_count": 2,

    # Ceiling decking / attic storage deck
    "decking": {
        "include": True,
        "material": "OSB",
        "thickness_in": 0.75,
        "sheet_width_in": 48,
        "sheet_length_in": 96,
        "orientation": "perpendicular_to_joists",
        "stagger": True,
        "stagger_offset_in": 48,
        "gap_in": 0.125
    },

    "origin": (0, 0, 0)
}
