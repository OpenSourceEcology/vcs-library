import FreeCAD as App
import Part

# =====================================================
# DOOR MODULE SCHEMA — EDIT THIS SECTION
# =====================================================

door_module_schema = {
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

# =====================================================
# DOOR MODULE COMPILER
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25
}

def compile_door_module(schema):
    ox, oy, oz = schema["origin"]
    ox *= IN
    oy *= IN
    oz *= IN

    module_width = schema["module_width_in"] * IN
    stud_height = schema["stud_height_in"] * IN
    spacing = schema["stud_spacing_in"] * IN

    lumber = schema["lumber"]
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported wall lumber size: " + lumber)

    wall_depth = LUMBER_SIZES[lumber] * IN
    t = 1.5 * IN

    rough_w = schema["door_rough_width_in"] * IN
    rough_h = schema["door_rough_height_in"] * IN
    osb = schema["osb_thickness_in"] * IN

    osb_sheet_width = schema["osb_sheet_width_in"] * IN
    osb_sheet_height = schema["osb_sheet_height_in"] * IN

    if schema["door_left_in"] is None:
        rough_x = (module_width - rough_w) / 2
    else:
        rough_x = schema["door_left_in"] * IN

    rough_right = rough_x + rough_w

    left_king_x = 0
    right_king_x = module_width - t

    left_jack_x = rough_x - t
    right_jack_x = rough_right

    header_size = schema["header_lumber"]
    header_depth = LUMBER_SIZES[header_size] * IN
    header_ply_count = schema["header_ply_count"]

    top_plate_z = t + stud_height

    rough_opening_bottom_z = 0
    rough_opening_top_z = rough_h

    flat_header_z = rough_opening_top_z
    main_header_z = flat_header_z + t
    header_top_z = main_header_z + header_depth

    if header_top_z > top_plate_z:
        raise ValueError("Door opening plus header is too tall.")

    doc = App.newDocument("Parametric_Door_Module")

    def add_box(name, x, y, z, sx, sy, sz):
        obj = doc.addObject("Part::Box", name)
        obj.Length = sx
        obj.Width = sy
        obj.Height = sz
        obj.Placement.Base = App.Vector(ox + x, oy + y, oz + z)
        return obj

    def add_osb_with_cutout():
        panel = Part.makeBox(
            osb_sheet_width,
            osb,
            osb_sheet_height,
            App.Vector(ox, oy - osb, oz)
        )

        cutout = Part.makeBox(
            rough_w,
            osb * 3,
            rough_h,
            App.Vector(ox + rough_x, oy - 2 * osb, oz)
        )

        obj = doc.addObject("Part::Feature", "Exterior_4x8_OSB_With_Door_Cutout")
        obj.Shape = panel.cut(cutout)
        return obj

    # Full bottom plate, cut later after assembly
    add_box("Bottom_Plate", 0, 0, 0, module_width, wall_depth, t)

    # Top plate
    add_box("Top_Plate", 0, 0, top_plate_z, module_width, wall_depth, t)

    # King studs are first and last studs
    add_box("Left_King_Stud", left_king_x, 0, t, t, wall_depth, stud_height)
    add_box("Right_King_Stud", right_king_x, 0, t, t, wall_depth, stud_height)

    # Jack studs
    jack_height = flat_header_z - t

    add_box("Left_Jack_Stud", left_jack_x, 0, t, t, wall_depth, jack_height)
    add_box("Right_Jack_Stud", right_jack_x, 0, t, t, wall_depth, jack_height)

    # Header and flat nailer span BETWEEN king studs, not over them
    header_x = left_king_x + t
    header_width = right_king_x - header_x

    if schema.get("flat_header_nailer", True):
        add_box(
            "Flat_2x6_Header_Nailer",
            header_x,
            0,
            flat_header_z,
            header_width,
            wall_depth,
            t
        )

    for ply in range(header_ply_count):
        add_box(
            f"Header_{header_size}_Ply_{ply+1}",
            header_x,
            ply * t,
            main_header_z,
            header_width,
            t,
            header_depth
        )

    # Top cripple above opening
    top_cripple_height = top_plate_z - header_top_z

    if top_cripple_height > 0:
        cripple_num = 1
        center_x = spacing

        while center_x < module_width - 0.01:
            if rough_x <= center_x <= rough_right:
                add_box(
                    f"Top_Cripple_{cripple_num}",
                    center_x - t / 2,
                    0,
                    header_top_z,
                    t,
                    wall_depth,
                    top_cripple_height
                )
                cripple_num += 1

            center_x += spacing

    # 2x6 blocking on edge between king studs and jack studs, 25" OC
    if schema.get("blocking", True):
        blocking_spacing = schema.get("blocking_spacing_in", 25) * IN

        z = t + blocking_spacing
        block_num = 1

        while z < flat_header_z - t:
            left_gap_start = left_king_x + t
            left_gap = left_jack_x - left_gap_start

            if left_gap > 0:
                add_box(
                    f"Left_Blocking_{block_num}",
                    left_gap_start,
                    0,
                    z,
                    left_gap,
                    wall_depth,
                    t
                )

            right_gap_start = right_jack_x + t
            right_gap = right_king_x - right_gap_start

            if right_gap > 0:
                add_box(
                    f"Right_Blocking_{block_num}",
                    right_gap_start,
                    0,
                    z,
                    right_gap,
                    wall_depth,
                    t
                )

            z += blocking_spacing
            block_num += 1

    if schema.get("include_osb", True):
        add_osb_with_cutout()

    doc.recompute()

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.ActiveView.viewAxometric()
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    return doc

compile_door_module(door_module_schema)