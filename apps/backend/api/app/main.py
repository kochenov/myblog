# myblog/apps/backend/api/app/main.py
from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Привет, мир! Сайт работает ✅"}
