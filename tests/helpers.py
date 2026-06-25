def response_results(response):
    data = response.json()
    return data["results"] if isinstance(data, dict) and "results" in data else data
