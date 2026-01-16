from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.route import router
from app.core import settings

app = FastAPI(
    title="Magos Calendar API",
    swagger_ui_parameters={"persistAuthorization": True},
)

templates = Jinja2Templates(directory="app/templates")

app.include_router(router)

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def read_root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"api_key": settings.API_KEY} # Передаем ключ во фронт
    )

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
