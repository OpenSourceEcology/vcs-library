"""Window module schema."""

SCHEMA = {
    "schema_name": "Window_Module",
    "units": "in",
    "document_name": "Parametric_Window_Module",

    "module_width_in": 48,
    "stud_height_in": 92.625,
    "stud_spacing_in": 24,

    # Options: "2x4", "2x6", "2x8"
    "lumber": "2x6",

    "window_rough_width_in": 24,
    "window_rough_height_in": 36,
    "window_sill_height_in": 36,
    "window_left_in": None,

    "building_width_in": 144,
    "clear_span_floors_above": 2,

    "header_ply_count": 2,
    "flat_header_nailer": True,

    "blocking": True,
    "blocking_spacing_in": 24,

    "include_osb": True,
    "osb_thickness_in": 0.5,
    "osb_sheet_width_in": 48,
    "osb_sheet_height_in": 96,

    "origin": (0, 0, 0)
}
