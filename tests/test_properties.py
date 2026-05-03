def test_room_crud_and_available_capacity(client, auth_headers):
    r = client.post(
        "/rooms",
        headers=auth_headers,
        json={"room_number": "101", "total_capacity": 3},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["available_capacity"] == 3
    room_id = body["id"]

    r = client.get(f"/rooms/{room_id}", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["total_capacity"] == 3

    r = client.patch(
        f"/rooms/{room_id}",
        headers=auth_headers,
        json={"total_capacity": 4},
    )
    assert r.status_code == 200
    assert r.json()["total_capacity"] == 4

    assert client.delete(f"/rooms/{room_id}", headers=auth_headers).status_code == 204


def test_duplicate_room_number_rejected(client, auth_headers):
    payload = {"room_number": "101", "total_capacity": 2}
    assert client.post("/rooms", headers=auth_headers, json=payload).status_code == 201
    assert client.post("/rooms", headers=auth_headers, json=payload).status_code == 409


def test_capacity_below_occupancy_rejected(client, auth_headers):
    room = client.post(
        "/rooms",
        headers=auth_headers,
        json={"room_number": "201", "total_capacity": 2},
    ).json()

    # Add 2 residents
    for i in range(2):
        client.post(
            "/residents",
            headers=auth_headers,
            json={
                "name": f"R{i}",
                "phone_number": f"91900000010{i}",
                "room_id": room["id"],
                "monthly_rent": "5000.00",
                "joined_date": "2026-05-01",
            },
        )

    # Now try to set capacity to 1 — must reject.
    r = client.patch(
        f"/rooms/{room['id']}",
        headers=auth_headers,
        json={"total_capacity": 1},
    )
    assert r.status_code == 409
