from fastapi import FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from typing import Optional, List
from bson import ObjectId
from datetime import datetime

app = FastAPI(title="Football API", description="API for football data management")

# MongoDB connection
MONGO_URL = "mongodb://localhost:27017"
client = AsyncIOMotorClient(MONGO_URL)
db = client.football


# Helper to convert ObjectId to string
def serialize_doc(doc):
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


# =============================================================================
# MODELS
# =============================================================================

class PlayerCreate(BaseModel):
    name: str
    position: Optional[str] = None
    team_id: Optional[str] = None
    age: Optional[int] = None
    nationality: Optional[str] = None


class PlayerUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    team_id: Optional[str] = None
    age: Optional[int] = None
    nationality: Optional[str] = None


class TeamCreate(BaseModel):
    name: str
    country: Optional[str] = None
    league: Optional[str] = None
    stadium: Optional[str] = None


class TeamUpdate(BaseModel):
    name: Optional[str] = None
    country: Optional[str] = None
    league: Optional[str] = None
    stadium: Optional[str] = None


class MatchCreate(BaseModel):
    home_team_id: str
    away_team_id: str
    date: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    stadium: Optional[str] = None


class MatchUpdate(BaseModel):
    home_team_id: Optional[str] = None
    away_team_id: Optional[str] = None
    date: Optional[datetime] = None
    home_score: Optional[int] = None
    away_score: Optional[int] = None
    stadium: Optional[str] = None


# =============================================================================
# PLAYERS ENDPOINTS
# =============================================================================

@app.get("/players", response_model=List[dict])
async def get_players(
    name: Optional[str] = Query(None, description="Filter by player name"),
    position: Optional[str] = Query(None, description="Filter by position"),
    team_id: Optional[str] = Query(None, description="Filter by team ID"),
    nationality: Optional[str] = Query(None, description="Filter by nationality"),
    min_age: Optional[int] = Query(None, description="Minimum age"),
    max_age: Optional[int] = Query(None, description="Maximum age"),
    is_test: Optional[bool] = Query(None, description="Filter test data only"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """Get all players with optional filters."""
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if position:
        query["position"] = {"$regex": position, "$options": "i"}
    if team_id:
        query["team_id"] = team_id
    if nationality:
        query["nationality"] = {"$regex": nationality, "$options": "i"}
    if min_age is not None:
        query["age"] = {"$gte": min_age}
    if max_age is not None:
        query.setdefault("age", {})["$lte"] = max_age
    if is_test is not None:
        query["is_test"] = is_test

    cursor = db.players.find(query).skip(skip).limit(limit)
    players = await cursor.to_list(length=limit)
    return [serialize_doc(p) for p in players]


@app.get("/players/{player_id}")
async def get_player(player_id: str):
    """Get a single player by ID."""
    try:
        player = await db.players.find_one({"_id": ObjectId(player_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID format")
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return serialize_doc(player)


@app.post("/players", status_code=201)
async def create_player(player: PlayerCreate):
    """Create a new test player. is_test=True is automatically set."""
    player_dict = player.model_dump()
    player_dict["is_test"] = True
    player_dict["created_at"] = datetime.utcnow()
    result = await db.players.insert_one(player_dict)
    player_dict["_id"] = str(result.inserted_id)
    return player_dict


@app.put("/players/{player_id}")
async def update_player(player_id: str, player: PlayerUpdate):
    """Update a player. Only test data can be modified."""
    try:
        existing = await db.players.find_one({"_id": ObjectId(player_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Player not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot modify real data. Only test data can be updated.")

    update_data = {k: v for k, v in player.model_dump().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.players.update_one({"_id": ObjectId(player_id)}, {"$set": update_data})

    updated = await db.players.find_one({"_id": ObjectId(player_id)})
    return serialize_doc(updated)


@app.delete("/players/{player_id}")
async def delete_player(player_id: str):
    """Delete a player. Only test data can be deleted."""
    try:
        existing = await db.players.find_one({"_id": ObjectId(player_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid player ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Player not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot delete real data. Only test data can be deleted.")

    await db.players.delete_one({"_id": ObjectId(player_id)})
    return {"message": "Player deleted successfully"}


# =============================================================================
# TEAMS ENDPOINTS
# =============================================================================

@app.get("/teams", response_model=List[dict])
async def get_teams(
    name: Optional[str] = Query(None, description="Filter by team name"),
    country: Optional[str] = Query(None, description="Filter by country"),
    league: Optional[str] = Query(None, description="Filter by league"),
    is_test: Optional[bool] = Query(None, description="Filter test data only"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """Get all teams with optional filters."""
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}
    if country:
        query["country"] = {"$regex": country, "$options": "i"}
    if league:
        query["league"] = {"$regex": league, "$options": "i"}
    if is_test is not None:
        query["is_test"] = is_test

    cursor = db.teams.find(query).skip(skip).limit(limit)
    teams = await cursor.to_list(length=limit)
    return [serialize_doc(t) for t in teams]


@app.get("/teams/{team_id}")
async def get_team(team_id: str):
    """Get a single team by ID."""
    try:
        team = await db.teams.find_one({"_id": ObjectId(team_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid team ID format")
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return serialize_doc(team)


@app.post("/teams", status_code=201)
async def create_team(team: TeamCreate):
    """Create a new test team. is_test=True is automatically set."""
    team_dict = team.model_dump()
    team_dict["is_test"] = True
    team_dict["created_at"] = datetime.utcnow()
    result = await db.teams.insert_one(team_dict)
    team_dict["_id"] = str(result.inserted_id)
    return team_dict


@app.put("/teams/{team_id}")
async def update_team(team_id: str, team: TeamUpdate):
    """Update a team. Only test data can be modified."""
    try:
        existing = await db.teams.find_one({"_id": ObjectId(team_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid team ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Team not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot modify real data. Only test data can be updated.")

    update_data = {k: v for k, v in team.model_dump().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.teams.update_one({"_id": ObjectId(team_id)}, {"$set": update_data})

    updated = await db.teams.find_one({"_id": ObjectId(team_id)})
    return serialize_doc(updated)


@app.delete("/teams/{team_id}")
async def delete_team(team_id: str):
    """Delete a team. Only test data can be deleted."""
    try:
        existing = await db.teams.find_one({"_id": ObjectId(team_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid team ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Team not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot delete real data. Only test data can be deleted.")

    await db.teams.delete_one({"_id": ObjectId(team_id)})
    return {"message": "Team deleted successfully"}


# =============================================================================
# MATCHES ENDPOINTS
# =============================================================================

@app.get("/matches", response_model=List[dict])
async def get_matches(
    home_team_id: Optional[str] = Query(None, description="Filter by home team ID"),
    away_team_id: Optional[str] = Query(None, description="Filter by away team ID"),
    team_id: Optional[str] = Query(None, description="Filter by any team (home or away)"),
    stadium: Optional[str] = Query(None, description="Filter by stadium"),
    date_from: Optional[datetime] = Query(None, description="Filter matches from this date"),
    date_to: Optional[datetime] = Query(None, description="Filter matches until this date"),
    is_test: Optional[bool] = Query(None, description="Filter test data only"),
    limit: int = Query(100, ge=1, le=1000),
    skip: int = Query(0, ge=0)
):
    """Get all matches with optional filters."""
    query = {}
    if home_team_id:
        query["home_team_id"] = home_team_id
    if away_team_id:
        query["away_team_id"] = away_team_id
    if team_id:
        query["$or"] = [{"home_team_id": team_id}, {"away_team_id": team_id}]
    if stadium:
        query["stadium"] = {"$regex": stadium, "$options": "i"}
    if date_from:
        query["date"] = {"$gte": date_from}
    if date_to:
        query.setdefault("date", {})["$lte"] = date_to
    if is_test is not None:
        query["is_test"] = is_test

    cursor = db.matches.find(query).skip(skip).limit(limit)
    matches = await cursor.to_list(length=limit)
    return [serialize_doc(m) for m in matches]


@app.get("/matches/{match_id}")
async def get_match(match_id: str):
    """Get a single match by ID."""
    try:
        match = await db.matches.find_one({"_id": ObjectId(match_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid match ID format")
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")
    return serialize_doc(match)


@app.post("/matches", status_code=201)
async def create_match(match: MatchCreate):
    """Create a new test match. is_test=True is automatically set."""
    match_dict = match.model_dump()
    match_dict["is_test"] = True
    match_dict["created_at"] = datetime.utcnow()
    result = await db.matches.insert_one(match_dict)
    match_dict["_id"] = str(result.inserted_id)
    return match_dict


@app.put("/matches/{match_id}")
async def update_match(match_id: str, match: MatchUpdate):
    """Update a match. Only test data can be modified."""
    try:
        existing = await db.matches.find_one({"_id": ObjectId(match_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid match ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Match not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot modify real data. Only test data can be updated.")

    update_data = {k: v for k, v in match.model_dump().items() if v is not None}
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        await db.matches.update_one({"_id": ObjectId(match_id)}, {"$set": update_data})

    updated = await db.matches.find_one({"_id": ObjectId(match_id)})
    return serialize_doc(updated)


@app.delete("/matches/{match_id}")
async def delete_match(match_id: str):
    """Delete a match. Only test data can be deleted."""
    try:
        existing = await db.matches.find_one({"_id": ObjectId(match_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid match ID format")

    if not existing:
        raise HTTPException(status_code=404, detail="Match not found")
    if not existing.get("is_test"):
        raise HTTPException(status_code=403, detail="Cannot delete real data. Only test data can be deleted.")

    await db.matches.delete_one({"_id": ObjectId(match_id)})
    return {"message": "Match deleted successfully"}


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """API root with available endpoints."""
    return {
        "message": "Football API",
        "endpoints": {
            "players": "/players",
            "teams": "/teams",
            "matches": "/matches",
            "docs": "/docs"
        }
    }


@app.delete("/cleanup/test-data")
async def cleanup_test_data():
    """Delete all test data from the database."""
    players_result = await db.players.delete_many({"is_test": True})
    teams_result = await db.teams.delete_many({"is_test": True})
    matches_result = await db.matches.delete_many({"is_test": True})

    return {
        "message": "Test data cleaned up",
        "deleted": {
            "players": players_result.deleted_count,
            "teams": teams_result.deleted_count,
            "matches": matches_result.deleted_count
        }
    }
