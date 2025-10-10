from fastapi import FastAPI
from core.database import init_db
from controllers import user_controller
from core.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

# Routes
app.include_router(user_controller.router)

# Init DB
init_db(app)
