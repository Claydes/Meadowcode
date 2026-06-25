import json

from django.urls import reverse


def test_openapi_schema_is_available(client):
    response = client.get(f"{reverse('schema')}?format=json", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/vnd.oai.openapi")

    schema = json.loads(response.content)
    assert schema["info"]["title"] == "Meadowcode API"
    assert schema["openapi"].startswith("3.")
    assert "/api/problems/" in schema["paths"]
    assert "/api/submissions/" in schema["paths"]


def test_api_docs_pages_render(client):
    swagger_response = client.get(reverse("swagger-ui"), HTTP_HOST="localhost")
    redoc_response = client.get(reverse("redoc"), HTTP_HOST="localhost")

    assert swagger_response.status_code == 200
    assert redoc_response.status_code == 200
    assert b"swagger" in swagger_response.content.lower()
    assert b"redoc" in redoc_response.content.lower()
