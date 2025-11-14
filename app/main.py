from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .database import init_db
from .routers import comments, pages
from .services import markdown_loader


app = FastAPI(title="RinBlog")

app.include_router(pages.router)
app.include_router(comments.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def startup() -> None:
    init_db()
    markdown_loader.refresh_cache()


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


