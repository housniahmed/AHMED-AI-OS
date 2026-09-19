from pathlib import Path

def test_deployment_files_exist():
    assert Path("Dockerfile").exists()
    assert Path("docker-compose.yml").exists()
    assert Path(".env.example").exists()
    assert Path("deploy/README.md").exists()

def test_compose_requires_database_password():
    text=Path("docker-compose.yml").read_text()
    assert "POSTGRES_PASSWORD" in text
    assert "postgres_data" in text
