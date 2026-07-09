# =====================================================
# SINGLE SLOPED ROOF RAFTER - SCHEMA + COMPILER
# WITH CORRECTED BIRDSMOUTH CUTS
# =====================================================
# 2x6 roof rafter driven by rake-wall assembly geometry.
#
# Coordinate convention matches the rake wall assembly:
#   X = left/right building width
#   Y = front/back building depth
#   Z = height
#
# The rafter runs front-to-back in Y.
# Its pitch is derived from:
#   front_height_in, back_height_in, building_depth_in
# rather than hard-coded as 3:12.
#
# Birdsmouth notes:
#   - For a 2x6 actual depth of 5.5", the default max notch depth is 1/4 depth:
#       5.5 / 4 = 1.375" = 1-3/8"
#   - The seat cuts are placed at the front and back wall bearing lines:
#       y = 0 and y = building_depth_in
#   - Front seat cut runs inward toward +Y.
#   - Back seat cut runs inward toward -Y so it stays on the back wall/top plate.
#   - The seat cuts sit on the derived rake/top-plate plane.
#   - Seat length is auto-computed from notch depth and slope unless explicitly set.
#     At 3:12, 1.375" notch depth gives a 5.5" seat length.
# =====================================================

import math
import FreeCAD as App
import Part


# =====================================================
# CONSTANTS / HELPERS
# =====================================================

IN = 25.4


def inch(value):
    return float(value) * IN


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


def add_profile_prism_x(doc, name, x0, x1, yz_points):
    """
    Extrude a 2D Y/Z side profile across X thickness.

    yz_points must be ordered around the perimeter and must not repeat the first point.
    Each point is (y, z) in inches.
    """
    n = len(yz_points)
    if n < 3:
        raise ValueError("Profile needs at least 3 points")

    front = [App.Vector(inch(x0), inch(y), inch(z)) for y, z in yz_points]
    back = [App.Vector(inch(x1), inch(y), inch(z)) for y, z in yz_points]

    faces = []

    # Left/X0 face
    poly = Part.makePolygon(front + [front[0]])
    faces.append(Part.Face(poly))

    # Right/X1 face, reversed for outward normal
    poly = Part.makePolygon(list(reversed(back)) + [back[-1]])
    faces.append(Part.Face(poly))

    # Side faces around profile
    for i in range(n):
        j = (i + 1) % n
        poly = Part.makePolygon([front[i], front[j], back[j], back[i], front[i]])
        faces.append(Part.Face(poly))

    shell = Part.makeShell(faces)
    solid = Part.makeSolid(shell)

    obj = doc.addObject("Part::Feature", name)
    obj.Shape = solid
    return obj


def add_rectangular_reference_line_y(doc, name, x_center, y0, z0, y1, z1, size):
    """Tiny sloped rectangular bar used only as a visual reference line."""
    half = size / 2.0
    pts = [
        (inch(x_center - half), inch(y0), inch(z0 - half)),
        (inch(x_center + half), inch(y0), inch(z0 - half)),
        (inch(x_center + half), inch(y1), inch(z1 - half)),
        (inch(x_center - half), inch(y1), inch(z1 - half)),
        (inch(x_center - half), inch(y0), inch(z0 + half)),
        (inch(x_center + half), inch(y0), inch(z0 + half)),
        (inch(x_center + half), inch(y1), inch(z1 + half)),
        (inch(x_center - half), inch(y1), inch(z1 + half)),
    ]
    return add_prism(doc, name, pts)


# =====================================================
# GEOMETRY FUNCTIONS
# =====================================================


def roof_plane_z_at_y(y_in, schema):
    """
    Global rake/roof bearing height at a given Y, extended beyond the wall line
    for front/back overhangs.
    """
    front_h = schema["front_height_in"]
    back_h = schema["back_height_in"]
    depth = schema["building_depth_in"]
    slope = (back_h - front_h) / depth
    return front_h + slope * y_in


def _clean_profile_points(points, eps=1e-7):
    """Remove consecutive duplicate points that can confuse face creation."""
    cleaned = []
    for p in points:
        if not cleaned:
            cleaned.append(p)
            continue
        if abs(p[0] - cleaned[-1][0]) > eps or abs(p[1] - cleaned[-1][1]) > eps:
            cleaned.append(p)
    if len(cleaned) > 1:
        if abs(cleaned[0][0] - cleaned[-1][0]) <= eps and abs(cleaned[0][1] - cleaned[-1][1]) <= eps:
            cleaned.pop()
    return cleaned


def build_rafter_side_profile(schema):
    """
    Builds the Y/Z profile for the rafter.

    With birdsmouth enabled, the base sloped underside is lowered by the notch depth,
    and horizontal seats are cut back up to the rake/top-plate bearing plane.
    """
    lumber_size = schema["lumber_size"]
    actual = schema["actual_size_in"][lumber_size]
    rafter_depth = actual["depth_in"]

    building_depth = schema["building_depth_in"]
    y_front_end = -schema["front_overhang_in"]
    y_back_end = building_depth + schema["back_overhang_in"]

    rise_per_in = (schema["back_height_in"] - schema["front_height_in"]) / building_depth
    include_birdsmouth = schema.get("include_birdsmouth_cuts", False)
    bird_depth = schema.get("birdsmouth_depth_in", 0.0) if include_birdsmouth else 0.0

    if bird_depth < 0:
        raise ValueError("birdsmouth_depth_in cannot be negative")
    if bird_depth > rafter_depth / 4.0 + 1e-9:
        raise ValueError(
            "birdsmouth_depth_in exceeds 1/4 of rafter depth. "
            f"For {lumber_size}, max is {rafter_depth / 4.0:.3f} in."
        )

    # The rafter's original sloped underside is dropped by bird_depth.
    # The birdsmouth seats then cut back up to the roof/top-plate bearing plane.
    def bearing_z(y):
        return roof_plane_z_at_y(y, schema) + schema.get("assembly_base_z_in", 0.0) + schema.get("z_offset_in", 0.0)

    def base_bottom_z(y):
        return bearing_z(y) - bird_depth

    def top_z(y):
        return base_bottom_z(y) + rafter_depth

    if include_birdsmouth and abs(rise_per_in) < 1e-9:
        raise ValueError("Cannot auto-generate birdsmouth cuts for a zero-slope rafter")

    if include_birdsmouth:
        if schema.get("birdsmouth_seat_length_in", None) is None:
            seat_len = bird_depth / abs(rise_per_in)
        else:
            seat_len = float(schema["birdsmouth_seat_length_in"])
    else:
        seat_len = 0.0

    if seat_len < 0:
        raise ValueError("birdsmouth_seat_length_in cannot be negative")

    y_front_bird = schema.get("front_birdsmouth_y_in", 0.0)
    y_back_bird = schema.get("back_birdsmouth_y_in", building_depth)

    # For the current single-slope cabin, the roof rises toward +Y.
    # The front wall seat runs inward/toward +Y from y=0.
    # The back wall seat runs inward/toward -Y from y=building_depth.
    # This keeps the back birdsmouth on the back top plate instead of beyond the wall.
    y_front_seat_start = y_front_bird
    y_front_seat_end = y_front_bird + seat_len
    y_back_seat_start = y_back_bird - seat_len
    y_back_seat_end = y_back_bird

    if include_birdsmouth:
        bottom_profile = [
            # Front overhang underside up to the front heel/plumb cut.
            (y_front_end, base_bottom_z(y_front_end)),
            (y_front_bird, base_bottom_z(y_front_bird)),

            # Front birdsmouth: vertical heel cut up, then horizontal seat inward.
            (y_front_seat_start, bearing_z(y_front_bird)),
            (y_front_seat_end, bearing_z(y_front_bird)),

            # Sloped underside between birdsmouth seats.
            (y_back_seat_start, base_bottom_z(y_back_seat_start)),

            # Back birdsmouth: horizontal seat to the back bearing line, then heel cut down.
            (y_back_seat_start, bearing_z(y_back_bird)),
            (y_back_seat_end, bearing_z(y_back_bird)),
            (y_back_bird, base_bottom_z(y_back_bird)),

            # Back overhang underside.
            (y_back_end, base_bottom_z(y_back_end)),
        ]
    else:
        bottom_profile = [
            (y_front_end, base_bottom_z(y_front_end)),
            (y_back_end, base_bottom_z(y_back_end)),
        ]

    top_profile = [
        (y_back_end, top_z(y_back_end)),
        (y_front_end, top_z(y_front_end)),
    ]

    yz_points = _clean_profile_points(bottom_profile + top_profile)

    derived = {
        "rafter_depth_in": rafter_depth,
        "birdsmouth_depth_in": bird_depth,
        "birdsmouth_seat_length_in": seat_len,
        "front_bearing_z_in": bearing_z(y_front_bird),
        "back_bearing_z_in": bearing_z(y_back_bird),
        "front_bottom_z_at_end_in": base_bottom_z(y_front_end),
        "back_bottom_z_at_end_in": base_bottom_z(y_back_end),
        "front_birdsmouth_seat_start_y_in": y_front_bird if include_birdsmouth else None,
        "front_birdsmouth_seat_end_y_in": y_front_seat_end if include_birdsmouth else None,
        "back_birdsmouth_seat_start_y_in": y_back_seat_start if include_birdsmouth else None,
        "back_birdsmouth_seat_end_y_in": y_back_bird if include_birdsmouth else None,
        "front_top_z_at_end_in": top_z(y_front_end),
        "back_top_z_at_end_in": top_z(y_back_end),
    }

    return yz_points, derived


# =====================================================
# COMPILER
# =====================================================


def compile(schema, doc):
    lumber_size = schema["lumber_size"]
    actual = schema["actual_size_in"][lumber_size]
    rafter_thickness = actual["thickness_in"]  # X direction
    rafter_depth = actual["depth_in"]

    building_depth = schema["building_depth_in"]
    front_overhang = schema["front_overhang_in"]
    back_overhang = schema["back_overhang_in"]

    y_front = -front_overhang
    y_back = building_depth + back_overhang
    horizontal_projection = y_back - y_front

    rise_per_in = (schema["back_height_in"] - schema["front_height_in"]) / building_depth
    pitch_per_foot = rise_per_in * 12.0
    angle_deg = math.degrees(math.atan(rise_per_in))
    true_length = math.sqrt(horizontal_projection ** 2 + (rise_per_in * horizontal_projection) ** 2)

    x0 = schema.get("rafter_x_in", 0.0)
    x1 = x0 + rafter_thickness
    x_center = x0 + rafter_thickness / 2.0

    yz_points, derived = build_rafter_side_profile(schema)

    rafter = add_profile_prism_x(
        doc,
        f"Roof_Rafter_{lumber_size}_{pitch_per_foot:.2f}in12_With_Birdsmouth_{horizontal_projection:.1f}in_HorizProj",
        x0,
        x1,
        yz_points
    )

    # Optional visual references: bearing/rake plane and birdsmouth seat elevations.
    if schema.get("show_reference_lines", True):
        s = schema.get("reference_line_size_in", 0.35)
        add_rectangular_reference_line_y(
            doc,
            "Reference_Rake_Bearing_Plane_Line",
            x_center + 4.0,
            y_front,
            roof_plane_z_at_y(y_front, schema) + schema.get("assembly_base_z_in", 0.0) + schema.get("z_offset_in", 0.0),
            y_back,
            roof_plane_z_at_y(y_back, schema) + schema.get("assembly_base_z_in", 0.0) + schema.get("z_offset_in", 0.0),
            s
        )

        if schema.get("include_birdsmouth_cuts", False):
            # Front seat reference, slightly offset in X.
            front_y = schema.get("front_birdsmouth_y_in", 0.0)
            back_y = schema.get("back_birdsmouth_y_in", building_depth)
            seat = derived["birdsmouth_seat_length_in"]
            add_rectangular_reference_line_y(
                doc,
                "Reference_Front_Birdsmouth_Seat_Line",
                x_center + 7.0,
                front_y,
                derived["front_bearing_z_in"],
                derived["front_birdsmouth_seat_end_y_in"],
                derived["front_bearing_z_in"],
                s
            )
            add_rectangular_reference_line_y(
                doc,
                "Reference_Back_Birdsmouth_Seat_Line",
                x_center + 7.0,
                derived["back_birdsmouth_seat_start_y_in"],
                derived["back_bearing_z_in"],
                derived["back_birdsmouth_seat_end_y_in"],
                derived["back_bearing_z_in"],
                s
            )

    doc.recompute()

    print("Single roof rafter with birdsmouth cuts complete.")
    print("Lumber:", lumber_size, "actual", rafter_thickness, "in x", rafter_depth, "in")
    print("Building depth:", building_depth, "in")
    print("Front/back overhangs:", front_overhang, "in /", back_overhang, "in")
    print("Horizontal projection:", horizontal_projection, "in")
    print("Derived pitch:", round(pitch_per_foot, 4), "in per 12 in")
    print("Derived angle:", round(angle_deg, 4), "degrees")
    print("Actual sloped reference length:", round(true_length, 4), "in")

    if schema.get("include_birdsmouth_cuts", False):
        print("Birdsmouth depth:", derived["birdsmouth_depth_in"], "in")
        print("Birdsmouth seat length:", round(derived["birdsmouth_seat_length_in"], 4), "in")
        print("Front/back bearing Z:", round(derived["front_bearing_z_in"], 4), "in /", round(derived["back_bearing_z_in"], 4), "in")
        if derived["birdsmouth_seat_length_in"] < schema.get("minimum_bearing_in", 1.5):
            print("WARNING: birdsmouth seat length is less than the requested minimum bearing.")

    return list(doc.Objects)
