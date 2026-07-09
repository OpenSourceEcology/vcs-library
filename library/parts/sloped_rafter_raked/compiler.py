# =====================================================
# SINGLE SLOPED ROOF RAFTER - SCHEMA + COMPILER
# WITH RAKED-WALL BIRDSMOUTH CUTS
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
# IMPORTANT:
#   This version is for rafters bearing on FRONT/BACK DEPTH-RAKE WALLS,
#   where the top plate itself slopes across the wall depth.
#
#   A normal birdsmouth for a flat wall uses a horizontal seat cut.
#   That does NOT match this assembly because the front/back top plates
#   are raked in depth. Here, each birdsmouth seat follows the same rake
#   plane as the wall/top plate over the full 2x6 wall depth.
#
# Defaults match the updated 3:12 rake wall assembly:
#   - building depth: 144"
#   - front bearing height at top of second top plate: 13.5"
#   - back bearing height at top of second top plate: 49.5"
#   - front/back overhangs: 24"
#   - rafter X: 0"
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


def add_profile_prism_x(doc, name, x0, x1, yz_points):
    """
    Extrude a 2D Y/Z side profile across X thickness.

    yz_points must be ordered around the perimeter and must not repeat the first point.
    Each point is (y, z) in inches.
    """
    n = len(yz_points)
    if n < 3:
        raise ValueError("Profile needs at least 3 points")

    left = [App.Vector(inch(x0), inch(y), inch(z)) for y, z in yz_points]
    right = [App.Vector(inch(x1), inch(y), inch(z)) for y, z in yz_points]

    faces = []

    # X0 face
    faces.append(Part.Face(Part.makePolygon(left + [left[0]])))

    # X1 face, reversed for outward normal
    faces.append(Part.Face(Part.makePolygon(list(reversed(right)) + [right[-1]])))

    # Side faces around profile
    for i in range(n):
        j = (i + 1) % n
        faces.append(Part.Face(Part.makePolygon([left[i], left[j], right[j], right[i], left[i]])))

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
    Builds the Y/Z side profile for the rafter.

    For raked-wall birdsmouths:
      - the uncut/sloped underside is lowered by birdsmouth_depth_in;
      - the front seat rises to the raked bearing plane at Y = 0 and follows
        that same slope to Y = wall_depth;
      - the back seat follows the raked bearing plane from
        Y = building_depth - wall_depth to Y = building_depth;
      - this matches depth-rake front/back wall top plates, unlike a flat-wall
        birdsmouth with a horizontal seat.
    """
    lumber_size = schema["lumber_size"]
    actual = schema["actual_size_in"][lumber_size]
    rafter_depth = actual["depth_in"]

    building_depth = schema["building_depth_in"]
    wall_depth = schema.get("front_back_wall_depth_in", 5.5)
    y_front_end = -schema["front_overhang_in"]
    y_back_end = building_depth + schema["back_overhang_in"]

    include_birdsmouth = schema.get("include_birdsmouth_cuts", False)
    bird_depth = schema.get("birdsmouth_depth_in", 0.0) if include_birdsmouth else 0.0

    if bird_depth < 0:
        raise ValueError("birdsmouth_depth_in cannot be negative")
    if bird_depth > rafter_depth / 4.0 + 1e-9:
        raise ValueError(
            "birdsmouth_depth_in exceeds 1/4 of rafter depth. "
            f"For {lumber_size}, max is {rafter_depth / 4.0:.3f} in."
        )
    if wall_depth <= 0:
        raise ValueError("front_back_wall_depth_in must be greater than zero")
    if wall_depth * 2.0 >= building_depth:
        raise ValueError("front_back_wall_depth_in is too large for the building depth")

    def bearing_z(y):
        return roof_plane_z_at_y(y, schema) + schema.get("assembly_base_z_in", 0.0) + schema.get("z_offset_in", 0.0)

    def base_bottom_z(y):
        # Bottom edge of the rafter outside the notched bearing zones.
        return bearing_z(y) - bird_depth

    def top_z(y):
        return base_bottom_z(y) + rafter_depth

    front_outer_y = schema.get("front_wall_outer_y_in", 0.0)
    front_inner_y = front_outer_y + wall_depth

    back_outer_y = schema.get("back_wall_outer_y_in", building_depth)
    back_inner_y = back_outer_y - wall_depth

    if include_birdsmouth:
        bottom_profile = [
            # Front overhang underside to front exterior face.
            (y_front_end, base_bottom_z(y_front_end)),
            (front_outer_y, base_bottom_z(front_outer_y)),

            # Front raked birdsmouth: heel cut up, raked seat across wall depth,
            # then heel cut back down to the lowered underside.
            (front_outer_y, bearing_z(front_outer_y)),
            (front_inner_y, bearing_z(front_inner_y)),
            (front_inner_y, base_bottom_z(front_inner_y)),

            # Sloped underside between walls.
            (back_inner_y, base_bottom_z(back_inner_y)),

            # Back raked birdsmouth across wall depth.
            (back_inner_y, bearing_z(back_inner_y)),
            (back_outer_y, bearing_z(back_outer_y)),
            (back_outer_y, base_bottom_z(back_outer_y)),

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
        "front_wall_depth_in": wall_depth,
        "back_wall_depth_in": wall_depth,
        "front_seat_start_y_in": front_outer_y if include_birdsmouth else None,
        "front_seat_end_y_in": front_inner_y if include_birdsmouth else None,
        "back_seat_start_y_in": back_inner_y if include_birdsmouth else None,
        "back_seat_end_y_in": back_outer_y if include_birdsmouth else None,
        "front_bearing_outer_z_in": bearing_z(front_outer_y),
        "front_bearing_inner_z_in": bearing_z(front_inner_y),
        "back_bearing_inner_z_in": bearing_z(back_inner_y),
        "back_bearing_outer_z_in": bearing_z(back_outer_y),
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
    rafter_thickness = actual["thickness_in"]
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
        f"Roof_Rafter_{lumber_size}_{pitch_per_foot:.2f}in12_RakedWallBirdsmouth_{horizontal_projection:.1f}in_HorizProj",
        x0,
        x1,
        yz_points
    )

    # Optional visual references: bearing/rake plane and raked birdsmouth seat lines.
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
            add_rectangular_reference_line_y(
                doc,
                "Reference_Front_Raked_Birdsmouth_Seat_Line",
                x_center + 7.0,
                derived["front_seat_start_y_in"],
                derived["front_bearing_outer_z_in"],
                derived["front_seat_end_y_in"],
                derived["front_bearing_inner_z_in"],
                s
            )
            add_rectangular_reference_line_y(
                doc,
                "Reference_Back_Raked_Birdsmouth_Seat_Line",
                x_center + 7.0,
                derived["back_seat_start_y_in"],
                derived["back_bearing_inner_z_in"],
                derived["back_seat_end_y_in"],
                derived["back_bearing_outer_z_in"],
                s
            )

    doc.recompute()

    print("Single roof rafter with raked-wall birdsmouth cuts complete.")
    print("Lumber:", lumber_size, "actual", rafter_thickness, "in x", rafter_depth, "in")
    print("Building depth:", building_depth, "in")
    print("Front/back overhangs:", front_overhang, "in /", back_overhang, "in")
    print("Horizontal projection:", horizontal_projection, "in")
    print("Derived pitch:", round(pitch_per_foot, 4), "in per 12 in")
    print("Derived angle:", round(angle_deg, 4), "degrees")
    print("Actual sloped reference length:", round(true_length, 4), "in")

    if schema.get("include_birdsmouth_cuts", False):
        print("Birdsmouth depth:", derived["birdsmouth_depth_in"], "in")
        print("Front raked seat Y:", derived["front_seat_start_y_in"], "to", derived["front_seat_end_y_in"], "in")
        print("Back raked seat Y:", derived["back_seat_start_y_in"], "to", derived["back_seat_end_y_in"], "in")
        print("Front bearing Z outer/inner:", round(derived["front_bearing_outer_z_in"], 4), "/", round(derived["front_bearing_inner_z_in"], 4), "in")
        print("Back bearing Z inner/outer:", round(derived["back_bearing_inner_z_in"], 4), "/", round(derived["back_bearing_outer_z_in"], 4), "in")
        if schema.get("front_back_wall_depth_in", 5.5) < schema.get("minimum_bearing_in", 1.5):
            print("WARNING: raked seat length is less than the requested minimum bearing.")

    return list(doc.Objects)
