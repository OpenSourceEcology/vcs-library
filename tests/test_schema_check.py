from libtools.schema_check import check_schema_source


def test_clean_schema_passes():
    assert check_schema_source('SCHEMA = {"schema_name": "x", "units": "in", "w_in": 24 * 2}') == []


def test_helper_constant_allowed():
    assert check_schema_source('T = 1.5\nSCHEMA = {"t_in": T}') == []


def test_import_rejected():
    assert any("import" in v.lower() for v in check_schema_source("import os\nSCHEMA = {}"))


def test_call_rejected():
    assert any("call" in v.lower() for v in check_schema_source('SCHEMA = {"a": open("x")}'))


def test_missing_schema_rejected():
    assert any("SCHEMA" in v for v in check_schema_source("X = {}"))


def test_duplicate_schema_rejected():
    assert check_schema_source("SCHEMA = {}\nSCHEMA = {}") != []


def test_non_dict_schema_rejected():
    assert check_schema_source("SCHEMA = 5") != []


def test_freecad_import_rejected():
    assert check_schema_source("import FreeCAD\nSCHEMA = {}") != []


def test_fstring_rejected():
    assert check_schema_source('N = "a"\nSCHEMA = {"n": f"x{N}"}') != []


def test_docstring_allowed():
    assert check_schema_source('"""Wall schema."""\nSCHEMA = {}') == []


def test_syntax_error_reported():
    assert check_schema_source("SCHEMA = {") != []


def test_syntax_error_names_line():
    violations = check_schema_source("SCHEMA = {\n")

    assert any("line 1" in violation for violation in violations)


def test_function_definition_rejected():
    violations = check_schema_source("def x():\n    pass\nSCHEMA = {}")

    assert any("function" in violation.lower() and "line 1" in violation for violation in violations)


def test_annotated_schema_assignment_allowed():
    assert check_schema_source("SCHEMA: dict = {}") == []


def test_attribute_rejected():
    violations = check_schema_source("X = obj.value\nSCHEMA = {}")

    assert any("attribute" in violation.lower() for violation in violations)


def test_comprehension_rejected():
    violations = check_schema_source("SCHEMA = {'xs': [x for x in range(3)]}")

    assert any("comprehension" in violation.lower() for violation in violations)


def test_subscript_allowed():
    assert check_schema_source("T = (1, 2)\nSCHEMA = {'t': T[0]}") == []


def test_subscript_assignment_target_rejected():
    violations = check_schema_source("SCHEMA = {}\nSCHEMA['x'] = 1")

    assert any("subscript" in violation.lower() for violation in violations)
