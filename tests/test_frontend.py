def test_problem_list_page_renders(client):
    response = client.get("/", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert b"Problems" in response.content


def test_problem_detail_page_renders(client):
    response = client.get("/problems/two-sum/", HTTP_HOST="localhost")

    assert response.status_code == 200
    assert b"code-editor" in response.content
