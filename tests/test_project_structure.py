from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_main_directories_exist() -> None:
    expected_dirs = [
        "docs",
        "configs",
        "src/ingestion",
        "src/transform",
        "src/quality",
        "src/alert_engine",
        "src/common",
        "dags",
        "dbt",
        "sql/ddl",
        "sql/queries",
        "docker",
        "tests",
        "scripts",
    ]

    for relative_path in expected_dirs:
        assert (PROJECT_ROOT / relative_path).is_dir(), f"Missing directory: {relative_path}"


def test_documentation_files_exist() -> None:
    expected_files = [
        "README.md",
        "docs/requirements.md",
        "docs/architecture.md",
        "docs/data_sources.md",
        "docs/timeline.md",
        "docs/dashboard_plan.md",
    ]

    for relative_path in expected_files:
        assert (PROJECT_ROOT / relative_path).is_file(), f"Missing docs file: {relative_path}"


def test_config_files_exist() -> None:
    expected_files = [
        "configs/.env.example",
        "configs/sources.yaml",
        "pyproject.toml",
    ]

    for relative_path in expected_files:
        assert (PROJECT_ROOT / relative_path).is_file(), f"Missing config file: {relative_path}"
