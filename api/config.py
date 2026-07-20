import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def normalize_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+asyncpg://", 1)
    return url


def build_database_config(url: str) -> tuple[str, dict[str, str]]:
    normalized_url = normalize_database_url(url)
    parsed = urlsplit(normalized_url)
    connect_args: dict[str, str] = {}
    filtered_query: list[tuple[str, str]] = []

    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        lowered = key.lower()
        lowered_value = value.lower()

        if lowered in {"sslmode", "ssl"}:
            if lowered_value not in {"disable", "false", "0"}:
                connect_args["ssl"] = "require"
            continue

        if lowered == "channel_binding":
            continue

        filtered_query.append((key, value))

    cleaned_url = urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            urlencode(filtered_query, doseq=True),
            parsed.fragment,
        )
    )

    return cleaned_url, connect_args


def parse_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("\"'")

    return values


class Settings:
    def __init__(self) -> None:
        env_values = load_env_file(ENV_FILE)

        def get(name: str, default: str) -> str:
            return os.environ.get(name, env_values.get(name, default))

        self.app_name = get("APP_NAME", "MoneyPlus API")
        self.environment = get("ENVIRONMENT", "development")
        self.debug = parse_bool(get("DEBUG", "true"))
        self.database_url, self.database_connect_args = build_database_config(
            get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/moneyplus")
        )
        self.frontend_url = get("FRONTEND_URL", "http://localhost:5173")
        frontend_urls_raw = get("FRONTEND_URLS", self.frontend_url)
        self.frontend_origins = [origin.strip() for origin in frontend_urls_raw.split(",") if origin.strip()]
        self.dev_demo_otp = get("DEV_DEMO_OTP", "123456")


settings = Settings()
