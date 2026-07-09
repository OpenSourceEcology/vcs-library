import FreeCAD as App
import Part

# =====================================================
# COMPILER
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25
}


def inch(value):
    return value * IN


def add_box(doc, name, x, y, z, sx, sy, sz):
    obj = doc.addObject("Part::Box", name)
    obj.Length = sx
    obj.Width = sy
    obj.Height = sz
    obj.Placement.Base = App.Vector(x, y, z)
    return obj


def add_prism(doc, name, pts):
    verts = [App.Vector(*p) for p in pts]

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


def add_sloped_member_x(doc, name, x, y, z_bottom, sx, sy, top_left_z, top_right_z):
    """
    Member with flat bottom and top sloping along local X.
    X = module width
    Y = wall depth
    Z = height
    """
    pts = [
        (x,      y,      z_bottom),
        (x+sx,   y,      z_bottom),
        (x+sx,   y+sy,   z_bottom),
        (x,      y+sy,   z_bottom),
        (x,      y,      top_left_z),
        (x+sx,   y,      top_right_z),
        (x+sx,   y+sy,   top_right_z),
        (x,      y+sy,   top_left_z),
    ]
    return add_prism(doc, name, pts)


def add_sloped_plate_x(doc, name, x, y, sx, sy, bottom_left_z, bottom_right_z, thickness):
    """
    Constant-thickness sloped plate.
    Both bottom and top faces follow the rake slope.
    """
    pts = [
        (x,      y,      bottom_left_z),
        (x+sx,   y,      bottom_right_z),
        (x+sx,   y+sy,   bottom_right_z),
        (x,      y+sy,   bottom_left_z),
        (x,      y,      bottom_left_z + thickness),
        (x+sx,   y,      bottom_right_z + thickness),
        (x+sx,   y+sy,   bottom_right_z + thickness),
        (x,      y+sy,   bottom_left_z + thickness),
    ]
    return add_prism(doc, name, pts)


def compile(schema, doc):
    ox, oy, oz = schema["origin"]
    ox = inch(ox)
    oy = inch(oy)
    oz = inch(oz)

    module_width_in = schema["module_width_in"]
    high_end_height_in = schema["high_end_height_in"]
    slope_drop_per_foot_in = schema["slope_drop_per_foot_in"]
    high_side = schema["high_side"]

    lumber = schema["lumber"]
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported lumber size: " + lumber)

    wall_depth_in = LUMBER_SIZES[lumber]
    t_in = 1.5
    stud_spacing_in = schema["stud_spacing_in"]
    osb_thickness_in = schema["osb_thickness_in"]

    total_drop_in = slope_drop_per_foot_in * (module_width_in / 12.0)

    if high_side == "right":
        left_height_in = high_end_height_in - total_drop_in
        right_height_in = high_end_height_in
    elif high_side == "left":
        left_height_in = high_end_height_in
        right_height_in = high_end_height_in - total_drop_in
    else:
        raise ValueError('high_side must be "left" or "right"')

    if min(left_height_in, right_height_in) <= 2 * t_in:
        raise ValueError("Module is too short for bottom plate, studs, and top plate.")

    def height_at_x(x_in):
        return left_height_in + (right_height_in - left_height_in) * (x_in / module_width_in)

    # Coordinate convention:
    # X = module width
    # Y = wall depth
    # Z = height
    # Exterior / OSB side = negative Y
    # Interior side = positive Y

    module_width = inch(module_width_in)
    wall_depth = inch(wall_depth_in)
    t = inch(t_in)
    osb = inch(osb_thickness_in)

    # -------------------------------------------------
    # Bottom plate
    # -------------------------------------------------

    add_box(
        doc,
        "Bottom_Plate",
        ox, oy, oz,
        module_width, wall_depth, t
    )

    # -------------------------------------------------
    # Standard studs
    # -------------------------------------------------

    stud_positions = [
        (0, "Left_End_Stud"),
        (stud_spacing_in - t_in / 2, "Interior_Stud_1_24oc"),
        (module_width_in - t_in, "Right_End_Stud"),
    ]

    for x_in, label in stud_positions:
        add_sloped_member_x(
            doc,
            label,
            ox + inch(x_in), oy, oz + t,
            t, wall_depth,
            oz + inch(height_at_x(x_in) - t_in),
            oz + inch(height_at_x(x_in + t_in) - t_in)
        )

    # -------------------------------------------------
    # U-corner reinforcement
    # Same geometry as standard wall module, but rake-cut.
    # -------------------------------------------------

    def add_left_corner_reinforcement():
        u_depth_in = wall_depth_in
        u_t_in = t_in

        add_sloped_member_x(
            doc,
            "Left_Corner_U_Left_Leg",
            ox + inch(0), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(height_at_x(0) - t_in),
            oz + inch(height_at_x(u_t_in) - t_in)
        )

        add_sloped_member_x(
            doc,
            "Left_Corner_U_Back",
            ox + inch(u_t_in), oy + inch(u_depth_in - u_t_in), oz + t,
            inch(u_depth_in), inch(u_t_in),
            oz + inch(height_at_x(u_t_in) - t_in),
            oz + inch(height_at_x(u_t_in + u_depth_in) - t_in)
        )

        add_sloped_member_x(
            doc,
            "Left_Corner_U_Right_Leg",
            ox + inch(u_depth_in - u_t_in + 2 * u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(height_at_x(u_depth_in - u_t_in + 2 * u_t_in) - t_in),
            oz + inch(height_at_x(u_depth_in - u_t_in + 3 * u_t_in) - t_in)
        )

    def add_right_corner_reinforcement():
        u_depth_in = wall_depth_in
        u_t_in = t_in

        add_sloped_member_x(
            doc,
            "Right_Corner_U_Right_Leg",
            ox + inch(module_width_in - u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(height_at_x(module_width_in - u_t_in) - t_in),
            oz + inch(height_at_x(module_width_in) - t_in)
        )

        add_sloped_member_x(
            doc,
            "Right_Corner_U_Back",
            ox + inch(module_width_in - u_t_in - u_depth_in), oy + inch(u_depth_in - u_t_in), oz + t,
            inch(u_depth_in), inch(u_t_in),
            oz + inch(height_at_x(module_width_in - u_t_in - u_depth_in) - t_in),
            oz + inch(height_at_x(module_width_in - u_t_in) - t_in)
        )

        add_sloped_member_x(
            doc,
            "Right_Corner_U_Left_Leg",
            ox + inch(module_width_in - u_depth_in - 2 * u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(height_at_x(module_width_in - u_depth_in - 2 * u_t_in) - t_in),
            oz + inch(height_at_x(module_width_in - u_depth_in - u_t_in) - t_in)
        )

    if schema.get("left_corner_reinforcement", False):
        add_left_corner_reinforcement()

    if schema.get("right_corner_reinforcement", False):
        add_right_corner_reinforcement()

    # -------------------------------------------------
    # Sloped top plate
    # -------------------------------------------------

    add_sloped_plate_x(
        doc,
        "Sloped_Top_Plate",
        ox, oy,
        module_width, wall_depth,
        oz + inch(left_height_in - t_in),
        oz + inch(right_height_in - t_in),
        t
    )

    # -------------------------------------------------
    # Exterior OSB
    # -------------------------------------------------

    if schema.get("include_osb", True):
        add_sloped_member_x(
            doc,
            "Exterior_OSB",
            ox, oy - osb, oz,
            module_width, osb,
            oz + inch(left_height_in),
            oz + inch(right_height_in)
        )

    doc.recompute()

    print("Side rake wall module complete.")
    print("Module width:", module_width_in, "in")
    print("High-end height:", high_end_height_in, "in")
    print("Slope drop:", slope_drop_per_foot_in, "in/ft")
    print("High side:", high_side)
    print("Low side height:", min(left_height_in, right_height_in), "in")
    print("Lumber:", lumber)

    return list(doc.Objects)
