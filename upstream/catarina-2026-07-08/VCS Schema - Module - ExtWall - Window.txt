import FreeCAD as App
import Part

# =====================================================
# WINDOW MODULE SCHEMA — EDIT THIS SECTION
# =====================================================

window_module_schema = {
    "module_width_in": 48,
    "stud_height_in": 92.625,
    "stud_spacing_in": 24,

    # Options: "2x4", "2x6", "2x8"
    "lumber": "2x6",

    "window_rough_width_in": 24,
    "window_rough_height_in": 36,
    "window_sill_height_in": 36,
    "window_left_in": None,

    "building_width_ft": 12,
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

# =====================================================
# WINDOW MODULE COMPILER
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25
}

def select_header_size(schema):
    opening = schema["window_rough_width_in"]
    floors = schema.get("clear_span_floors_above", 0)

    if floors <= 0:
        if opening <= 36:
            return "2x6", 1
        elif opening <= 48:
            return "2x8", 1
        else:
            return "2x10", 1

    elif floors == 1:
        if opening <= 36:
            return "2x8", 1
        elif opening <= 60:
            return "2x10", 1
        else:
            return "2x12", 2

    else:
        if opening <= 24:
            return "2x8", 1
        elif opening <= 48:
            return "2x10", 1
        elif opening <= 72:
            return "2x12", 2
        else:
            raise ValueError("Opening too large for this simple header selector.")

def compile_window_module(schema):
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

    rough_w = schema["window_rough_width_in"] * IN
    rough_h = schema["window_rough_height_in"] * IN
    sill_h = schema["window_sill_height_in"] * IN
    osb = schema["osb_thickness_in"] * IN

    osb_sheet_width = schema.get("osb_sheet_width_in", 48) * IN
    osb_sheet_height = schema.get("osb_sheet_height_in", 96) * IN

    if schema["window_left_in"] is None:
        rough_x = (module_width - rough_w) / 2
    else:
        rough_x = schema["window_left_in"] * IN

    rough_right = rough_x + rough_w

    header_size, jack_count = select_header_size(schema)
    header_depth = LUMBER_SIZES[header_size] * IN
    header_ply_count = schema.get("header_ply_count", 2)

    total_frame_height = stud_height + 2 * t
    top_plate_z = t + stud_height

    sill_top_z = t + sill_h
    sill_bottom_z = sill_top_z - t

    rough_opening_top_z = sill_top_z + rough_h

    flat_nailer_height = t if schema.get("flat_header_nailer", True) else 0
    flat_header_z = rough_opening_top_z
    main_header_z = flat_header_z + flat_nailer_height
    header_top_z = main_header_z + header_depth

    if header_top_z > top_plate_z:
        raise ValueError("Window opening plus header is too tall for this wall module.")

    doc = App.newDocument("Parametric_Window_Module")

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
            App.Vector(ox + rough_x, oy - 2 * osb, oz + sill_top_z)
        )

        obj = doc.addObject("Part::Feature", "Exterior_4x8_OSB_With_Window_Cutout")
        obj.Shape = panel.cut(cutout)
        return obj

    # Plates
    add_box("Bottom_Plate", 0, 0, 0, module_width, wall_depth, t)
    add_box("Top_Plate", 0, 0, top_plate_z, module_width, wall_depth, t)

    # End studs
    add_box("Left_End_Stud", 0, 0, t, t, wall_depth, stud_height)
    add_box("Right_End_Stud", module_width - t, 0, t, t, wall_depth, stud_height)

    # Jack and king stud positions
    left_jack_x = rough_x - t
    right_jack_x = rough_right

    left_king_x = left_jack_x - t
    right_king_x = right_jack_x + t

    add_box("Left_King_Stud", left_king_x, 0, t, t, wall_depth, stud_height)
    add_box("Right_King_Stud", right_king_x, 0, t, t, wall_depth, stud_height)

    # Jack studs
    jack_height = flat_header_z - t

    for i in range(jack_count):
        add_box(
            f"Left_Jack_Stud_{i+1}",
            left_jack_x - i * t,
            0,
            t,
            t,
            wall_depth,
            jack_height
        )

        add_box(
            f"Right_Jack_Stud_{i+1}",
            right_jack_x + i * t,
            0,
            t,
            t,
            wall_depth,
            jack_height
        )

    # Sill spans between jack studs
    add_box(
        "Window_Sill",
        rough_x,
        0,
        sill_bottom_z,
        rough_w,
        wall_depth,
        t
    )

    # Header assembly
    header_x = left_jack_x
    header_width = rough_w + 2 * t

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

    # Bottom cripples under sill
    cripple_num = 1
    center_x = spacing

    while center_x < module_width - 0.01:
        if rough_x <= center_x <= rough_right:
            add_box(
                f"Bottom_Cripple_{cripple_num}",
                center_x - t / 2,
                0,
                t,
                t,
                wall_depth,
                sill_bottom_z - t
            )
            cripple_num += 1

        center_x += spacing

    # Top cripples above header
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

    # Full-height studs outside window assembly
    stud_num = 1
    center_x = t / 2

    protected_left = left_king_x
    protected_right = right_king_x + t

    while center_x <= module_width - t / 2 + 0.01:
        x = center_x - t / 2

        overlaps_window_framing = not (
            x + t <= protected_left or x >= protected_right
        )

        is_end = abs(x) < 0.01 or abs(x - (module_width - t)) < 0.01

        if not overlaps_window_framing and not is_end:
            add_box(
                f"Full_Stud_Outside_Window_{stud_num}",
                x,
                0,
                t,
                t,
                wall_depth,
                stud_height
            )
            stud_num += 1

        center_x += spacing

    # 2x6 blocking, 1-1/2" high x wall-depth deep
    if schema.get("blocking", True):
        blocking_spacing = schema.get("blocking_spacing_in", 24) * IN

        z = t + blocking_spacing
        block_num = 1

        while z < top_plate_z - t:
            left_gap = left_king_x - t
            if left_gap > 0:
                add_box(
                    f"Left_Blocking_{block_num}",
                    t,
                    0,
                    z,
                    left_gap,
                    wall_depth,
                    t
                )

            right_gap_start = right_king_x + t
            right_gap = module_width - t - right_gap_start
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

    print("Selected header:", header_ply_count, "adjacent", header_size, "plies")
    print("Jack studs per side:", jack_count)

    return doc

compile_window_module(window_module_schema)