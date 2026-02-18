from contextlib import asynccontextmanager
from Andromeda.api.init_db import init_db

from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield

app = FastAPI(lifespan=lifespan)



# --------------- Internal ---------------
# This section contains internal, Galacti specific functions.
# They are not publicly accessible under normal operating conditions.




# --------------- External ---------------
# This section contains external and public functions.
# They are intended to be publicly accessible at all times.

@app.get("/")
def root_get():
    return {"info":"Andromeda API is online.", "version":"v0.0.1"}