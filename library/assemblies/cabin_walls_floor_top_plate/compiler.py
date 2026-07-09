import FreeCAD as App
import Part
import math

# =====================================================
# CABIN FLOOR + WALLS + SINGLE TOP PLATE ASSEMBLY
# Single-file FreeCAD script
# Includes: framed floor with top/bottom sheathing, standard wall module,
# window module, single-door module, single 2x6 top plate, and cabin assembly compiler.
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25,
}

# =====================================================
# CABIN ASSEMBLY SCHEMA — EDIT THIS SECTION
# =====================================================

# =====================================================
# GEOMETRY HELPERS
# =====================================================

def _placement(origin_in, rotation_deg):
    ox, oy, oz = origin_in
    return App.Placement(
        App.Vector(ox * IN, oy * IN, oz * IN),
        App.Rotation(App.Vector(0, 0, 1), rotation_deg),
    )


def add_box(doc, name, x, y, z, sx, sy, sz, base_placement=None):
    """Add a box using inches in local coordinates, optionally transformed by base_placement."""
    local = App.Placement(App.Vector(x * IN, y * IN, z * IN), App.Rotation())
    final = base_placement.multiply(local) if base_placement else local

    obj = doc.addObject("Part::Box", name)
    obj.Length = sx * IN
    obj.Width = sy * IN
    obj.Height = sz * IN
    obj.Placement = final
    return obj


def add_osb_with_rect_cutout(doc, name, panel_w, panel_h, osb_t, cut_x, cut_z, cut_w, cut_h, base_placement):
    """Exterior OSB panel on local negative Y, with rectangular cutout."""
    panel = Part.makeBox(panel_w * IN, osb_t * IN, panel_h * IN, App.Vector(0, -osb_t * IN, 0))
    cutout = Part.makeBox(cut_w * IN, osb_t * 3 * IN, cut_h * IN, App.Vector(cut_x * IN, -2 * osb_t * IN, cut_z * IN))
    shape = panel.cut(cutout)
    shape.Placement = base_placement
    obj = doc.addObject("Part::Feature", name)
    obj.Shape = shape
    return obj


# =====================================================
# FRAMED FLOOR COMPILER
# Local convention:
#   X = floor width, Y = floor depth, Z = height
#   Bottom OSB at Z=0
#   Framing sits on top of bottom OSB
#   Top OSB sits on top of framing
# =====================================================

def floor_total_height_in(floor_schema):
    joist_depth = LUMBER_SIZES[floor_schema["framing_lumber"]]
    return (
        floor_schema["bottom_osb_thickness_in"]
        + joist_depth
        + floor_schema["top_osb_thickness_in"]
    )


def _add_staggered_sheeting(doc, prefix, width, depth, z, thickness, sheet_w=48, sheet_l=96):
    """Add 4x8 sheathing sheets, staggered by half a sheet every other course.

    Sheets are represented as separate panels so layout is visible.
    Joists run front-to-back along Y, so the long 96 in sheet dimension runs
    left-to-right along X, perpendicular to the joists. Courses step in Y.
    Alternate courses are offset 48 in along X to stagger end joints.
    """
    course = 0
    y0 = 0
    while y0 < depth - 0.01:
        course_depth = min(sheet_w, depth - y0)

        x = -sheet_l / 2 if course % 2 else 0
        sheet_num = 1
        while x < width - 0.01:
            visible_x = max(0, x)
            visible_end = min(width, x + sheet_l)
            visible_l = visible_end - visible_x
            if visible_l > 0.01:
                add_box(
                    doc,
                    f"{prefix}_Course_{course + 1}_Sheet_{sheet_num}",
                    visible_x,
                    y0,
                    z,
                    visible_l,
                    course_depth,
                    thickness,
                )
            x += sheet_l
            sheet_num += 1

        y0 += sheet_w
        course += 1


def compile_framed_floor_into_doc(doc, schema):
    width = schema["width_in"]
    depth = schema["depth_in"]
    lumber = schema["framing_lumber"]
    joist_depth = LUMBER_SIZES[lumber]
    joist_spacing = schema["joist_spacing_in"]
    top_osb = schema["top_osb_thickness_in"]
    bottom_osb = schema["bottom_osb_thickness_in"]
    sheet_w = schema.get("sheet_width_in", 48)
    sheet_l = schema.get("sheet_length_in", 96)
    t = 1.5

    framing_z = bottom_osb
    top_osb_z = bottom_osb + joist_depth

    # Bottom sheathing: 3/4 in pressure-treated plywood, individual 4x8 sheets, staggered.
    _add_staggered_sheeting(
        doc,
        "Floor_Bottom_PT_Plywood",
        width,
        depth,
        0,
        bottom_osb,
        sheet_w,
        sheet_l,
    )

    # Double rim joists.
    # Front/back rims run full width. Inner rims sit immediately inside them.
    add_box(doc, "Floor_Front_Outer_Rim_Joist", 0, 0, framing_z, width, t, joist_depth)
    add_box(doc, "Floor_Front_Inner_Rim_Joist", 0, t, framing_z, width, t, joist_depth)
    add_box(doc, "Floor_Back_Outer_Rim_Joist", 0, depth - t, framing_z, width, t, joist_depth)
    add_box(doc, "Floor_Back_Inner_Rim_Joist", 0, depth - 2 * t, framing_z, width, t, joist_depth)

    # Left/right double rims run between the doubled front/back rims.
    side_y = 2 * t
    side_len = depth - 4 * t
    add_box(doc, "Floor_Left_Outer_Rim_Joist", 0, side_y, framing_z, t, side_len, joist_depth)
    add_box(doc, "Floor_Left_Inner_Rim_Joist", t, side_y, framing_z, t, side_len, joist_depth)
    add_box(doc, "Floor_Right_Outer_Rim_Joist", width - t, side_y, framing_z, t, side_len, joist_depth)
    add_box(doc, "Floor_Right_Inner_Rim_Joist", width - 2 * t, side_y, framing_z, t, side_len, joist_depth)

    # Interior joists run front-to-back, between the inner front/back rim joists.
    # The center of the first joist is 24 in from the left edge of the first/outer
    # left rim joist. Each subsequent joist is 24 in OC moving right.
    # No extra final joist is added at the right rim, so the rim remains doubled, not tripled.
    joist_num = 1
    center_x = joist_spacing
    right_inner_rim_left_x = width - 2 * t
    while center_x < right_inner_rim_left_x - 0.01:
        x = center_x - t / 2
        add_box(
            doc,
            f"Floor_Interior_Joist_{joist_num}",
            x,
            2 * t,
            framing_z,
            t,
            depth - 4 * t,
            joist_depth,
        )
        joist_num += 1
        center_x += joist_spacing

    # Top sheathing: 3/4 in OSB, individual 4x8 sheets, staggered.
    _add_staggered_sheeting(
        doc,
        "Floor_Top_OSB",
        width,
        depth,
        top_osb_z,
        top_osb,
        sheet_w,
        sheet_l,
    )

    return floor_total_height_in(schema)

# =====================================================
# STANDARD WALL MODULE COMPILER
# Local convention:
#   X = module width
#   Y = wall depth
#   Z = height
#   Exterior / OSB side = negative Y
# =====================================================

def compile_wall_module_into_doc(doc, schema, base_placement, prefix):
    module_width = schema["module_width_in"]
    stud_height = schema["stud_height_in"]
    spacing = schema["stud_spacing_in"]
    lumber = schema["lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5
    osb = schema["osb_thickness_in"]
    osb_sheet_height = schema.get("osb_sheet_height_in", 96)

    add_box(doc, prefix + "_Bottom_Plate", 0, 0, 0, module_width, wall_depth, t, base_placement)
    add_box(doc, prefix + "_Top_Plate", 0, 0, t + stud_height, module_width, wall_depth, t, base_placement)

    center_x = t / 2
    stud_num = 1
    last_center = None
    while center_x <= module_width - t / 2 + 0.01:
        add_box(doc, f"{prefix}_Stud_{stud_num}", center_x - t / 2, 0, t, t, wall_depth, stud_height, base_placement)
        last_center = center_x
        center_x += spacing
        stud_num += 1

    right_end_center = module_width - t / 2
    if last_center is None or abs(last_center - right_end_center) > 0.01:
        add_box(doc, prefix + "_Right_End_Stud", module_width - t, 0, t, t, wall_depth, stud_height, base_placement)

    def add_left_corner_reinforcement():
        u_depth = 5.5
        u_t = 1.5
        add_box(doc, prefix + "_Left_Corner_U_Left_Leg", 0, 0, t, u_t, u_depth, stud_height, base_placement)
        add_box(doc, prefix + "_Left_Corner_U_Back", u_t, u_depth - u_t, t, u_depth, u_t, stud_height, base_placement)
        add_box(doc, prefix + "_Left_Corner_U_Right_Leg", u_depth + u_t, 0, t, u_t, u_depth, stud_height, base_placement)

    def add_right_corner_reinforcement():
        u_depth = 5.5
        u_t = 1.5
        add_box(doc, prefix + "_Right_Corner_U_Right_Leg", module_width - u_t, 0, t, u_t, u_depth, stud_height, base_placement)
        add_box(doc, prefix + "_Right_Corner_U_Back", module_width - u_t - u_depth, u_depth - u_t, t, u_depth, u_t, stud_height, base_placement)
        add_box(doc, prefix + "_Right_Corner_U_Left_Leg", module_width - u_depth - 2 * u_t, 0, t, u_t, u_depth, stud_height, base_placement)

    if schema.get("left_corner_reinforcement", False):
        add_left_corner_reinforcement()
    if schema.get("right_corner_reinforcement", False):
        add_right_corner_reinforcement()

    if schema.get("include_osb", True):
        add_box(doc, prefix + "_Exterior_1_2in_OSB", 0, -osb, 0, module_width, osb, osb_sheet_height, base_placement)

# =====================================================
# WINDOW MODULE COMPILER
# =====================================================

def select_window_header_size(schema):
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


def compile_window_module_into_doc(doc, schema, base_placement, prefix):
    module_width = schema["module_width_in"]
    stud_height = schema["stud_height_in"]
    spacing = schema["stud_spacing_in"]
    lumber = schema["lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5

    rough_w = schema["window_rough_width_in"]
    rough_h = schema["window_rough_height_in"]
    sill_h = schema["window_sill_height_in"]
    osb = schema["osb_thickness_in"]
    osb_sheet_width = schema.get("osb_sheet_width_in", 48)
    osb_sheet_height = schema.get("osb_sheet_height_in", 96)

    rough_x = (module_width - rough_w) / 2 if schema.get("window_left_in") is None else schema["window_left_in"]
    rough_right = rough_x + rough_w

    header_size, jack_count = select_window_header_size(schema)
    header_depth = LUMBER_SIZES[header_size]
    header_ply_count = schema.get("header_ply_count", 2)

    top_plate_z = t + stud_height
    sill_top_z = t + sill_h
    sill_bottom_z = sill_top_z - t
    rough_opening_top_z = sill_top_z + rough_h

    flat_nailer_height = t if schema.get("flat_header_nailer", True) else 0
    flat_header_z = rough_opening_top_z
    main_header_z = flat_header_z + flat_nailer_height
    header_top_z = main_header_z + header_depth

    if header_top_z > top_plate_z:
        raise ValueError(prefix + ": Window opening plus header is too tall for this wall module.")

    add_box(doc, prefix + "_Bottom_Plate", 0, 0, 0, module_width, wall_depth, t, base_placement)
    add_box(doc, prefix + "_Top_Plate", 0, 0, top_plate_z, module_width, wall_depth, t, base_placement)
    add_box(doc, prefix + "_Left_End_Stud", 0, 0, t, t, wall_depth, stud_height, base_placement)
    add_box(doc, prefix + "_Right_End_Stud", module_width - t, 0, t, t, wall_depth, stud_height, base_placement)

    left_jack_x = rough_x - t
    right_jack_x = rough_right
    left_king_x = left_jack_x - t
    right_king_x = right_jack_x + t

    add_box(doc, prefix + "_Left_King_Stud", left_king_x, 0, t, t, wall_depth, stud_height, base_placement)
    add_box(doc, prefix + "_Right_King_Stud", right_king_x, 0, t, t, wall_depth, stud_height, base_placement)

    jack_height = flat_header_z - t
    for i in range(jack_count):
        add_box(doc, f"{prefix}_Left_Jack_Stud_{i+1}", left_jack_x - i * t, 0, t, t, wall_depth, jack_height, base_placement)
        add_box(doc, f"{prefix}_Right_Jack_Stud_{i+1}", right_jack_x + i * t, 0, t, t, wall_depth, jack_height, base_placement)

    add_box(doc, prefix + "_Window_Sill", rough_x, 0, sill_bottom_z, rough_w, wall_depth, t, base_placement)

    header_x = left_jack_x
    header_width = rough_w + 2 * t

    if schema.get("flat_header_nailer", True):
        add_box(doc, prefix + "_Flat_2x6_Header_Nailer", header_x, 0, flat_header_z, header_width, wall_depth, t, base_placement)

    for ply in range(header_ply_count):
        add_box(doc, f"{prefix}_Header_{header_size}_Ply_{ply+1}", header_x, ply * t, main_header_z, header_width, t, header_depth, base_placement)

    cripple_num = 1
    center_x = spacing
    while center_x < module_width - 0.01:
        if rough_x <= center_x <= rough_right:
            add_box(doc, f"{prefix}_Bottom_Cripple_{cripple_num}", center_x - t / 2, 0, t, t, wall_depth, sill_bottom_z - t, base_placement)
            cripple_num += 1
        center_x += spacing

    top_cripple_height = top_plate_z - header_top_z
    if top_cripple_height > 0:
        cripple_num = 1
        center_x = spacing
        while center_x < module_width - 0.01:
            if rough_x <= center_x <= rough_right:
                add_box(doc, f"{prefix}_Top_Cripple_{cripple_num}", center_x - t / 2, 0, header_top_z, t, wall_depth, top_cripple_height, base_placement)
                cripple_num += 1
            center_x += spacing

    stud_num = 1
    center_x = t / 2
    protected_left = left_king_x
    protected_right = right_king_x + t
    while center_x <= module_width - t / 2 + 0.01:
        x = center_x - t / 2
        overlaps_window_framing = not (x + t <= protected_left or x >= protected_right)
        is_end = abs(x) < 0.01 or abs(x - (module_width - t)) < 0.01
        if not overlaps_window_framing and not is_end:
            add_box(doc, f"{prefix}_Full_Stud_Outside_Window_{stud_num}", x, 0, t, t, wall_depth, stud_height, base_placement)
            stud_num += 1
        center_x += spacing

    if schema.get("blocking", True):
        blocking_spacing = schema.get("blocking_spacing_in", 24)
        z = t + blocking_spacing
        block_num = 1
        while z < top_plate_z - t:
            left_gap = left_king_x - t
            if left_gap > 0:
                add_box(doc, f"{prefix}_Left_Blocking_{block_num}", t, 0, z, left_gap, wall_depth, t, base_placement)
            right_gap_start = right_king_x + t
            right_gap = module_width - t - right_gap_start
            if right_gap > 0:
                add_box(doc, f"{prefix}_Right_Blocking_{block_num}", right_gap_start, 0, z, right_gap, wall_depth, t, base_placement)
            z += blocking_spacing
            block_num += 1

    if schema.get("include_osb", True):
        add_osb_with_rect_cutout(
            doc,
            prefix + "_Exterior_4x8_OSB_With_Window_Cutout",
            osb_sheet_width,
            osb_sheet_height,
            osb,
            rough_x,
            sill_top_z,
            rough_w,
            rough_h,
            base_placement,
        )

# =====================================================
# SINGLE DOOR MODULE COMPILER
# =====================================================

def compile_door_module_into_doc(doc, schema, base_placement, prefix):
    module_width = schema["module_width_in"]
    stud_height = schema["stud_height_in"]
    spacing = schema["stud_spacing_in"]
    lumber = schema["lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5

    rough_w = schema["door_rough_width_in"]
    rough_h = schema["door_rough_height_in"]
    osb = schema["osb_thickness_in"]
    osb_sheet_width = schema.get("osb_sheet_width_in", 48)
    osb_sheet_height = schema.get("osb_sheet_height_in", 96)

    rough_x = (module_width - rough_w) / 2 if schema.get("door_left_in") is None else schema["door_left_in"]
    rough_right = rough_x + rough_w

    left_king_x = 0
    right_king_x = module_width - t
    left_jack_x = rough_x - t
    right_jack_x = rough_right

    header_size = schema.get("header_lumber", "2x8")
    header_depth = LUMBER_SIZES[header_size]
    header_ply_count = schema.get("header_ply_count", 2)

    top_plate_z = t + stud_height
    rough_opening_bottom_z = 0
    rough_opening_top_z = rough_h
    flat_header_z = rough_opening_top_z
    main_header_z = flat_header_z + t
    header_top_z = main_header_z + header_depth

    if header_top_z > top_plate_z:
        raise ValueError(prefix + ": Door opening plus header is too tall.")

    add_box(doc, prefix + "_Bottom_Plate", 0, 0, 0, module_width, wall_depth, t, base_placement)
    add_box(doc, prefix + "_Top_Plate", 0, 0, top_plate_z, module_width, wall_depth, t, base_placement)
    add_box(doc, prefix + "_Left_King_Stud", left_king_x, 0, t, t, wall_depth, stud_height, base_placement)
    add_box(doc, prefix + "_Right_King_Stud", right_king_x, 0, t, t, wall_depth, stud_height, base_placement)

    jack_height = flat_header_z - t
    add_box(doc, prefix + "_Left_Jack_Stud", left_jack_x, 0, t, t, wall_depth, jack_height, base_placement)
    add_box(doc, prefix + "_Right_Jack_Stud", right_jack_x, 0, t, t, wall_depth, jack_height, base_placement)

    # Header and flat nailer span BETWEEN king studs, not over them.
    header_x = left_king_x + t
    header_width = right_king_x - header_x

    if schema.get("flat_header_nailer", True):
        add_box(doc, prefix + "_Flat_2x6_Header_Nailer", header_x, 0, flat_header_z, header_width, wall_depth, t, base_placement)

    for ply in range(header_ply_count):
        add_box(doc, f"{prefix}_Header_{header_size}_Ply_{ply+1}", header_x, ply * t, main_header_z, header_width, t, header_depth, base_placement)

    top_cripple_height = top_plate_z - header_top_z
    if top_cripple_height > 0:
        cripple_num = 1
        center_x = spacing
        while center_x < module_width - 0.01:
            if rough_x <= center_x <= rough_right:
                add_box(doc, f"{prefix}_Top_Cripple_{cripple_num}", center_x - t / 2, 0, header_top_z, t, wall_depth, top_cripple_height, base_placement)
                cripple_num += 1
            center_x += spacing

    if schema.get("blocking", True):
        blocking_spacing = schema.get("blocking_spacing_in", 25)
        z = t + blocking_spacing
        block_num = 1
        while z < flat_header_z - t:
            left_gap_start = left_king_x + t
            left_gap = left_jack_x - left_gap_start
            if left_gap > 0:
                add_box(doc, f"{prefix}_Left_Blocking_{block_num}", left_gap_start, 0, z, left_gap, wall_depth, t, base_placement)

            right_gap_start = right_jack_x + t
            right_gap = right_king_x - right_gap_start
            if right_gap > 0:
                add_box(doc, f"{prefix}_Right_Blocking_{block_num}", right_gap_start, 0, z, right_gap, wall_depth, t, base_placement)

            z += blocking_spacing
            block_num += 1

    if schema.get("include_osb", True):
        add_osb_with_rect_cutout(
            doc,
            prefix + "_Exterior_4x8_OSB_With_Door_Cutout",
            osb_sheet_width,
            osb_sheet_height,
            osb,
            rough_x,
            rough_opening_bottom_z,
            rough_w,
            rough_h,
            base_placement,
        )


# =====================================================
# SINGLE TOP PLATE COMPILER
# World convention:
#   X = left/right, Y = front/back, Z = up
#   Top plate is a 2x6 laid flat, 5.5 in wide x 1.5 in tall.
#   Boards are shown as separate pieces, with names indicating stock/cut lengths.
# =====================================================

def wall_module_total_height_in(common_wall_schema):
    t = 1.5
    return common_wall_schema["stud_height_in"] + 2 * t


def _choose_top_plate_segments(total_length, module_width, min_seam_distance, preferred_stock_lengths):
    """Return cut segments for a top plate.

    For the current 155 in and 144 in walls, this returns a single segment,
    which automatically satisfies the seam rule. If a future wall is longer
    than available stock, seams are placed away from 48 in module edges by
    at least min_seam_distance.
    """
    preferred = sorted(preferred_stock_lengths, reverse=True)

    for stock in preferred:
        if stock >= total_length:
            return [(0, total_length, stock)]

    segments = []
    start = 0
    remaining = total_length

    while remaining > 0.01:
        chosen_stock = None
        chosen_cut = None

        for stock in preferred:
            cut = min(stock, remaining)
            end = start + cut

            if abs(total_length - end) < 0.01:
                chosen_stock = stock
                chosen_cut = cut
                break

            module_index = round(end / module_width)
            nearest_module_edge = module_index * module_width
            if abs(end - nearest_module_edge) >= min_seam_distance - 0.01:
                chosen_stock = stock
                chosen_cut = cut
                break

        if chosen_stock is None:
            # Fallback: place seam halfway between module edges.
            chosen_stock = preferred[0]
            tentative = min(chosen_stock, remaining)
            end = start + tentative
            module_index = math.floor(end / module_width)
            target_end = module_index * module_width + module_width / 2
            if target_end <= start + 1 or target_end >= total_length:
                target_end = min(start + tentative, total_length)
            chosen_cut = target_end - start

        segments.append((start, chosen_cut, chosen_stock))
        start += chosen_cut
        remaining = total_length - start

    return segments


def compile_single_top_plate_into_doc(doc, schema):
    top_plate = schema.get("single_top_plate", {})
    if not top_plate.get("include", False):
        return

    floor = schema["floor"]
    common = schema["common_wall"]

    cabin_w = floor["width_in"]
    cabin_d = floor["depth_in"]
    wall_depth = LUMBER_SIZES[top_plate.get("lumber", "2x6")]
    plate_thickness = top_plate.get("thickness_in", 1.5)
    module_w = common["module_width_in"]
    min_seam = top_plate.get("min_seam_distance_from_module_edge_in", 24)
    stock = top_plate.get("preferred_stock_lengths_in", [240, 192, 168, 144, 120, 96])

    z = floor_total_height_in(floor) + wall_module_total_height_in(common)

    # Front and back plates: run full cabin width so they intersect the side walls.
    for side_name, y in [("Front", 0), ("Back", cabin_d - wall_depth)]:
        segments = _choose_top_plate_segments(cabin_w, module_w, min_seam, stock)
        for idx, (x, cut_len, stock_len) in enumerate(segments, start=1):
            add_box(
                doc,
                f"Single_Top_Plate_{side_name}_{idx}_cut_{cut_len:g}_from_{stock_len:g}",
                x,
                y,
                z,
                cut_len,
                wall_depth,
                plate_thickness,
            )

    # Left and right plates: fit BETWEEN the front/back plates.
    # This lets the top plate assembly intersect perpendicular walls without
    # overlapping itself at the corners. For this cabin: 144 - 5.5 - 5.5 = 133 in.
    side_plate_y_start = wall_depth
    side_plate_length = cabin_d - 2 * wall_depth

    for side_name, x in [("Left", 0), ("Right", cabin_w - wall_depth)]:
        segments = _choose_top_plate_segments(side_plate_length, module_w, min_seam, stock)
        for idx, (local_y, cut_len, stock_len) in enumerate(segments, start=1):
            y = side_plate_y_start + local_y
            add_box(
                doc,
                f"Single_Top_Plate_{side_name}_{idx}_cut_{cut_len:g}_from_{stock_len:g}",
                x,
                y,
                z,
                wall_depth,
                cut_len,
                plate_thickness,
            )

# =====================================================
# CABIN ASSEMBLY COMPILER
# =====================================================

def module_placement_for_wall(schema, wall, module_index):
    floor = schema["floor"]
    width = floor["width_in"]
    depth = floor["depth_in"]
    floor_t = floor_total_height_in(floor)
    module_w = schema["common_wall"]["module_width_in"]

    side = wall["side"]

    if side == "front":
        # runs left to right; exterior OSB faces negative Y
        x = wall.get("start_offset_in", 0) + module_index * module_w
        return _placement((x, 0, floor_t), 0)

    if side == "back":
        # runs left to right, but module is rotated 180 so exterior OSB faces positive Y.
        # To keep module order left-to-right, each module's local origin is its right edge.
        x = wall.get("start_offset_in", 0) + (module_index + 1) * module_w
        return _placement((x, depth, floor_t), 180)

    if side == "right":
        # runs front to back; exterior OSB faces positive X
        y = module_index * module_w
        return _placement((width, y, floor_t), 90)

    if side == "left":
        # runs front to back, but module is rotated -90 so exterior OSB faces negative X.
        # To keep module order front-to-back, each module's local origin is its back edge.
        y = (module_index + 1) * module_w
        return _placement((0, y, floor_t), -90)

    raise ValueError("Unknown wall side: " + side)


def compile(schema, doc):

    floor_w = schema["floor"]["width_in"]
    floor_d = schema["floor"]["depth_in"]
    floor_t = compile_framed_floor_into_doc(doc, schema["floor"])

    common = schema["common_wall"]

    for wall in schema["walls"]:
        for i, module in enumerate(wall["modules"]):
            module_schema = dict(common)
            module_schema.update(module)

            prefix = f"{wall['name']}_Module_{i+1}_{module['type'].capitalize()}"
            placement = module_placement_for_wall(schema, wall, i)

            if module["type"] == "standard":
                compile_wall_module_into_doc(doc, module_schema, placement, prefix)
            elif module["type"] == "window":
                module_schema.setdefault("building_width_in", 144)
                module_schema.setdefault("clear_span_floors_above", 0)
                module_schema.setdefault("header_ply_count", 2)
                module_schema.setdefault("flat_header_nailer", True)
                module_schema.setdefault("blocking", True)
                module_schema.setdefault("blocking_spacing_in", 24)
                compile_window_module_into_doc(doc, module_schema, placement, prefix)
            elif module["type"] == "door":
                module_schema.setdefault("header_lumber", "2x8")
                module_schema.setdefault("header_ply_count", 2)
                module_schema.setdefault("flat_header_nailer", True)
                module_schema.setdefault("blocking", True)
                module_schema.setdefault("blocking_spacing_in", 25)
                compile_door_module_into_doc(doc, module_schema, placement, prefix)
            else:
                raise ValueError("Unknown module type: " + module["type"])

    compile_single_top_plate_into_doc(doc, schema)

    doc.recompute()


    return list(doc.Objects)
