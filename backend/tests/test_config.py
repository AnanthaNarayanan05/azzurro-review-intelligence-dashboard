from app.core.config import DEFAULT_SQLITE_PATH, Settings


def test_defaults_use_repo_sqlite_file_and_no_llm() -> None:
    settings = Settings(_env_file=None, database_url="", llm_provider="none", llm_api_key="")

    assert settings.resolved_database_url == f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"
    assert settings.llm_enabled is False


def test_llm_requires_provider_and_key() -> None:
    assert Settings(_env_file=None, llm_provider="anthropic", llm_api_key="").llm_enabled is False
    assert Settings(_env_file=None, llm_provider="NONE", llm_api_key="x").llm_enabled is False
    assert Settings(_env_file=None, llm_provider="anthropic", llm_api_key="x").llm_enabled is True


def test_cors_origins_are_parsed_from_comma_separated_string() -> None:
    settings = Settings(_env_file=None, cors_origins=" http://a.test , ,http://b.test")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_api_key_is_hidden_from_repr() -> None:
    settings = Settings(_env_file=None, llm_api_key="super-secret-key")

    assert "super-secret-key" not in repr(settings)
