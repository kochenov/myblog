# myblog/apps/backend/api/app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Привет, мир! Сайт работает ✅"}


from app.core.config import settings

print(settings.PROJECT_NAME)
