import FreeCAD as App

IN = 25.4

# =====================================================
# CEILING SCHEMA — EDIT THIS SECTION
# =====================================================

ceiling_schema = {
    "name": "Ceiling_Parametric_With_OSB_Decking",
    "units": "in",

    # Overall finished outside dimensions of the entire ceiling assembly
    "width_in": 155,   # left to right
    "depth_in": 144,   # front to back

    # Options: "2x4", "2x6", "2x8", "2x10", "2x12"
    "lumber": "2x6",

    # Joists run front to back, between the doubled front/back rim joists
    "joist_spacing_in": 24,
    "first_joist_center_from_left_edge_in": 24,

    # Doubled rim joists on all four sides
    "rim_joist_count": 2,

    # Ceiling decking / attic storage deck
    "decking": {
        "include": True,
        "material": "OSB",
        "thickness_in": 0.75,
        "sheet_width_in": 48,
        "sheet_length_in": 96,
        "orientation": "perpendicular_to_joists",
        "stagger": True,
        "stagger_offset_in": 48,
        "gap_in": 0.125
    },

    "origin": (0, 0, 0)
}


# =====================================================
# CEILING COMPILER
# =====================================================

LUMBER_SIZES = {
    "2x4": 3.5,
    "2x6": 5.5,
    "2x8": 7.25,
    "2x10": 9.25,
    "2x12": 11.25
}


def compile_ceiling(schema):
    doc = App.newDocument(schema["name"])

    ox, oy, oz = schema.get("origin", (0, 0, 0))
    ox *= IN
    oy *= IN
    oz *= IN

    width = schema["width_in"] * IN
    depth = schema["depth_in"] * IN
    spacing = schema["joist_spacing_in"] * IN
    first_center = schema.get(
        "first_joist_center_from_left_edge_in",
        schema["joist_spacing_in"]
    ) * IN

    lumber = schema["lumber"]
    if lumber not in LUMBER_SIZES:
        raise ValueError("Unsupported lumber size: " + lumber)

    member_height = LUMBER_SIZES[lumber] * IN
    member_thickness = 1.5 * IN
    rim_count = schema.get("rim_joist_count", 2)

    if rim_count < 1:
        raise ValueError("rim_joist_count must be at least 1")

    rim_pack_thickness = rim_count * member_thickness

    # Members running front-to-back fit between the front/back rim packs.
    depth_member_length = depth - 2 * rim_pack_thickness

    if depth_member_length <= 0:
        raise ValueError("Ceiling depth is too small for the selected rim count and lumber thickness.")

    if width <= 2 * rim_pack_thickness:
        raise ValueError("Ceiling width is too small for the selected rim count and lumber thickness.")

    def add_box(name, x, y, z, sx, sy, sz):
        obj = doc.addObject("Part::Box", name)
        obj.Length = sx
        obj.Width = sy
        obj.Height = sz
        obj.Placement.Base = App.Vector(ox + x, oy + y, oz + z)
        return obj

    # Coordinate convention:
    # X = left to right
    # Y = front to back
    # Z = vertical
    # Overall assembly footprint is exactly width_in x depth_in.

    # =================================================
    # FRONT AND BACK RIM JOISTS
    # These run left-to-right and are full assembly width.
    # They are doubled when rim_joist_count = 2.
    # =================================================

    for i in range(rim_count):
        add_box(
            f"Front_Rim_Joist_{i + 1}",
            0,
            i * member_thickness,
            0,
            width,
            member_thickness,
            member_height
        )

        add_box(
            f"Back_Rim_Joist_{i + 1}",
            0,
            depth - (i + 1) * member_thickness,
            0,
            width,
            member_thickness,
            member_height
        )

    # =================================================
    # LEFT AND RIGHT RIM JOISTS
    # These run front-to-back, but fit BETWEEN the front/back rim packs.
    # Length = depth_in - 2 * rim_joist_count * 1.5".
    # For 144" depth and double rims: 144 - 6 = 138".
    # =================================================

    y_start = rim_pack_thickness

    for i in range(rim_count):
        add_box(
            f"Left_Rim_Joist_{i + 1}",
            i * member_thickness,
            y_start,
            0,
            member_thickness,
            depth_member_length,
            member_height
        )

        add_box(
            f"Right_Rim_Joist_{i + 1}",
            width - (i + 1) * member_thickness,
            y_start,
            0,
            member_thickness,
            depth_member_length,
            member_height
        )

    # =================================================
    # INTERIOR CEILING JOISTS
    # Joists run front-to-back and fit BETWEEN the front/back rim packs.
    # First joist center is measured from the left outside edge.
    # Subsequent joists are placed at joist_spacing_in o.c. toward the right.
    # Joists are omitted if they would interfere with the doubled right rim pack.
    # =================================================

    joist_num = 1
    center_x = first_center
    max_x_without_right_rim = width - rim_pack_thickness

    while center_x < width:
        x = center_x - member_thickness / 2

        # Keep interior joists clear of both side rim packs.
        if x >= rim_pack_thickness and x + member_thickness <= max_x_without_right_rim:
            add_box(
                f"Ceiling_Joist_{joist_num}",
                x,
                y_start,
                0,
                member_thickness,
                depth_member_length,
                member_height
            )
            joist_num += 1

        center_x += spacing

    # =================================================
    # CEILING DECKING
    # Default: 3/4" 4x8 OSB, perpendicular to joists, staggered.
    # Because joists run front-to-back, the sheet long direction runs left-to-right.
    # Panels are clipped to the exact overall ceiling footprint.
    # A small visual gap is left between sheets using gap_in.
    # =================================================

    decking = schema.get("decking", {})
    decking_count = 0

    if decking.get("include", False):
        material = decking.get("material", "OSB")
        deck_t = decking.get("thickness_in", 0.75) * IN
        sheet_w = decking.get("sheet_width_in", 48) * IN
        sheet_l = decking.get("sheet_length_in", 96) * IN
        gap = decking.get("gap_in", 0.125) * IN
        stagger = decking.get("stagger", True)
        stagger_offset = decking.get("stagger_offset_in", 48) * IN
        orientation = decking.get("orientation", "perpendicular_to_joists")

        if orientation != "perpendicular_to_joists":
            raise ValueError("This compiler currently supports decking orientation = 'perpendicular_to_joists'.")

        if sheet_w <= 0 or sheet_l <= 0 or deck_t <= 0:
            raise ValueError("Decking sheet dimensions and thickness must be positive.")

        z_deck = member_height
        row = 0
        y = 0

        while y < depth - 0.001:
            row_height = min(sheet_w, depth - y)
            offset = stagger_offset if (stagger and row % 2 == 1) else 0

            # Start at -offset so staggered rows begin with a clipped partial sheet.
            x = -offset
            col = 0

            while x < width - 0.001:
                panel_x0 = max(0, x)
                panel_x1 = min(width, x + sheet_l)

                if panel_x1 > panel_x0:
                    # Shrink panels slightly to show the configured sheet gap.
                    sx = max(0, panel_x1 - panel_x0 - gap)
                    sy = max(0, row_height - gap)

                    if sx > 0 and sy > 0:
                        decking_count += 1
                        add_box(
                            f"Ceiling_Deck_{material}_Row_{row + 1}_Sheet_{col + 1}",
                            panel_x0,
                            y,
                            z_deck,
                            sx,
                            sy,
                            deck_t
                        )

                x += sheet_l
                col += 1

            y += sheet_w
            row += 1

    doc.recompute()

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.ActiveView.viewAxometric()
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass

    print("Ceiling generated")
    print("Overall width:", schema["width_in"], "in")
    print("Overall depth:", schema["depth_in"], "in")
    print("Lumber:", lumber)
    print("Rim count per side:", rim_count)
    print("Front/back rim length:", schema["width_in"], "in")
    print("Left/right rim length:", depth_member_length / IN, "in")
    print("Interior joist length:", depth_member_length / IN, "in")
    print("Interior joists placed:", joist_num - 1)

    if decking.get("include", False):
        print("Decking material:", decking.get("material", "OSB"))
        print("Decking thickness:", decking.get("thickness_in", 0.75), "in")
        print("Decking sheets placed:", decking_count)

    return doc


compile_ceiling(ceiling_schema)
