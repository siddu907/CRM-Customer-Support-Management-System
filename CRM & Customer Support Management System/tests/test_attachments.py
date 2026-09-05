from tests.test_system_workflow import register_customer


def test_attachment_validation_and_download(client):
	headers = register_customer(client, "attachment-owner@example.com")
	category = client.get("/categories", headers=headers).json()[0]
	ticket = client.post("/tickets", headers=headers, json={"category_id": category["id"], "subject": "Attachment case", "description": "Attachment validation"}).json()
	endpoint = f"/tickets/{ticket['id']}/attachments"
	assert client.post(endpoint, headers=headers, files={"file": ("bad.exe", b"bad", "application/octet-stream")}).status_code == 400
	assert client.post(endpoint, headers=headers, files={"file": ("wrong.pdf", b"not pdf", "text/plain")}).status_code == 400
	uploaded = client.post(endpoint, headers=headers, files={"file": ("evidence.txt", b"evidence", "text/plain")})
	assert uploaded.status_code == 201
	downloaded = client.get(f"/attachments/{uploaded.json()['id']}", headers=headers)
	assert downloaded.status_code == 200
	assert downloaded.content == b"evidence"
