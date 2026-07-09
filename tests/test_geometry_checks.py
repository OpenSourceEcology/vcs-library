from libtools.geometry_checks import ShapeInfo, check_completeness, check_fit, check_overlap


def fake_shape(
    name,
    bbox_in=None,
    valid=True,
    closed=True,
    volume_in3=1.0,
):
    return ShapeInfo(
        name=name,
        valid=valid,
        closed=closed,
        volume_in3=volume_in3,
        bbox_in=bbox_in or {"x": [0.0, 1.0], "y": [0.0, 1.0], "z": [0.0, 1.0]},
    )


def box_common_volume(a, b):
    volume = 1.0
    for axis in ("x", "y", "z"):
        low = max(a.bbox_in[axis][0], b.bbox_in[axis][0])
        high = min(a.bbox_in[axis][1], b.bbox_in[axis][1])
        volume *= max(0.0, high - low)
    return volume


def test_completeness_all_good():
    shapes = [fake_shape("Roof_Rafter_001")]
    expect = {"solids": {"min_count": 1, "roles": [{"pattern": "Roof_Rafter_*", "count": 1}]}}

    assert check_completeness(shapes, expect) == []


def test_completeness_missing_role_pattern_reports_violation():
    shapes = [fake_shape("Stud_001")]
    expect = {"solids": {"roles": [{"pattern": "Roof_Rafter_*", "count": 1}]}}

    violations = check_completeness(shapes, expect)

    assert any("Roof_Rafter_*" in violation and "expected 1" in violation and "actual 0" in violation for violation in violations)


def test_completeness_invalid_solid_reports_shape_name():
    violations = check_completeness([fake_shape("BadSolid", valid=False)], {})

    assert any("BadSolid" in violation and "valid" in violation for violation in violations)


def test_completeness_open_shell_reports_shape_name():
    violations = check_completeness([fake_shape("OpenShell", closed=False)], {})

    assert any("OpenShell" in violation and "closed" in violation for violation in violations)


def test_completeness_zero_volume_reports_shape_name():
    violations = check_completeness([fake_shape("FlatSolid", volume_in3=0.0)], {})

    assert any("FlatSolid" in violation and "volume" in violation for violation in violations)


def test_completeness_min_count_shortfall_reports_counts():
    violations = check_completeness([fake_shape("OnlySolid")], {"solids": {"min_count": 2}})

    assert any("min_count" in violation and "expected 2" in violation and "actual 1" in violation for violation in violations)


def test_completeness_role_without_count_requires_at_least_one_match():
    assert check_completeness(
        [fake_shape("Roof_Rafter_001")],
        {"solids": {"roles": [{"pattern": "Roof_Rafter_*"}]}},
    ) == []

    violations = check_completeness(
        [fake_shape("Stud_001")],
        {"solids": {"roles": [{"pattern": "Roof_Rafter_*"}]}},
    )
    assert any("Roof_Rafter_*" in violation and "at least 1" in violation and "actual 0" in violation for violation in violations)


def test_overlap_separated_boxes_pass():
    shapes = [
        fake_shape("A", {"x": [0.0, 1.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
        fake_shape("B", {"x": [2.0, 3.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
    ]

    assert check_overlap(shapes, box_common_volume, {}) == []


def test_overlap_intersecting_boxes_report_volume_and_names():
    shapes = [
        fake_shape("A", {"x": [0.0, 2.0], "y": [0.0, 2.0], "z": [0.0, 2.0]}),
        fake_shape("B", {"x": [1.0, 3.0], "y": [0.5, 1.5], "z": [0.0, 1.0]}),
    ]

    violations = check_overlap(shapes, box_common_volume, {"overlap": {"tolerance_in3": 0.01}})

    assert len(violations) == 1
    assert "A" in violations[0] and "B" in violations[0] and "1.0" in violations[0]


def test_overlap_allowed_contact_accepts_reversed_pattern_pair():
    shapes = [
        fake_shape("OSB_1", {"x": [0.0, 2.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
        fake_shape("Stud_1", {"x": [1.0, 3.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
    ]
    expect = {"overlap": {"tolerance_in3": 0.01, "allowed_contact": [["Stud_*", "OSB_*"]]}}

    assert check_overlap(shapes, box_common_volume, expect) == []


def test_overlap_below_tolerance_passes():
    shapes = [
        fake_shape("A", {"x": [0.0, 1.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
        fake_shape("B", {"x": [0.99, 2.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
    ]

    assert check_overlap(shapes, box_common_volume, {"overlap": {"tolerance_in3": 0.02}}) == []


def test_overlap_touching_faces_pass_without_calling_common_volume():
    shapes = [
        fake_shape("A", {"x": [0.0, 1.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
        fake_shape("B", {"x": [1.0, 2.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}),
    ]
    calls = []

    def recording_common_volume(a, b):
        calls.append((a.name, b.name))
        return box_common_volume(a, b)

    assert check_overlap(shapes, recording_common_volume, {}) == []
    assert calls == []


def test_fit_union_inside_envelope_passes():
    shapes = [
        fake_shape("A", {"x": [0.0, 1.0], "y": [0.0, 2.0], "z": [0.0, 3.0]}),
        fake_shape("B", {"x": [1.0, 2.0], "y": [1.0, 3.0], "z": [2.0, 4.0]}),
    ]
    expect = {"envelope": {"bbox_in": {"x": [0.0, 2.0], "y": [0.0, 3.0], "z": [0.0, 4.0]}}}

    assert check_fit(shapes, expect) == []


def test_fit_outside_one_axis_beyond_tolerance_reports_axis():
    shapes = [fake_shape("A", {"x": [0.0, 2.6], "y": [0.0, 1.0], "z": [0.0, 1.0]})]
    expect = {"envelope": {"bbox_in": {"x": [0.0, 2.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}, "tolerance_in": 0.5}}

    violations = check_fit(shapes, expect)

    assert len(violations) == 1
    assert "x" in violations[0] and "actual" in violations[0] and "allowed" in violations[0]


def test_fit_outside_but_within_tolerance_passes():
    shapes = [fake_shape("A", {"x": [-0.4, 2.4], "y": [0.0, 1.0], "z": [0.0, 1.0]})]
    expect = {"envelope": {"bbox_in": {"x": [0.0, 2.0], "y": [0.0, 1.0], "z": [0.0, 1.0]}, "tolerance_in": 0.5}}

    assert check_fit(shapes, expect) == []
