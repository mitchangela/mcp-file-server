"""Print a random token for .env"""
import secrets

print(secrets.token_urlsafe(32))
