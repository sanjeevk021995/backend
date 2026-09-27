# from pydantic_settings import BaseSettings, SettingsConfigDict
# from functools import lru_cache

# class Settings(BaseSettings):
#     app_name: str = "Clinic Management API"
#     environment: str = "development"
#     debug: bool = True
#     database_url: str = "sqlite:///./clinic.db"
#     jwt_secret: str = "CHANGE_ME"
#     jwt_access_minutes: int = 30
#     jwt_refresh_days: int = 7
#     cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
#     auto_complete: bool = True
#     auto_no_show: bool = True

#     model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

#     @property
#     def cors_list(self):
#         return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

# @lru_cache
# def get_settings():
#     return Settings()

# settings = get_settings()
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "Clinic Management API"
    environment: str = "development"
    debug: bool = True
    database_url: str = "postgresql://localhost/clinic"
    jwt_secret: str = "CHANGE_ME"
    jwt_access_minutes: int = 30
    jwt_refresh_days: int = 7
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_complete: bool = True
    auto_no_show: bool = True

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    @property
    def sync_database_url(self) -> str:
        """Ensures 'postgres://' URLs from cloud services are converted to 'postgresql://'."""
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql://", 1)
        return self.database_url

    @property
    def cors_list(self):
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings():
    return Settings()

settings = get_settings()