import FreeCAD as App
import Part

# =====================================================
# RAKE WALL ASSEMBLY SCHEMA
# Modular architecture, compiler included in this file.
#
# Includes:
#   - Front wall: corner + 3 standard wall modules + corner, 12" high
#   - Back wall:  corner + 3 standard wall modules + corner, 45.25" high
#   - Left/right side rake walls sandwiched between front/back walls
#       * 3 side rake modules per side
#       * from front to back: 37", 48", 48"
#       * total side clear span = 133"
#   - Whole assembly elevation is parametric via assembly_base_z_in
# =====================================================

# =====================================================
# CONSTANTS / LUMBER
# =====================================================

IN = 25.4

# Actual lumber depths, in inches.
LUMBER_SIZES = {
    "2x3": 2.5,
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25,
}

NOMINAL_THICKNESS_IN = 1.5


# =====================================================
# BASIC HELPERS
# =====================================================

def inch(value):
    return value * IN


def add_box(doc, name, x, y, z, sx, sy, sz):
    obj = doc.addObject("Part::Box", name)
    obj.Length = sx
    obj.Width = sy
    obj.Height = sz
    obj.Placement.Base = App.Vector(x, y, z)
    return obj


def add_prism(doc, name, points):
    """
    Build a closed solid from 8 points.

    Points:
      0 bottom-front-left
      1 bottom-front-right
      2 bottom-back-right
      3 bottom-back-left
      4 top-front-left
      5 top-front-right
      6 top-back-right
      7 top-back-left
    """
    verts = [App.Vector(*p) for p in points]

    faces_idx = [
        [0, 1, 2, 3],
        [4, 7, 6, 5],
        [0, 4, 5, 1],
        [1, 5, 6, 2],
        [2, 6, 7, 3],
        [3, 7, 4, 0],
    ]

    faces = []
    for idxs in faces_idx:
        poly = Part.makePolygon([verts[i] for i in idxs] + [verts[idxs[0]]])
        faces.append(Part.Face(poly))

    shell = Part.makeShell(faces)
    solid = Part.makeSolid(shell)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = solid
    return obj


def add_sloped_member_y(doc, name, x, y, z_bottom, sx, sy, top_front_z, top_back_z):
    """
    Member with flat bottom and top sloping along global Y.
    Used for side-rake studs and OSB.
    """
    pts = [
        (x,      y,      z_bottom),
        (x+sx,   y,      z_bottom),
        (x+sx,   y+sy,   z_bottom),
        (x,      y+sy,   z_bottom),
        (x,      y,      top_front_z),
        (x+sx,   y,      top_front_z),
        (x+sx,   y+sy,   top_back_z),
        (x,      y+sy,   top_back_z),
    ]
    return add_prism(doc, name, pts)


def add_sloped_plate_y(doc, name, x, y, sx, sy, bottom_front_z, bottom_back_z, thickness):
    """
    Constant-thickness sloped plate.
    Both bottom and top faces follow the same front-to-back slope.
    """
    pts = [
        (x,      y,      bottom_front_z),
        (x+sx,   y,      bottom_front_z),
        (x+sx,   y+sy,   bottom_back_z),
        (x,      y+sy,   bottom_back_z),
        (x,      y,      bottom_front_z + thickness),
        (x+sx,   y,      bottom_front_z + thickness),
        (x+sx,   y+sy,   bottom_back_z + thickness),
        (x,      y+sy,   bottom_back_z + thickness),
    ]
    return add_prism(doc, name, pts)


# =====================================================
# VALIDATION / HEIGHT FUNCTION
# =====================================================

def wall_depth_in(schema):
    return LUMBER_SIZES[schema["wall_lumber"]]


def overall_depth_in(schema):
    wd = wall_depth_in(schema)
    return wd + schema["clear_span_between_front_back_walls_in"] + wd


def height_front_to_back(y_in, schema):
    """
    Global height profile at a given assembly Y coordinate.

    The front wall occupies y = 0 to wall_depth.
    The back wall occupies y = wall_depth + clear_span to overall_depth.

    The side rake walls are sandwiched between those two walls, so their
    slope is calculated from the interior face of the front wall to the
    interior face of the back wall.
    """
    wd = wall_depth_in(schema)
    clear_span = schema["clear_span_between_front_back_walls_in"]
    y_front_inner = wd
    y_back_inner = wd + clear_span

    front_h = schema["front_wall_height_in"]
    back_h = schema["back_wall_height_in"]

    if clear_span == 0:
        return front_h

    # Clamp outside the side-wall span so front/back wall pieces remain stable.
    if y_in <= y_front_inner:
        return front_h
    if y_in >= y_back_inner:
        return back_h

    return front_h + (back_h - front_h) * ((y_in - y_front_inner) / clear_span)


def validate_schema(schema):
    wall_lumber = schema["wall_lumber"]
    if wall_lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported wall_lumber: " + wall_lumber)

    for key in ["corner_long_lumber", "corner_short_lumber"]:
        if schema[key] not in LUMBER_SIZES:
            raise ValueError("Unsupported " + key + ": " + schema[key])

    wd = wall_depth_in(schema)
    corner_w = schema["corner_module_width_in"]
    standard_w = schema["standard_module_width_in"]
    n = schema["standard_modules_per_wall"]
    expected_width = 2 * corner_w + n * standard_w

    if abs(expected_width - schema["building_width_in"]) > 0.001:
        raise ValueError(
            "Module layout width does not equal building_width_in: "
            + str(expected_width) + " != " + str(schema["building_width_in"])
        )

    if abs(corner_w - wd) > 0.001:
        raise ValueError(
            "corner_module_width_in should match wall depth for this square corner module."
        )

    side_total = sum(schema["side_rake_module_lengths_front_to_back_in"])
    if abs(side_total - schema["clear_span_between_front_back_walls_in"]) > 0.001:
        raise ValueError(
            "Side rake module lengths must add up to clear_span_between_front_back_walls_in: "
            + str(side_total) + " != " + str(schema["clear_span_between_front_back_walls_in"])
        )

    min_height = 2 * NOMINAL_THICKNESS_IN
    if schema["front_wall_height_in"] <= min_height:
        raise ValueError("front_wall_height_in is too short for top and bottom plates.")
    if schema["back_wall_height_in"] <= min_height:
        raise ValueError("back_wall_height_in is too short for top and bottom plates.")


# =====================================================
# FRONT/BACK MODULE COMPILERS
# =====================================================

def compile_corner_module(doc, schema, module_name, x0_in, y0_in, height_in, exterior_side):
    """
    Small square corner module made from:
      - two 2x6 full-depth side members,
      - two 2x3 members between them,
      - optional 1/2" exterior OSB on the outside face.

    Framed footprint is 5.5" x 5.5".
    """
    t = NOMINAL_THICKNESS_IN
    long_depth = LUMBER_SIZES[schema["corner_long_lumber"]]
    short_depth = LUMBER_SIZES[schema["corner_short_lumber"]]
    module_w = schema["corner_module_width_in"]
    wd = wall_depth_in(schema)
    osb_t = schema.get("osb_thickness_in", 0.5)

    if abs(module_w - long_depth) > 0.001:
        raise ValueError("Corner module width must match the actual width of the 2x6 side, usually 5.5 in.")

    required_between_2x6s = module_w - 2 * t
    if abs(required_between_2x6s - short_depth) > 0.001:
        raise ValueError(
            "Corner short lumber must fit between the two 2x6 sides. "
            "For a 5.5 in square: 5.5 - 1.5 - 1.5 = 2.5 in, matching a 2x3."
        )

    add_box(doc, f"{module_name}_Left_Side_2x6_Full_Depth",
            inch(x0_in), inch(y0_in), 0,
            inch(t), inch(wd), inch(height_in))

    add_box(doc, f"{module_name}_Right_Side_2x6_Full_Depth",
            inch(x0_in + module_w - t), inch(y0_in), 0,
            inch(t), inch(wd), inch(height_in))

    add_box(doc, f"{module_name}_Front_2x3_Between_2x6s",
            inch(x0_in + t), inch(y0_in), 0,
            inch(short_depth), inch(t), inch(height_in))

    add_box(doc, f"{module_name}_Back_2x3_Between_2x6s",
            inch(x0_in + t), inch(y0_in + wd - t), 0,
            inch(short_depth), inch(t), inch(height_in))

    if schema.get("include_osb", True):
        if exterior_side == "front":
            osb_y = y0_in - osb_t
        elif exterior_side == "back":
            osb_y = y0_in + wd
        else:
            raise ValueError('exterior_side must be "front" or "back" for front/back wall corner modules')

        add_box(doc, f"{module_name}_Exterior_OSB",
                inch(x0_in), inch(osb_y), 0,
                inch(module_w), inch(osb_t), inch(height_in))


def compile_standard_wall_module(doc, schema, module_name, x0_in, y0_in, height_in, exterior_side):
    """
    Standard flat wall module, 48" wide by 5.5" deep.
    """
    module_w = schema["standard_module_width_in"]
    wd = wall_depth_in(schema)
    t = NOMINAL_THICKNESS_IN
    osb_t = schema["osb_thickness_in"]

    if schema.get("bottom_plate", True):
        add_box(doc, f"{module_name}_Bottom_Plate",
                inch(x0_in), inch(y0_in), 0,
                inch(module_w), inch(wd), inch(t))

    stud_positions = [
        (0, "Left_End_Stud"),
        (schema["stud_spacing_in"] - t / 2, "Interior_Stud_1_24oc"),
        (module_w - t, "Right_End_Stud"),
    ]

    stud_bottom_z = t
    stud_height = height_in - 2 * t

    for sx_in, label in stud_positions:
        add_box(doc, f"{module_name}_{label}",
                inch(x0_in + sx_in), inch(y0_in), inch(stud_bottom_z),
                inch(t), inch(wd), inch(stud_height))

    if schema.get("top_plate", True):
        add_box(doc, f"{module_name}_Top_Plate",
                inch(x0_in), inch(y0_in), inch(height_in - t),
                inch(module_w), inch(wd), inch(t))

    if schema.get("include_osb", True):
        if exterior_side == "front":
            osb_y = y0_in - osb_t
        elif exterior_side == "back":
            osb_y = y0_in + wd
        else:
            raise ValueError('exterior_side must be "front" or "back"')

        add_box(doc, f"{module_name}_Exterior_OSB",
                inch(x0_in), inch(osb_y), 0,
                inch(module_w), inch(osb_t), inch(height_in))


def compile_front_or_back_wall(doc, schema, wall_name, y0_in, height_in, exterior_side):
    """
    Places modules left-to-right:
      1) corner module
      2) standard module
      3) standard module
      4) standard module
      5) corner module
    """
    corner_w = schema["corner_module_width_in"]
    standard_w = schema["standard_module_width_in"]
    n_standard = schema["standard_modules_per_wall"]

    x = 0

    compile_corner_module(doc, schema, f"{wall_name}_Left_Corner_Module", x, y0_in, height_in, exterior_side)
    x += corner_w

    for i in range(n_standard):
        compile_standard_wall_module(doc, schema, f"{wall_name}_M{i+1}_Standard_Wall_Module", x, y0_in, height_in, exterior_side)
        x += standard_w

    compile_corner_module(doc, schema, f"{wall_name}_Right_Corner_Module", x, y0_in, height_in, exterior_side)


# =====================================================
# SIDE RAKE MODULE COMPILERS
# =====================================================

def compile_side_rake_module(doc, schema, module_name, x0_in, y0_in, module_len_in, exterior_side):
    """
    Side rake wall module between front and back walls.

    Coordinate convention:
      X = wall depth direction for side walls
      Y = module length front-to-back
      Z = height

    exterior_side:
      "left"  -> OSB on negative X side
      "right" -> OSB on positive X side
    """
    wd = wall_depth_in(schema)
    t = NOMINAL_THICKNESS_IN
    osb_t = schema["osb_thickness_in"]

    y1_in = y0_in + module_len_in
    h0 = height_front_to_back(y0_in, schema)
    h1 = height_front_to_back(y1_in, schema)

    top_plate_bottom_front = h0 - t
    top_plate_bottom_back = h1 - t

    # Bottom plate: full length of this module.
    if schema.get("bottom_plate", True):
        add_box(doc, f"{module_name}_Bottom_Plate",
                inch(x0_in), inch(y0_in), 0,
                inch(wd), inch(module_len_in), inch(t))

    # Studs: front/end, interior studs, back/end.
    # For full 48" modules, interior studs are laid out 24" o.c. from the
    # front/short end, matching the standard wall-module convention.
    # For the short/low module, the middle stud can instead be referenced from
    # the tallest stud (the back/end stud). This keeps the stud 24" o.c. from
    # the high/tall end of that module.
    stud_positions = [(0, "Front_End_Stud")]

    spacing = schema["stud_spacing_in"]
    short_module_from_tallest = (
        schema.get("short_side_rake_module_middle_stud_from_tallest", False)
        and module_len_in < schema.get("standard_module_width_in", 48) - 0.001
    )

    if short_module_from_tallest:
        # Back/end stud center is at module_len - t/2.
        # Interior stud center should be 24" forward of that.
        # Convert centerline location back to front-face location by subtracting t/2.
        stud_y = module_len_in - spacing - t
        if stud_y > t + 0.001 and stud_y < module_len_in - t - 0.001:
            stud_positions.append((stud_y, "Interior_Stud_1_24oc_From_Tallest_Stud"))
    else:
        stud_y = spacing - t / 2
        count = 1
        while stud_y < module_len_in - t - 0.001:
            stud_positions.append((stud_y, f"Interior_Stud_{count}_24oc"))
            count += 1
            stud_y += spacing

    stud_positions.append((module_len_in - t, "Back_End_Stud"))

    for sy_in, label in stud_positions:
        global_y = y0_in + sy_in
        stud_top_front = height_front_to_back(global_y, schema) - t
        stud_top_back = height_front_to_back(global_y + t, schema) - t

        add_sloped_member_y(doc, f"{module_name}_{label}",
                            inch(x0_in), inch(global_y), inch(t),
                            inch(wd), inch(t),
                            inch(stud_top_front), inch(stud_top_back))

    # Constant-thickness sloped top plate.
    if schema.get("top_plate", True):
        add_sloped_plate_y(doc, f"{module_name}_Sloped_Top_Plate",
                           inch(x0_in), inch(y0_in),
                           inch(wd), inch(module_len_in),
                           inch(top_plate_bottom_front), inch(top_plate_bottom_back),
                           inch(t))

    # Rake-cut exterior OSB.
    if schema.get("include_osb", True):
        if exterior_side == "left":
            osb_x = x0_in - osb_t
        elif exterior_side == "right":
            osb_x = x0_in + wd
        else:
            raise ValueError('exterior_side must be "left" or "right"')

        add_sloped_member_y(doc, f"{module_name}_Exterior_OSB",
                            inch(osb_x), inch(y0_in), 0,
                            inch(osb_t), inch(module_len_in),
                            inch(h0), inch(h1))


def compile_left_or_right_rake_wall(doc, schema, wall_name, x0_in, exterior_side):
    """
    Places 3 side rake modules between front/back walls.
    From front to back: 37", 48", 48".
    """
    wd = wall_depth_in(schema)
    y = wd  # interior face of front wall

    for i, module_len in enumerate(schema["side_rake_module_lengths_front_to_back_in"]):
        compile_side_rake_module(doc, schema, f"{wall_name}_M{i+1}_Rake_Module_{module_len}in",
                                 x0_in, y, module_len, exterior_side)
        y += module_len



# =====================================================
# SECOND / CONTINUOUS TOP PLATE COMPILER
# =====================================================

def compile_second_top_plates(doc, schema):
    """
    Adds a second continuous 2x6 top-plate layer over the module top plates.

    Layout:
      - Front and back plates: 155" long, full building width.
      - Left and right plates: 133" long, spanning only the clear distance
        between the front and back walls.

    The side plates follow the same global rake height plane used by the side
    rake wall modules.
    """
    if not schema.get("second_top_plate", False):
        return

    lumber = schema.get("second_top_plate_lumber", schema["wall_lumber"])
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported second_top_plate_lumber: " + lumber)

    width = schema["building_width_in"]
    wd = wall_depth_in(schema)
    clear_span = schema["clear_span_between_front_back_walls_in"]
    back_y0 = wd + clear_span

    plate_width = LUMBER_SIZES[lumber]
    t = schema.get("second_top_plate_thickness_in", NOMINAL_THICKNESS_IN)

    front_back_len = schema.get("front_back_second_top_plate_length_in", width)
    left_right_len = schema.get("left_right_second_top_plate_length_in", clear_span)

    if abs(front_back_len - width) > 0.001:
        raise ValueError("front_back_second_top_plate_length_in should equal building_width_in for this assembly.")
    if abs(left_right_len - clear_span) > 0.001:
        raise ValueError("left_right_second_top_plate_length_in should equal clear_span_between_front_back_walls_in for this assembly.")

    # Front continuous second top plate: sits on top of the front wall module top plates.
    add_box(doc, "Front_Wall_Continuous_Second_Top_Plate_2x6",
            inch(0), inch(0), inch(schema["front_wall_height_in"]),
            inch(front_back_len), inch(plate_width), inch(t))

    # Back continuous second top plate: sits on top of the back wall module top plates.
    add_box(doc, "Back_Wall_Continuous_Second_Top_Plate_2x6",
            inch(0), inch(back_y0), inch(schema["back_wall_height_in"]),
            inch(front_back_len), inch(plate_width), inch(t))

    # Left continuous side top plate: spans the clear distance between front/back walls.
    left_x0 = 0
    side_y0 = wd
    side_y1 = wd + left_right_len
    add_sloped_plate_y(doc, "Left_Rake_Wall_Continuous_Second_Top_Plate_2x6_133in",
                       inch(left_x0), inch(side_y0),
                       inch(plate_width), inch(left_right_len),
                       inch(height_front_to_back(side_y0, schema)),
                       inch(height_front_to_back(side_y1, schema)),
                       inch(t))

    # Right continuous side top plate: spans the clear distance between front/back walls.
    right_x0 = width - plate_width
    add_sloped_plate_y(doc, "Right_Rake_Wall_Continuous_Second_Top_Plate_2x6_133in",
                       inch(right_x0), inch(side_y0),
                       inch(plate_width), inch(left_right_len),
                       inch(height_front_to_back(side_y0, schema)),
                       inch(height_front_to_back(side_y1, schema)),
                       inch(t))


# =====================================================
# ASSEMBLY COMPILER
# =====================================================

def compile(schema, doc):
    validate_schema(schema)


    width = schema["building_width_in"]
    wd = wall_depth_in(schema)
    clear_span = schema["clear_span_between_front_back_walls_in"]
    overall_depth = overall_depth_in(schema)

    front_y0 = 0
    back_y0 = wd + clear_span
    left_x0 = 0
    right_x0 = width - wd

    # Front/back walls.
    compile_front_or_back_wall(doc, schema, schema.get("front_wall_name", "Front_Wall"),
                               front_y0, schema["front_wall_height_in"], "front")

    compile_front_or_back_wall(doc, schema, schema.get("back_wall_name", "Back_Wall"),
                               back_y0, schema["back_wall_height_in"], "back")

    # Side rake walls, sandwiched between front/back walls.
    compile_left_or_right_rake_wall(doc, schema, schema.get("left_wall_name", "Left_Rake_Wall"),
                                    left_x0, "left")

    compile_left_or_right_rake_wall(doc, schema, schema.get("right_wall_name", "Right_Rake_Wall"),
                                    right_x0, "right")

    # Continuous second top plate layer.
    compile_second_top_plates(doc, schema)

    # Apply assembly origin/base elevation translation.
    ox, oy, oz = schema.get("origin", (0, 0, 0))
    base_z = schema.get("assembly_base_z_in", 0)
    total_z = oz + base_z

    if ox or oy or total_z:
        origin = App.Vector(inch(ox), inch(oy), inch(total_z))
        for obj in doc.Objects:
            if hasattr(obj, "Placement"):
                obj.Placement.Base = obj.Placement.Base.add(origin)

    doc.recompute()


    print("Rake wall assembly complete.")
    print("Building width:", width, "in")
    print("Wall depth:", wd, "in")
    print("Clear span between front/back walls:", clear_span, "in")
    print("Overall outside-to-outside depth:", overall_depth, "in")
    print("Front wall height:", schema["front_wall_height_in"], "in")
    print("Back wall height:", schema["back_wall_height_in"], "in")
    print("Side rake pitch:", schema.get("side_rake_pitch_rise_per_12_in", 3.0), "in 12")
    print("Side rake module lengths front-to-back:", schema["side_rake_module_lengths_front_to_back_in"], "in")
    print("Assembly base Z:", schema.get("assembly_base_z_in", 0), "in")
    print("Front/back module sequence: corner +", schema["standard_modules_per_wall"], "standard + corner")
    if schema.get("include_osb", True):
        print("OSB: 1/2 in exterior OSB on all modules")
    if schema.get("second_top_plate", False):
        print("Added: continuous second 2x6 top plates")
        print("Second top plate lengths:",
              schema.get("front_back_second_top_plate_length_in", width), "in front/back,",
              schema.get("left_right_second_top_plate_length_in", clear_span), "in left/right")
    if schema.get("short_side_rake_module_middle_stud_from_tallest", False):
        print("Short side-rake module interior stud is 24 in o.c. from the tallest stud.")

    return list(doc.Objects)
