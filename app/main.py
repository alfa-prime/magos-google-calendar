from fastapi import FastAPI
from app.route import router

app = FastAPI(
    title="Magos Calendar API",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=True)
