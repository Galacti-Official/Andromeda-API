from fastapi import FastAPI

app = FastAPI()



# --------------- Internal ---------------
# This section contains internal, Galacti specific functions.
# They are not publicly accessible under normal operating conditions.




# --------------- External ---------------
# This section contains external and public functions.
# They are intended to be publicly accessible at all times.

@app.get("/")
def root_get():
    return {"info":"Andromeda API is online.", "version":"v0.0.1"}