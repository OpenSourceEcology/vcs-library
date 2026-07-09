
import FreeCAD as App
import Part

# =====================================================
# DEPTH RAKE WALL MODULE — PARAMETRIC SCHEMA
# =====================================================

depth_rake_wall_module_schema = {
    "name": "Depth_Rake_Wall_Module_Parametric_U_Corners_v2",

    # -------------------------------------------------
    # PRIMARY EDITABLE PARAMETERS
    # -------------------------------------------------

    # Overall module width, left to right
    "module_width_in": 48,

    # Height at the high side of the module
    "high_side_height_in": 60,

    # Rake slope, expressed as inches of vertical drop per foot of wall depth.
    # Example: 3 = 3 inches of drop per 12 inches of horizontal run.
    "slope_drop_per_foot_in": 3,

    # Which side of the wall depth is highest.
    # Coordinate convention:
    #   exterior = OSB side / negative Y side
    #   interior = positive Y side
    # Options: "exterior", "interior"
    "high_side": "interior",

    # Lumber size for studs, plates, and U-corner pieces
    # Options: "2x4", "2x6", "2x8", "2x10", "2x12"
    "lumber": "2x6",

    # Stud spacing
    "stud_spacing_in": 24,

    # -------------------------------------------------
    # CORNER REINFORCEMENT
    # Uses the same U-corner geometry as the standard wall module.
    # -------------------------------------------------

    "left_corner_reinforcement": True,
    "right_corner_reinforcement": True,

    # -------------------------------------------------
    # OSB
    # -------------------------------------------------

    "include_osb": True,
    "osb_thickness_in": 0.5,

    # -------------------------------------------------
    # PLACEMENT
    # -------------------------------------------------

    "origin": (0, 0, 0)
}


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


def add_sloped_member_y(doc, name, x, y, z_bottom, sx, sy, top_exterior_z, top_interior_z):
    """
    Member with flat bottom and top sloping along local Y.

    X = module width
    Y = wall depth
    Z = height

    exterior side = local Y = 0
    interior side = local Y = wall depth
    """
    pts = [
        (x,      y,      z_bottom),
        (x+sx,   y,      z_bottom),
        (x+sx,   y+sy,   z_bottom),
        (x,      y+sy,   z_bottom),
        (x,      y,      top_exterior_z),
        (x+sx,   y,      top_exterior_z),
        (x+sx,   y+sy,   top_interior_z),
        (x,      y+sy,   top_interior_z),
    ]
    return add_prism(doc, name, pts)


def add_sloped_plate_y(doc, name, x, y, sx, sy, bottom_exterior_z, bottom_interior_z, thickness):
    """
    Constant-thickness sloped plate.
    Both bottom and top faces follow the rake slope across wall depth.
    """
    pts = [
        (x,      y,      bottom_exterior_z),
        (x+sx,   y,      bottom_exterior_z),
        (x+sx,   y+sy,   bottom_interior_z),
        (x,      y+sy,   bottom_interior_z),
        (x,      y,      bottom_exterior_z + thickness),
        (x+sx,   y,      bottom_exterior_z + thickness),
        (x+sx,   y+sy,   bottom_interior_z + thickness),
        (x,      y+sy,   bottom_interior_z + thickness),
    ]
    return add_prism(doc, name, pts)


def compile_depth_rake_wall_module(schema):
    ox, oy, oz = schema["origin"]
    ox = inch(ox)
    oy = inch(oy)
    oz = inch(oz)

    module_width_in = schema["module_width_in"]
    high_side_height_in = schema["high_side_height_in"]
    slope_drop_per_foot_in = schema["slope_drop_per_foot_in"]
    high_side = schema["high_side"]

    lumber = schema["lumber"]
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported lumber size: " + lumber)

    wall_depth_in = LUMBER_SIZES[lumber]
    t_in = 1.5
    stud_spacing_in = schema["stud_spacing_in"]
    osb_thickness_in = schema["osb_thickness_in"]

    total_drop_in = slope_drop_per_foot_in * (wall_depth_in / 12.0)

    if high_side == "interior":
        exterior_height_in = high_side_height_in - total_drop_in
        interior_height_in = high_side_height_in
    elif high_side == "exterior":
        exterior_height_in = high_side_height_in
        interior_height_in = high_side_height_in - total_drop_in
    else:
        raise ValueError('high_side must be "exterior" or "interior"')

    if min(exterior_height_in, interior_height_in) <= 2 * t_in:
        raise ValueError("Module is too short for bottom plate, studs, and top plate.")

    def height_at_y(y_in):
        return exterior_height_in + (interior_height_in - exterior_height_in) * (y_in / wall_depth_in)

    doc = App.newDocument(schema["name"])

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
        add_sloped_member_y(
            doc,
            label,
            ox + inch(x_in), oy, oz + t,
            t, wall_depth,
            oz + inch(exterior_height_in - t_in),
            oz + inch(interior_height_in - t_in)
        )

    # -------------------------------------------------
    # U-corner reinforcement
    # Same geometry as standard wall module, but rake-cut across depth.
    # -------------------------------------------------

    def add_left_corner_reinforcement():
        u_depth_in = wall_depth_in
        u_t_in = t_in

        add_sloped_member_y(
            doc,
            "Left_Corner_U_Left_Leg",
            ox + inch(0), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(exterior_height_in - t_in),
            oz + inch(interior_height_in - t_in)
        )

        add_sloped_member_y(
            doc,
            "Left_Corner_U_Back",
            ox + inch(u_t_in), oy + inch(u_depth_in - u_t_in), oz + t,
            inch(u_depth_in), inch(u_t_in),
            oz + inch(height_at_y(u_depth_in - u_t_in) - t_in),
            oz + inch(height_at_y(u_depth_in) - t_in)
        )

        add_sloped_member_y(
            doc,
            "Left_Corner_U_Right_Leg",
            ox + inch(u_depth_in - u_t_in + 2 * u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(exterior_height_in - t_in),
            oz + inch(interior_height_in - t_in)
        )

    def add_right_corner_reinforcement():
        u_depth_in = wall_depth_in
        u_t_in = t_in

        add_sloped_member_y(
            doc,
            "Right_Corner_U_Right_Leg",
            ox + inch(module_width_in - u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(exterior_height_in - t_in),
            oz + inch(interior_height_in - t_in)
        )

        add_sloped_member_y(
            doc,
            "Right_Corner_U_Back",
            ox + inch(module_width_in - u_t_in - u_depth_in), oy + inch(u_depth_in - u_t_in), oz + t,
            inch(u_depth_in), inch(u_t_in),
            oz + inch(height_at_y(u_depth_in - u_t_in) - t_in),
            oz + inch(height_at_y(u_depth_in) - t_in)
        )

        add_sloped_member_y(
            doc,
            "Right_Corner_U_Left_Leg",
            ox + inch(module_width_in - u_depth_in - 2 * u_t_in), oy + inch(0), oz + t,
            inch(u_t_in), inch(u_depth_in),
            oz + inch(exterior_height_in - t_in),
            oz + inch(interior_height_in - t_in)
        )

    if schema.get("left_corner_reinforcement", False):
        add_left_corner_reinforcement()

    if schema.get("right_corner_reinforcement", False):
        add_right_corner_reinforcement()

    # -------------------------------------------------
    # Sloped top plate
    # -------------------------------------------------

    add_sloped_plate_y(
        doc,
        "Sloped_Top_Plate",
        ox, oy,
        module_width, wall_depth,
        oz + inch(exterior_height_in - t_in),
        oz + inch(interior_height_in - t_in),
        t
    )

    # -------------------------------------------------
    # Exterior OSB
    # -------------------------------------------------

    if schema.get("include_osb", True):
        add_box(
            doc,
            "Exterior_OSB",
            ox, oy - osb, oz,
            module_width, osb, inch(exterior_height_in)
        )

    doc.recompute()

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.ActiveView.viewAxometric()
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    print("Depth rake wall module complete.")
    print("Module width:", module_width_in, "in")
    print("High-side height:", high_side_height_in, "in")
    print("Slope drop:", slope_drop_per_foot_in, "in/ft")
    print("High side:", high_side)
    print("Exterior height:", exterior_height_in, "in")
    print("Interior height:", interior_height_in, "in")
    print("Lumber:", lumber)

    return doc


compile_depth_rake_wall_module(depth_rake_wall_module_schema)
