"""
Configuración centralizada de OdontoMarket utilizando Pydantic Settings (v2).
Lee y valida automáticamente las variables definidas en el archivo `.env`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Esquema tipado de configuración global.
    Si falta una variable crítica o tiene un tipo inválido, Pydantic detendrá
    el arranque del servidor inmediatamente con un error claro (Fail-Fast).
    """

    PROJECT_NAME: str = "OdontoMarket API - Marketplace Dental Multi-Vendedor"
    VERSION: str = "1.0.0"

    # URL de conexión a la base de datos (SQLite por defecto para desarrollo local)
    DATABASE_URL: str = "sqlite:///./odontomarket.db"

    # Parámetros criptográficos para la firma de tokens JWT
    SECRET_KEY: str = "odontomarket_super_secret_jwt_key_change_in_production_2026_dental"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 horas

    # Lista de orígenes permitidos para peticiones Cross-Origin (Next.js en puerto 3000)
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        """Convierte la cadena separada por comas del .env en una lista limpia de URLs."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Configuración de Pydantic v2 para indicar de qué archivo leer las variables
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


# Instancia única (Singleton) importable desde cualquier capa del backend
settings = Settings()
