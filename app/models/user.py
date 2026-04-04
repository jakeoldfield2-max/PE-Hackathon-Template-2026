import secrets

from peewee import AutoField, CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    id = AutoField()
    username = CharField(unique=True, index=True)
    email = CharField(unique=True, index=True)
    api_key = CharField(unique=True, index=True, null=True)
    created_at = DateTimeField()

    class Meta:
        table_name = "users"

    @classmethod
    def generate_api_key(cls):
        """Generate a new API key with format upk_{random_token}.

        Returns:
            A unique API key string like 'upk_a1b2c3d4e5f6...'
        """
        token = secrets.token_hex(24)  # 48 character hex string
        return f"upk_{token}"
