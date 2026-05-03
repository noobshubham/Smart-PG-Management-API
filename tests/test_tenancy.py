"""Tenancy isolation — the most important invariant in the system.

If any of these break, two PG owners can see each other's data.
"""


def _create_room(client, headers, room_number="101", capacity=3):
    r = client.post(
        "/rooms",
        headers=headers,
        json={"room_number": room_number, "total_capacity": capacity},
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_owner_cannot_see_another_pgs_rooms(client, owner_token, second_owner_token):
    _, token_a = owner_token
    _, token_b = second_owner_token
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    room_a = _create_room(client, headers_a, "A1")

    list_b = client.get("/rooms", headers=headers_b).json()
    assert all(r["id"] != room_a["id"] for r in list_b)
    assert client.get(f"/rooms/{room_a['id']}", headers=headers_b).status_code == 404


def test_owner_cannot_modify_another_pgs_room(client, owner_token, second_owner_token):
    _, token_a = owner_token
    _, token_b = second_owner_token
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    room_a = _create_room(client, headers_a, "A1")

    r = client.patch(
        f"/rooms/{room_a['id']}",
        headers=headers_b,
        json={"total_capacity": 99},
    )
    assert r.status_code == 404
    assert client.delete(f"/rooms/{room_a['id']}", headers=headers_b).status_code == 404


def test_same_room_number_allowed_in_different_pgs(client, owner_token, second_owner_token):
    _, token_a = owner_token
    _, token_b = second_owner_token
    _create_room(client, {"Authorization": f"Bearer {token_a}"}, "101")
    # Same room_number must succeed in a different tenant.
    _create_room(client, {"Authorization": f"Bearer {token_b}"}, "101")
