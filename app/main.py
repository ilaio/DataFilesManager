from fastapi import FastAPI

from app.routes import files

app = FastAPI(title="DataFilesManager")
app.include_router(files.router)
