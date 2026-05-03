def test_register_and_login(client):
    r = client.post(
        "/auth/register",
        json={
            "pg_name": "Acme PG",
            "owner_name": "Owner Acme",
            "phone_number": "919999000001",
            "password": "supersecret",
        },
    )
    assert r.status_code == 201
    assert r.json()["pg_name"] == "Acme PG"
    assert "hashed_password" not in r.json()

    r = client.post(
        "/auth/login",
        json={"phone_number": "919999000001", "password": "supersecret"},
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"


def test_duplicate_registration_rejected(client):
    payload = {
        "pg_name": "Dup PG",
        "owner_name": "Dup Owner",
        "phone_number": "919999000099",
        "password": "supersecret",
    }
    assert client.post("/auth/register", json=payload).status_code == 201
    assert client.post("/auth/register", json=payload).status_code == 409


def test_login_with_wrong_password(client):
    client.post(
        "/auth/register",
        json={
            "pg_name": "X",
            "owner_name": "Y",
            "phone_number": "919999000003",
            "password": "supersecret",
        },
    )
    r = client.post(
        "/auth/login",
        json={"phone_number": "919999000003", "password": "wrong"},
    )
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/me").status_code == 401


def test_me_returns_owner(client, auth_headers):
    r = client.get("/me", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["pg_name"] == "Sunrise PG"


def test_invalid_token_rejected(client):
    r = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_update_profile_sets_upi_vpa(client, auth_headers):
    r = client.patch(
        "/auth/me",
        headers=auth_headers,
        json={"upi_vpa": "owner@upi"},
    )
    assert r.status_code == 200
    assert r.json()["upi_vpa"] == "owner@upi"
