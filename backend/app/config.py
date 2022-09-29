from pydantic import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Whitelabel API"
    app_description: str = f"End points for frontend solutions to cater the {app_name} needs"


settings = Settings()
