def compile(schema, doc) -> list:
    width = schema["width_in"]
    height = schema["height_in"]
    thickness = schema["thickness_in"]

    left = doc.add_box(
        "left_box",
        0,
        0,
        0,
        width / 2 - 1,
        height,
        thickness,
    )
    right = doc.add_box(
        "right_box",
        width / 2 + 1,
        0,
        0,
        width / 2 - 1,
        height,
        thickness,
    )
    return [left, right]
