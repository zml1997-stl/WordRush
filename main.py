from fastapi import FastAPI

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Welcome to WordRush!"}

@app.get("/test")
async def test_endpoint():
    return {"status": "success", "detail": "Test endpoint is working!"}