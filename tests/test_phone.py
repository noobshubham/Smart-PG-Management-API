from app.core.phone import normalise_phone


def test_strips_plus_and_spaces():
    assert normalise_phone("+91 90000 11111") == "919000011111"


def test_strips_whatsapp_and_dashes():
    assert normalise_phone("(+91)-9000011111") == "919000011111"


def test_empty_input():
    assert normalise_phone("") == ""
