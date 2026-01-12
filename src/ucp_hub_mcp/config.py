
import os
import yaml
from typing import Dict, List, Optional, Any
from pydantic import Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    """
    A settings source that loads configuration from 'config.yaml'.
    """
    def get_field_value(self, field: Any, field_name: str) -> tuple[Any, str, bool]:
        # Not used directly, we override __call__
        return None, field_name, False

    def __call__(self) -> Dict[str, Any]:
        # Look for config.yaml in the current working directory or relative to this file
        config_file = os.getenv("UCP_CONFIG_PATH", "config.yaml")
        
        # Try looking in the package root if CWD fails
        if not os.path.exists(config_file):
             # Adjusted for src layout
             package_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) 
             candidate = os.path.join(package_root, "config.yaml")
             if os.path.exists(candidate):
                 config_file = candidate

        if not os.path.exists(config_file):
            return {}
            
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

class Settings(BaseSettings):
    """
    Application Settings.
    
    Priority:
    1. Environment Variables (UCP_...)
    2. config.yaml
    3. Defaults
    """
    model_config = SettingsConfigDict(
        env_prefix='UCP_',
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    # Infrastructure
    host: str = "0.0.0.0"
    port: int = 10101
    log_level: str = "INFO"
    
    # Default Target (Optional)
    ucp_server_url: Optional[str] = None
    
    # Logic Configuration
    endpoint_map: Optional[Dict[str, str]] = None
    sandbox_globals: List[str] = Field(default_factory=list)
    
    # Defaults
    http_timeout: float = 10.0
    jwt_expiry_seconds: int = 300

    def model_post_init(self, __context: Any) -> None:
        if self.endpoint_map is None:
            self.endpoint_map = {}
        super().model_post_init(__context)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Priority Order (Last one wins/overrides):
        # 1. Defaults (Implicit)
        # 2. config.yaml
        # 3. Environment Variables (.env file or OS environ)
        # 4. Constructor Arguments (init_settings)
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
        )

# Global Instance
settings = Settings()
