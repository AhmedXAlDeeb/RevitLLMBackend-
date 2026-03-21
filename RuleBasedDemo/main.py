from fastapi import FastAPI
from pydantic import BaseModel
from typing import List


# Create API application
app = FastAPI()

# Define structure of incoming data

# Create endpoint
@app.post("/modeldata")
def analyze_model(data: dict):

    rooms = data.get("rooms", [])
    doors = data.get("doors", [])
    stairs = data.get("stairs", [])

    results = []

    # ROOM CHECK
    for room in rooms:
        if room["area"] < 9:
            results.append(
                f"Room '{room['name']}' is too small ({room['area']} m²)"
            )

    # DOOR CHECK
    for door in doors:
        if door["width"] < 800:
            results.append(
                f"Door width {door['width']} mm is below minimum"
            )

    # STAIR CHECK
    for stair in stairs:
        if stair["width"] < 1000:
            results.append(
                f"Stair width {stair['width']} mm is too narrow"
            )

    if len(results) == 0:
        results.append("Model passed basic checks")

    return {"analysis": results}
    