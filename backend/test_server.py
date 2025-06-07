from fastapi import FastAPI
import time

print("Test server script is starting...")
app = FastAPI()
print("FastAPI app object created.")

@app.on_event("startup")
async def startup_event():
    print("Server has completed startup and is ready!")

@app.get("/")
def read_root():
    return {"Hello": "World"}