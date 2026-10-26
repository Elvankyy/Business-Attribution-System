from app.core.config import Settings


def test_settings_defaults():
    settings = Settings(_env_file=None)

    assert settings.app_name == "Business Attribution System"
    assert settings.api_port == 8000
    assert settings.llm_configured is False
    assert settings.database_url.startswith("sqlite+aiosqlite")


def test_storage_path_resolves_to_directory():
    settings = Settings(_env_file=None)

    assert settings.storage_path.is_absolute()
