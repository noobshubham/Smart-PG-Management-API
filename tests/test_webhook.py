def test_verify_handshake_returns_challenge(client):
    r = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify",
            "hub.challenge": "echo-me",
        },
    )
    assert r.status_code == 200
    assert r.text == "echo-me"


def test_verify_with_wrong_token_rejected(client):
    r = client.get(
        "/webhooks/whatsapp",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "WRONG",
            "hub.challenge": "x",
        },
    )
    assert r.status_code == 403


def test_post_returns_200_even_for_unknown_payload(client):
    r = client.post("/webhooks/whatsapp", json={"some": "garbage"})
    # Must always 200 so providers don't retry forever.
    assert r.status_code == 200


def test_ocr_rejects_non_image_upload(client, auth_headers):
    r = client.post(
        "/residents/onboarding/ocr",
        headers=auth_headers,
        files={"file": ("doc.txt", b"not an image", "text/plain")},
    )
    assert r.status_code == 415


def test_ocr_accepts_image_and_returns_draft(client, auth_headers, fake_ai):
    from app.integrations.ai.base import IdCardExtraction

    fake_ai.id_response = IdCardExtraction(
        name="Asha Verma",
        date_of_birth="1995-08-12",
        id_number="1234 5678 9012",
        address="MG Road, Bengaluru",
        id_type="aadhar",
    )

    r = client.post(
        "/residents/onboarding/ocr",
        headers=auth_headers,
        files={"file": ("id.jpg", b"\xff\xd8\xff fake-jpeg", "image/jpeg")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Asha Verma"
    assert body["id_type"] == "aadhar"
