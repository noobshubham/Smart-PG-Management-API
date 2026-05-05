def _create_room(client, headers, room_number, capacity):
    return client.post(
        "/rooms",
        headers=headers,
        json={"room_number": room_number, "total_capacity": capacity},
    ).json()


def test_resident_full_lifecycle(client, auth_headers):
    room = _create_room(client, auth_headers, "101", 2)

    r = client.post(
        "/residents",
        headers=auth_headers,
        json={
            "name": "Asha Verma",
            "phone_number": "+91 90000 11111",
            "room_id": room["id"],
            "monthly_rent": "8000.00",
            "security_deposit": "16000.00",
            "joined_date": "2026-05-01",
        },
    )
    assert r.status_code == 201
    body = r.json()
    # Phone normalised: '+', spaces stripped.
    assert body["phone_number"] == "919000011111"
    resident_id = body["id"]

    # Available capacity dropped from 2 → 1.
    available = client.get(f"/rooms/{room['id']}", headers=auth_headers).json()
    assert available["available_capacity"] == 1

    # Move-out flips is_active and available_capacity recovers.
    r = client.post(
        f"/residents/{resident_id}/move-out",
        headers=auth_headers,
        json={"move_out_date": "2026-08-15"},
    )
    assert r.status_code == 200
    assert r.json()["is_active"] is False

    available = client.get(f"/rooms/{room['id']}", headers=auth_headers).json()
    assert available["available_capacity"] == 2


def test_room_full_blocks_creation(client, auth_headers):
    room = _create_room(client, auth_headers, "401", 1)

    ok = client.post(
        "/residents",
        headers=auth_headers,
        json={
            "name": "First",
            "phone_number": "919000040001",
            "room_id": room["id"],
            "monthly_rent": "1000.00",
            "joined_date": "2026-05-01",
        },
    )
    assert ok.status_code == 201

    full = client.post(
        "/residents",
        headers=auth_headers,
        json={
            "name": "Second",
            "phone_number": "919000040002",
            "room_id": room["id"],
            "monthly_rent": "1000.00",
            "joined_date": "2026-05-01",
        },
    )
    assert full.status_code == 409


def test_move_out_before_join_rejected(client, auth_headers):
    room = _create_room(client, auth_headers, "501", 1)
    rid = client.post(
        "/residents",
        headers=auth_headers,
        json={
            "name": "Time",
            "phone_number": "919000050001",
            "room_id": room["id"],
            "monthly_rent": "1000.00",
            "joined_date": "2026-06-01",
        },
    ).json()["id"]

    r = client.post(
        f"/residents/{rid}/move-out",
        headers=auth_headers,
        json={"move_out_date": "2026-05-15"},
    )
    assert r.status_code == 400


def test_ocr_returns_503_when_ai_provider_unavailable(client, auth_headers):
    # AIUnavailableError raised during dependency resolution must surface as 503,
    # not 500 from the unhandled-exception fallback.
    from app.integrations.ai import AIUnavailableError, get_ai_provider
    from app.main import app

    def _unavailable():
        raise AIUnavailableError("GEMINI_API_KEY not configured")

    app.dependency_overrides[get_ai_provider] = _unavailable
    try:
        r = client.post(
            "/residents/onboarding/ocr",
            headers=auth_headers,
            files={"file": ("id.jpg", b"\xff\xd8\xff\xe0fake", "image/jpeg")},
        )
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)

    assert r.status_code == 503
    body = r.json()
    assert "AI provider unavailable" in body["detail"]
    assert "GEMINI_API_KEY not configured" in body["detail"]
