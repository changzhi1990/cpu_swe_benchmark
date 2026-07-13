from fastapi.testclient import TestClient

from cpu_swe_benchmark.dashboard import app


def test_dashboard_index_serves_html():
    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    assert "CPU SWE Benchmark Dashboard" in response.text
    assert "businessCharts" in response.text
    assert "systemCharts" in response.text
    assert "function drawChart" in response.text


def test_dashboard_health_route():
    client = TestClient(app)
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_system_history_route():
    client = TestClient(app)
    response = client.get("/api/system/history")

    assert response.status_code == 200
    assert "cpu" in response.json()
    assert "gpus" in response.json()
