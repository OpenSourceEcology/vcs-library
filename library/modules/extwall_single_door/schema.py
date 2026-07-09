"""Door module schema."""

SCHEMA = {
    "schema_name": "Door_Module",
    "units": "in",
    "document_name": "Parametric_Door_Module",

    "module_width_in": 48,
    "stud_height_in": 92.625,
    "stud_spacing_in": 24,

    # Options: "2x4", "2x6", "2x8"
    "lumber": "2x6",

    # Door rough opening
    # Height is measured from the floor / bottom of module
    "door_rough_width_in": 38.25,
    "door_rough_height_in": 82,
    "door_left_in": None,

    # Header
    "header_lumber": "2x8",
    "header_ply_count": 2,
    "flat_header_nailer": True,

    # Blocking between king studs and jack studs
    "blocking": True,
    "blocking_spacing_in": 25,

    "include_osb": True,
    "osb_thickness_in": 0.5,
    "osb_sheet_width_in": 48,
    "osb_sheet_height_in": 96,

    "origin": (0, 0, 0)
}
