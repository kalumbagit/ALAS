# tests/conftest.py
import sys
import os
import pytest_asyncio
from tortoise import Tortoise

# Ajoute le répertoire parent au PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest_asyncio.fixture(scope="session", autouse=True)
async def initialize_tests():
    """Initialise la base Tortoise en mémoire pour les tests."""
    await Tortoise.init(
        db_url="sqlite://:memory:",  # base en mémoire = rapide et isolée
        modules={"models": ["models.user_model"]},
    )
    await Tortoise.generate_schemas()
    yield
    await Tortoise.close_connections()
