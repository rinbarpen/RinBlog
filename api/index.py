from app.main import app as fastapi_app

# Vercel expects a module-level `app` object for ASGI compatibility.
app = fastapi_app


