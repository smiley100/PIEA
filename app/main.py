from fastapi import FastAPI
from app.routers import correction

app = FastAPI(title="Evalution automatique en base de données" )

# Inclure le routeur
app.include_router(correction.router)

@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de génération de corrigés !"}
