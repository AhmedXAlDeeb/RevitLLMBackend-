from fastapi import FastAPI
from pydantic import BaseModel
from typing import List


app = FastAPI()

MIN_AREA = 14

# Define Room model
class Room(BaseModel):
    id: int
    name: str
    area: float

def check_room(room):
    if room.area < MIN_AREA:
        return {
            "id": room.id,
            "status": "fail",
            "message": "Area is below minimum"
        }
    return {
        "id": room.id,
        "status": "pass"
    }

@app.post("/check-compliance")
def check_compliance(rooms: List[Room]):
    return [check_room(room) for room in rooms]