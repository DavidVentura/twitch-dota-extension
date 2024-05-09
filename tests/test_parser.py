from twitch_dota_extension.tooltips import markup_to_nodes, Node


def test_markup_to_nodes():
    s = "<h1>Active: Blink</h1> Teleport to a target point up to [b]1200[/b] units away. \\n\\nBlink Dagger cannot be used for [b]3.0[/b] seconds after taking damage from an enemy hero or Roshan."
    got = markup_to_nodes(s)
    assert got == [
        Node(tag="h1", val="Active: Blink"),
        Node(tag="text", val="Teleport to a target point up to"),
        Node(tag="b", val="1200"),
        Node(tag="text", val="units away."),
        Node(tag="newline", val=""),
        Node(tag="newline", val=""),
        Node(tag="text", val="Blink Dagger cannot be used for"),
        Node(tag="b", val="3.0"),
        Node(tag="text", val="seconds after taking damage from an enemy hero or Roshan."),
    ]


def test_markup_to_nodes_2():
    s = ""
    got = markup_to_nodes(s)
    assert got == []


def test_markup_to_nodes_3():
    s = "<br/><br/>"
    got = markup_to_nodes(s)
    assert got == [
        Node(tag="newline", val=""),
        Node(tag="newline", val=""),
    ]
