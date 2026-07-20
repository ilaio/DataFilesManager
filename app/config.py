from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    csv_data_dir: str = "data/csv"
    csv_type_inference_sample_size: int = 10_000
    csv_default_page_size: int = 50

    @property
    def csv_page_size_options(self) -> list[int]:
        return [25, 50, 100]

    @property
    def csv_data_path(self) -> Path:
        path = Path(self.csv_data_dir)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
