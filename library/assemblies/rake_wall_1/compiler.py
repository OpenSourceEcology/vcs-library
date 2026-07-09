import FreeCAD as App
import Part

# =====================================================
# RAKE WALL ASSEMBLY SCHEMA
# =====================================================

# =====================================================
# CONSTANTS / LUMBER
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25
}


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
        [0, 1, 2, 3],  # bottom
        [4, 7, 6, 5],  # top
        [0, 4, 5, 1],  # front
        [1, 5, 6, 2],  # right
        [2, 6, 7, 3],  # back
        [3, 7, 4, 0],  # left
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


def add_sloped_stud_y(doc, name, x, y, z_bottom, sx, sy, top_front_z, top_back_z):
    """
    Member with flat bottom at z_bottom and sloped top in Y.
    Used for studs, rake-cut blocking, U-corner pieces, and OSB.
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
    Both the bottom and top faces follow the same slope.
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
# HEIGHT FUNCTIONS
# =====================================================

def height_front_to_back(y_in, schema):
    """
    Global height profile.
    y=0 is front; y=building_depth is back.
    """
    front_h = schema["front_height_in"]
    back_h = schema["back_height_in"]
    depth = schema["building_depth_in"]
    return front_h + (back_h - front_h) * (y_in / depth)


# =====================================================
# SIDE-WALL U-CORNER HELPERS
# =====================================================

def add_side_wall_u_corner(doc, schema, wall_name, corner_name, x0, y0, y1):
    """
    Adds one U-shaped corner assembly to a left/right side-wall module.

    Side-wall coordinate convention:
      - module length runs in global Y
      - wall depth runs in global X
      - left-wall exterior is negative X; left-wall interior is positive X
      - right-wall exterior is positive X; right-wall interior is negative X

    The U consists of:
      - an on-edge stud at the actual wall/module end,
      - a flat 2x member along the interior side,
      - another on-edge stud set in from the end.
    """
    lumber = schema["wall_lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5

    def top_at(y_in):
        return height_front_to_back(y_in, schema) - t

    # Closed/bottom side of the U is always toward the inside of the building.
    if wall_name == "Left_Wall":
        interior_x = x0 + wall_depth - t
    elif wall_name == "Right_Wall":
        interior_x = x0
    else:
        raise ValueError("add_side_wall_u_corner is only for Left_Wall or Right_Wall")

    if corner_name == "Front":
        edge_y = y0
        flat_y = y0 + t
        second_edge_y = y0 + wall_depth + t

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Primary_Edge_Stud",
            inch(x0), inch(edge_y), inch(t),
            inch(wall_depth), inch(t),
            inch(top_at(edge_y)), inch(top_at(edge_y + t))
        )

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Interior_Flat_2x",
            inch(interior_x), inch(flat_y), inch(t),
            inch(t), inch(wall_depth),
            inch(top_at(flat_y)), inch(top_at(flat_y + wall_depth))
        )

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Secondary_Edge_Stud",
            inch(x0), inch(second_edge_y), inch(t),
            inch(wall_depth), inch(t),
            inch(top_at(second_edge_y)), inch(top_at(second_edge_y + t))
        )

    elif corner_name == "Back":
        edge_y = y1 - t
        flat_y = y1 - t - wall_depth
        second_edge_y = y1 - wall_depth - 2 * t

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Primary_Edge_Stud",
            inch(x0), inch(edge_y), inch(t),
            inch(wall_depth), inch(t),
            inch(top_at(edge_y)), inch(top_at(edge_y + t))
        )

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Interior_Flat_2x",
            inch(interior_x), inch(flat_y), inch(t),
            inch(t), inch(wall_depth),
            inch(top_at(flat_y)), inch(top_at(flat_y + wall_depth))
        )

        add_sloped_stud_y(
            doc,
            f"{wall_name}_{corner_name}_U_Corner_Secondary_Edge_Stud",
            inch(x0), inch(second_edge_y), inch(t),
            inch(wall_depth), inch(t),
            inch(top_at(second_edge_y)), inch(top_at(second_edge_y + t))
        )

    else:
        raise ValueError("corner_name must be 'Front' or 'Back'")


# =====================================================
# WALL COMPILERS
# =====================================================

def compile_front_or_back_wall(doc, schema, wall_name, y_in):
    """
    Front/back walls:
    - run left-to-right
    - height changes through the wall thickness
    - generated directly in global coordinates
    - no rotations
    """
    module_w = schema["module_width_in"]
    n = schema["modules_per_wall"]

    lumber = schema["wall_lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5
    osb_t = schema["osb_thickness_in"]

    x_start = wall_depth

    if wall_name == "Front_Wall":
        y0 = y_in
        y_front = y0
        y_back = y0 + wall_depth
        osb_y = y0 - osb_t
        osb_top_y = y_front
    else:
        y0 = y_in - wall_depth
        y_front = y0
        y_back = y0 + wall_depth
        osb_y = y0 + wall_depth
        osb_top_y = y_back

    h_front = height_front_to_back(y_front, schema)
    h_back = height_front_to_back(y_back, schema)

    top_plate_bottom_front = h_front - t
    top_plate_bottom_back = h_back - t

    for m in range(n):
        x0 = x_start + m * module_w

        # Bottom plate
        if schema.get("bottom_plate", True):
            add_box(
                doc,
                f"{wall_name}_M{m+1}_Bottom_Plate",
                inch(x0), inch(y0), 0,
                inch(module_w), inch(wall_depth), inch(t)
            )

        # Studs: left, center at 24" o.c., right
        stud_positions = [
            (0, "Left_End_Stud"),
            (schema["stud_spacing_in"] - t / 2, "Interior_Stud_1_24oc"),
            (module_w - t, "Right_End_Stud"),
        ]

        for sx_in, label in stud_positions:
            stud_x = x0 + sx_in

            # Studs start above bottom plate and stop under top plate.
            add_sloped_stud_y(
                doc,
                f"{wall_name}_M{m+1}_{label}",
                inch(stud_x), inch(y0), inch(t),
                inch(t), inch(wall_depth),
                inch(top_plate_bottom_front),
                inch(top_plate_bottom_back)
            )

        # Correct constant-thickness sloped top plate
        if schema.get("top_plate", True):
            add_sloped_plate_y(
                doc,
                f"{wall_name}_M{m+1}_Sloped_Top_Plate",
                inch(x0), inch(y0),
                inch(module_w), inch(wall_depth),
                inch(top_plate_bottom_front),
                inch(top_plate_bottom_back),
                inch(t)
            )

        # OSB exterior
        if schema.get("include_osb", True):
            osb_h = height_front_to_back(osb_top_y, schema)

            add_box(
                doc,
                f"{wall_name}_M{m+1}_Exterior_OSB",
                inch(x0), inch(osb_y), 0,
                inch(module_w), inch(osb_t), inch(osb_h)
            )


def compile_left_or_right_wall(doc, schema, wall_name, x_in):
    """
    Left/right rake walls:
    - run front-to-back
    - height changes along wall length
    - generated directly in global coordinates
    - no rotations
    - first and last modules can receive U-corner reinforcement
    """
    module_w = schema["module_width_in"]
    n = schema["modules_per_wall"]

    lumber = schema["wall_lumber"]
    wall_depth = LUMBER_SIZES[lumber]
    t = 1.5
    osb_t = schema["osb_thickness_in"]

    if wall_name == "Left_Wall":
        x0 = x_in
        osb_x = x0 - osb_t
    else:
        x0 = x_in - wall_depth
        osb_x = x0 + wall_depth

    for m in range(n):
        y0 = m * module_w
        y1 = y0 + module_w

        h0 = height_front_to_back(y0, schema)
        h1 = height_front_to_back(y1, schema)

        top_plate_bottom_front = h0 - t
        top_plate_bottom_back = h1 - t

        # Bottom plate
        if schema.get("bottom_plate", True):
            add_box(
                doc,
                f"{wall_name}_M{m+1}_Bottom_Plate",
                inch(x0), inch(y0), 0,
                inch(wall_depth), inch(module_w), inch(t)
            )

        # Studs: front/end, middle at 24" o.c., back/end
        stud_positions = [
            (0, "Front_End_Stud"),
            (schema["stud_spacing_in"] - t / 2, "Interior_Stud_1_24oc"),
            (module_w - t, "Back_End_Stud"),
        ]

        for sy_in, label in stud_positions:
            stud_y = y0 + sy_in

            stud_y_front = stud_y
            stud_y_back = stud_y + t

            stud_top_front = height_front_to_back(stud_y_front, schema) - t
            stud_top_back = height_front_to_back(stud_y_back, schema) - t

            # Studs start above bottom plate and stop under the sloped top plate.
            add_sloped_stud_y(
                doc,
                f"{wall_name}_M{m+1}_{label}",
                inch(x0), inch(stud_y), inch(t),
                inch(wall_depth), inch(t),
                inch(stud_top_front),
                inch(stud_top_back)
            )

        # U-corner reinforcement only on the first and last side-wall modules.
        if schema.get("side_wall_u_corner_reinforcement", False):
            if m == 0:
                key = "left_wall_front_u_corner_reinforcement" if wall_name == "Left_Wall" else "right_wall_front_u_corner_reinforcement"
                if schema.get(key, True):
                    add_side_wall_u_corner(doc, schema, wall_name, "Front", x0, y0, y1)

            if m == n - 1:
                key = "left_wall_back_u_corner_reinforcement" if wall_name == "Left_Wall" else "right_wall_back_u_corner_reinforcement"
                if schema.get(key, True):
                    add_side_wall_u_corner(doc, schema, wall_name, "Back", x0, y0, y1)

        # Correct constant-thickness sloped top plate
        if schema.get("top_plate", True):
            add_sloped_plate_y(
                doc,
                f"{wall_name}_M{m+1}_Sloped_Top_Plate",
                inch(x0), inch(y0),
                inch(wall_depth), inch(module_w),
                inch(top_plate_bottom_front),
                inch(top_plate_bottom_back),
                inch(t)
            )

        # OSB exterior, rake-cut along the wall length
        if schema.get("include_osb", True):
            add_sloped_stud_y(
                doc,
                f"{wall_name}_M{m+1}_Exterior_OSB",
                inch(osb_x), inch(y0), 0,
                inch(osb_t), inch(module_w),
                inch(h0), inch(h1)
            )


# =====================================================
# SECOND / CONTINUOUS TOP PLATE COMPILER
# =====================================================

def compile_second_top_plates(doc, schema):
    """
    Adds a second continuous 2x top-plate layer over the module top plates.

    The second plates sit directly on the upper face of the module top plates,
    so their bottom face follows the same global rake height profile.

    Layout:
      - Front/back plates: full building width, 155" long.
      - Left/right plates: run between the front/back second top plates,
        so they do not overlap at the corners.

    Note:
      The left/right wall run is 144" overall. Because the front/back
      second top plates occupy a 2x6 width at each end, the modeled
      left/right plate clear span is 144" minus those two plate widths.
    """
    if not schema.get("second_top_plate", False):
        return

    lumber = schema.get("second_top_plate_lumber", schema["wall_lumber"])
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported second top plate lumber size: " + lumber)

    width = schema["building_width_in"]
    depth = schema["building_depth_in"]
    plate_width = LUMBER_SIZES[lumber]
    t = schema.get("second_top_plate_thickness_in", 1.5)

    front_back_len = schema.get("front_back_second_top_plate_length_in", width)
    left_right_len = schema.get("left_right_second_top_plate_length_in", depth)

    # Front continuous second top plate.
    front_x0 = 0
    front_y0 = 0
    front_y1 = plate_width
    add_sloped_plate_y(
        doc,
        "Front_Wall_Continuous_Second_Top_Plate_2x6",
        inch(front_x0), inch(front_y0),
        inch(front_back_len), inch(plate_width),
        inch(height_front_to_back(front_y0, schema)),
        inch(height_front_to_back(front_y1, schema)),
        inch(t)
    )

    # Back continuous second top plate.
    back_x0 = 0
    back_y0 = depth - plate_width
    back_y1 = depth
    add_sloped_plate_y(
        doc,
        "Back_Wall_Continuous_Second_Top_Plate_2x6",
        inch(back_x0), inch(back_y0),
        inch(front_back_len), inch(plate_width),
        inch(height_front_to_back(back_y0, schema)),
        inch(height_front_to_back(back_y1, schema)),
        inch(t)
    )

    # Left continuous second top plate.
    # It spans between the front/back second top plates, not under/over them.
    left_x0 = 0
    left_y0 = plate_width
    left_clear_len = max(0, left_right_len - 2 * plate_width)
    left_y1 = left_y0 + left_clear_len
    add_sloped_plate_y(
        doc,
        "Left_Wall_Continuous_Second_Top_Plate_2x6_Between_Front_Back",
        inch(left_x0), inch(left_y0),
        inch(plate_width), inch(left_clear_len),
        inch(height_front_to_back(left_y0, schema)),
        inch(height_front_to_back(left_y1, schema)),
        inch(t)
    )

    # Right continuous second top plate.
    # It spans between the front/back second top plates, not under/over them.
    right_x0 = width - plate_width
    right_y0 = plate_width
    right_clear_len = max(0, left_right_len - 2 * plate_width)
    right_y1 = right_y0 + right_clear_len
    add_sloped_plate_y(
        doc,
        "Right_Wall_Continuous_Second_Top_Plate_2x6_Between_Front_Back",
        inch(right_x0), inch(right_y0),
        inch(plate_width), inch(right_clear_len),
        inch(height_front_to_back(right_y0, schema)),
        inch(height_front_to_back(right_y1, schema)),
        inch(t)
    )


# =====================================================
# ASSEMBLY COMPILER
# =====================================================

def compile(schema, doc):

    width = schema["building_width_in"]
    depth = schema["building_depth_in"]

    compile_left_or_right_wall(doc, schema, "Left_Wall", 0)
    compile_left_or_right_wall(doc, schema, "Right_Wall", width)

    compile_front_or_back_wall(doc, schema, "Front_Wall", 0)
    compile_front_or_back_wall(doc, schema, "Back_Wall", depth)

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
    print("Footprint:", width, "in x", depth, "in")
    print("Front height:", schema["front_height_in"], "in")
    print("Back height:", schema["back_height_in"], "in")
    print("Correction: studs now stop under the top plates.")
    print("Correction: side-wall top plates are constant-thickness sloped plates.")
    print("Added: U-corner reinforcement to first and last modules of left/right walls.")
    if schema.get("second_top_plate", False):
        print("Added: continuous second 2x6 top plates over all four walls.")
        plate_width = LUMBER_SIZES[schema.get("second_top_plate_lumber", schema["wall_lumber"])]
        side_nominal = schema.get("left_right_second_top_plate_length_in", depth)
        side_clear = max(0, side_nominal - 2 * plate_width)
        print("Second top plate lengths:",
              schema.get("front_back_second_top_plate_length_in", width), "in front/back,",
              side_nominal, "in nominal left/right run,",
              side_clear, "in modeled clear span between front/back plates")

    return list(doc.Objects)
