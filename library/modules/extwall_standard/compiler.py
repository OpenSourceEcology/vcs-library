import FreeCAD as App

# =====================================================
# WALL MODULE COMPILER
# =====================================================

IN = 25.4

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25
}

def compile(schema, doc):
    ox, oy, oz = schema["origin"]
    ox *= IN
    oy *= IN
    oz *= IN

    module_width = schema["module_width_in"] * IN
    stud_height = schema["stud_height_in"] * IN
    spacing = schema["stud_spacing_in"] * IN

    lumber = schema["lumber"]
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported lumber size: " + lumber)

    wall_depth = LUMBER_SIZES[lumber] * IN
    t = 1.5 * IN
    osb = schema["osb_thickness_in"] * IN
    osb_sheet_height = schema.get("osb_sheet_height_in", 96) * IN

    def add_box(name, x, y, z, sx, sy, sz):
        obj = doc.addObject("Part::Box", name)
        obj.Length = sx
        obj.Width = sy
        obj.Height = sz
        obj.Placement.Base = App.Vector(ox + x, oy + y, oz + z)
        return obj

    # Coordinate convention:
    # X = module width
    # Y = wall depth
    # Z = height
    # Exterior / OSB side = negative Y
    # Interior side = positive Y

    add_box("Bottom_Plate", 0, 0, 0, module_width, wall_depth, t)

    add_box(
        "Top_Plate",
        0, 0, t + stud_height,
        module_width, wall_depth, t
    )

    # Standard studs
    center_x = t / 2
    stud_num = 1

    while center_x <= module_width - t / 2 + 0.01:
        add_box(
            f"Stud_{stud_num}",
            center_x - t / 2,
            0,
            t,
            t,
            wall_depth,
            stud_height
        )
        center_x += spacing
        stud_num += 1

    # Ensure right end stud exists
    last_center = center_x - spacing
    right_end_center = module_width - t / 2

    if abs(last_center - right_end_center) > 0.01:
        add_box(
            "Right_End_Stud",
            module_width - t,
            0,
            t,
            t,
            wall_depth,
            stud_height
        )

    def add_left_corner_reinforcement():
        u_depth = 5.5 * IN
        u_t = 1.5 * IN

        add_box(
            "Left_Corner_U_Left_Leg",
            0,
            0,
            t,
            u_t,
            u_depth,
            stud_height
        )

        add_box(
            "Left_Corner_U_Back",
            u_t,
            u_depth - u_t,
            t,
            u_depth,
            u_t,
            stud_height
        )

        add_box(
            "Left_Corner_U_Right_Leg",
            u_depth - u_t + 2 * u_t,
            0,
            t,
            u_t,
            u_depth,
            stud_height
        )

    def add_right_corner_reinforcement():
        u_depth = 5.5 * IN
        u_t = 1.5 * IN

        add_box(
            "Right_Corner_U_Right_Leg",
            module_width - u_t,
            0,
            t,
            u_t,
            u_depth,
            stud_height
        )

        add_box(
            "Right_Corner_U_Back",
            module_width - u_t - u_depth,
            u_depth - u_t,
            t,
            u_depth,
            u_t,
            stud_height
        )

        add_box(
            "Right_Corner_U_Left_Leg",
            module_width - u_depth - 2 * u_t,
            0,
            t,
            u_t,
            u_depth,
            stud_height
        )

    if schema.get("left_corner_reinforcement", False):
        add_left_corner_reinforcement()

    if schema.get("right_corner_reinforcement", False):
        add_right_corner_reinforcement()

    # Exterior OSB — single 4x8 sheet, 96" tall
    add_box(
        "Exterior_1_2in_OSB",
        0,
        -osb,
        0,
        module_width,
        osb,
        osb_sheet_height
    )

    doc.recompute()

    return list(doc.Objects)
