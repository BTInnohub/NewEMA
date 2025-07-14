from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
import asyncio
import json
from enum import Enum
import random

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="EMA NextGen IDS API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security setup
security = HTTPBearer()
SECRET_KEY = "ema-nextgen-intrusion-detection-system-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass

manager = ConnectionManager()

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    SECURITY = "security"
    MAINTENANCE = "maintenance"

class ZoneType(str, Enum):
    BURGLARY = "burglary"
    ROBBERY = "robbery"
    SABOTAGE = "sabotage"
    TECHNICAL = "technical"
    FIRE = "fire"
    GLASS_BREAK = "glass_break"
    MOTION = "motion"
    DOOR_CONTACT = "door_contact"

class ZoneStatus(str, Enum):
    NORMAL = "normal"
    ALARM = "alarm"
    FAULT = "fault"
    BYPASS = "bypass"
    MAINTENANCE = "maintenance"

class AlarmSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlarmStatus(str, Enum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    name: str
    role: UserRole
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True
    last_login: Optional[datetime] = None

class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    role: UserRole = UserRole.SECURITY

class UserLogin(BaseModel):
    email: str
    password: str

class Zone(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    zone_type: ZoneType
    status: ZoneStatus = ZoneStatus.NORMAL
    is_armed: bool = False
    area: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_triggered: Optional[datetime] = None
    trigger_count: int = 0

class ZoneCreate(BaseModel):
    name: str
    zone_type: ZoneType
    area: str
    description: Optional[str] = None

class ZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_type: Optional[ZoneType] = None
    area: Optional[str] = None
    description: Optional[str] = None
    is_armed: Optional[bool] = None

class Alarm(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    zone_id: str
    zone_name: str
    alarm_type: ZoneType
    severity: AlarmSeverity
    status: AlarmStatus = AlarmStatus.ACTIVE
    message: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_by: Optional[str] = None
    area: str

class Event(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    description: str
    user_id: Optional[str] = None
    zone_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SystemStats(BaseModel):
    total_zones: int
    active_alarms: int
    zones_armed: int
    zones_normal: int
    zones_fault: int
    total_events_today: int
    system_uptime: str
    last_maintenance: Optional[datetime] = None

# Utility functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        
        return User(**user)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")

async def log_event(event_type: str, description: str, user_id: str = None, zone_id: str = None, metadata: Dict = None):
    event = Event(
        event_type=event_type,
        description=description,
        user_id=user_id,
        zone_id=zone_id,
        metadata=metadata or {}
    )
    await db.events.insert_one(event.dict())

# Background task to simulate zone activity
async def simulate_zone_activity():
    while True:
        try:
            zones = await db.zones.find({"is_armed": True}).to_list(1000)
            if zones:
                # Randomly trigger some zones (very low probability)
                if random.random() < 0.1:  # 10% chance every 30 seconds
                    zone = random.choice(zones)
                    
                    # Update zone status
                    await db.zones.update_one(
                        {"id": zone["id"]},
                        {
                            "$set": {
                                "status": ZoneStatus.ALARM,
                                "last_triggered": datetime.utcnow(),
                                "$inc": {"trigger_count": 1}
                            }
                        }
                    )
                    
                    # Create alarm
                    severity = random.choice([AlarmSeverity.LOW, AlarmSeverity.MEDIUM, AlarmSeverity.HIGH, AlarmSeverity.CRITICAL])
                    alarm = Alarm(
                        zone_id=zone["id"],
                        zone_name=zone["name"],
                        alarm_type=ZoneType(zone["zone_type"]),
                        severity=severity,
                        message=f"Zone '{zone['name']}' triggered - {zone['zone_type']} detected",
                        area=zone["area"]
                    )
                    await db.alarms.insert_one(alarm.dict())
                    
                    # Log event
                    await log_event(
                        "zone_triggered",
                        f"Zone {zone['name']} triggered alarm",
                        zone_id=zone["id"],
                        metadata={"severity": severity, "zone_type": zone["zone_type"]}
                    )
                    
                    # Broadcast to all connected clients
                    await manager.broadcast(json.dumps({
                        "type": "alarm",
                        "data": alarm.dict()
                    }))
                    
                    await manager.broadcast(json.dumps({
                        "type": "zone_update",
                        "data": {"id": zone["id"], "status": ZoneStatus.ALARM}
                    }))
                    
        except Exception as e:
            logging.error(f"Error in simulation: {e}")
        
        await asyncio.sleep(30)  # Check every 30 seconds

# Start background task
@app.on_event("startup")
async def startup_event():
    asyncio.create_task(simulate_zone_activity())

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Auth endpoints
@api_router.post("/auth/register")
async def register_user(user_data: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role
    )
    
    # Store user with hashed password
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    await db.users.insert_one(user_dict)
    
    await log_event("user_registered", f"User {user.name} registered", user.id)
    
    return {"message": "User registered successfully", "user": user}

@api_router.post("/auth/login")
async def login_user(login_data: UserLogin):
    # Find user
    user_doc = await db.users.find_one({"email": login_data.email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(login_data.password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Update last login
    await db.users.update_one(
        {"id": user_doc["id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    # Create access token
    access_token = create_access_token(
        data={"sub": user_doc["id"], "email": user_doc["email"], "role": user_doc["role"]}
    )
    
    user = User(**user_doc)
    await log_event("user_login", f"User {user.name} logged in", user.id)
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# Zone endpoints
@api_router.post("/zones", response_model=Zone)
async def create_zone(zone_data: ZoneCreate, current_user: User = Depends(get_current_user)):
    zone = Zone(**zone_data.dict())
    await db.zones.insert_one(zone.dict())
    await log_event("zone_created", f"Zone {zone.name} created", current_user.id, zone.id)
    return zone

@api_router.get("/zones", response_model=List[Zone])
async def get_zones(current_user: User = Depends(get_current_user)):
    zones = await db.zones.find().to_list(1000)
    return [Zone(**zone) for zone in zones]

@api_router.get("/zones/{zone_id}", response_model=Zone)
async def get_zone(zone_id: str, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    return Zone(**zone)

@api_router.put("/zones/{zone_id}", response_model=Zone)
async def update_zone(zone_id: str, zone_data: ZoneUpdate, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    update_data = {k: v for k, v in zone_data.dict().items() if v is not None}
    if update_data:
        await db.zones.update_one({"id": zone_id}, {"$set": update_data})
    
    updated_zone = await db.zones.find_one({"id": zone_id})
    updated_zone_obj = Zone(**updated_zone)
    
    await log_event("zone_updated", f"Zone {updated_zone_obj.name} updated", current_user.id, zone_id)
    
    # Broadcast zone update
    zone_dict = updated_zone_obj.dict()
    # Convert datetime objects to ISO format strings for JSON serialization
    for key, value in zone_dict.items():
        if isinstance(value, datetime):
            zone_dict[key] = value.isoformat()
    
    await manager.broadcast(json.dumps({
        "type": "zone_update",
        "data": zone_dict
    }))
    
    return updated_zone_obj

@api_router.delete("/zones/{zone_id}")
async def delete_zone(zone_id: str, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    await db.zones.delete_one({"id": zone_id})
    await log_event("zone_deleted", f"Zone {zone['name']} deleted", current_user.id, zone_id)
    
    return {"message": "Zone deleted successfully"}

@api_router.post("/zones/{zone_id}/arm")
async def arm_zone(zone_id: str, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    await db.zones.update_one({"id": zone_id}, {"$set": {"is_armed": True}})
    await log_event("zone_armed", f"Zone {zone['name']} armed", current_user.id, zone_id)
    
    # Broadcast zone update
    await manager.broadcast(json.dumps({
        "type": "zone_update",
        "data": {"id": zone_id, "is_armed": True}
    }))
    
    return {"message": "Zone armed successfully"}

@api_router.post("/zones/{zone_id}/disarm")
async def disarm_zone(zone_id: str, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    await db.zones.update_one({"id": zone_id}, {"$set": {"is_armed": False, "status": ZoneStatus.NORMAL}})
    await log_event("zone_disarmed", f"Zone {zone['name']} disarmed", current_user.id, zone_id)
    
    # Broadcast zone update
    await manager.broadcast(json.dumps({
        "type": "zone_update",
        "data": {"id": zone_id, "is_armed": False, "status": ZoneStatus.NORMAL}
    }))
    
    return {"message": "Zone disarmed successfully"}

@api_router.post("/zones/{zone_id}/test-alarm")
async def test_alarm_zone(zone_id: str, current_user: User = Depends(get_current_user)):
    zone = await db.zones.find_one({"id": zone_id})
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    # Update zone status to alarm
    await db.zones.update_one(
        {"id": zone_id},
        {
            "$set": {
                "status": ZoneStatus.ALARM,
                "last_triggered": datetime.utcnow()
            },
            "$inc": {"trigger_count": 1}
        }
    )
    
    # Create test alarm
    severity = AlarmSeverity.MEDIUM  # Default to medium for manual tests
    alarm = Alarm(
        zone_id=zone_id,
        zone_name=zone["name"],
        alarm_type=ZoneType(zone["zone_type"]),
        severity=severity,
        message=f"TEST ALARM - Zone '{zone['name']}' manually triggered by {current_user.name}",
        area=zone["area"]
    )
    await db.alarms.insert_one(alarm.dict())
    
    # Log event
    await log_event(
        "test_alarm_triggered",
        f"Test alarm manually triggered for zone {zone['name']} by {current_user.name}",
        current_user.id,
        zone_id,
        metadata={"severity": severity, "zone_type": zone["zone_type"], "manual": True}
    )
    
    # Broadcast to all connected clients
    await manager.broadcast(json.dumps({
        "type": "alarm",
        "data": alarm.dict()
    }))
    
    await manager.broadcast(json.dumps({
        "type": "zone_update",
        "data": {"id": zone_id, "status": ZoneStatus.ALARM}
    }))
    
    return {"message": "Test alarm triggered successfully", "alarm": alarm}

# Alarm endpoints
@api_router.get("/alarms", response_model=List[Alarm])
async def get_alarms(current_user: User = Depends(get_current_user)):
    alarms = await db.alarms.find().sort("triggered_at", -1).to_list(1000)
    return [Alarm(**alarm) for alarm in alarms]

@api_router.post("/alarms/{alarm_id}/acknowledge")
async def acknowledge_alarm(alarm_id: str, current_user: User = Depends(get_current_user)):
    alarm = await db.alarms.find_one({"id": alarm_id})
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    await db.alarms.update_one(
        {"id": alarm_id},
        {
            "$set": {
                "status": AlarmStatus.ACKNOWLEDGED,
                "acknowledged_at": datetime.utcnow(),
                "acknowledged_by": current_user.id
            }
        }
    )
    
    await log_event("alarm_acknowledged", f"Alarm {alarm_id} acknowledged", current_user.id)
    
    # Broadcast alarm update
    await manager.broadcast(json.dumps({
        "type": "alarm_update",
        "data": {"id": alarm_id, "status": AlarmStatus.ACKNOWLEDGED}
    }))
    
    return {"message": "Alarm acknowledged successfully"}

@api_router.post("/alarms/{alarm_id}/resolve")
async def resolve_alarm(alarm_id: str, current_user: User = Depends(get_current_user)):
    alarm = await db.alarms.find_one({"id": alarm_id})
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    
    await db.alarms.update_one(
        {"id": alarm_id},
        {
            "$set": {
                "status": AlarmStatus.RESOLVED,
                "resolved_at": datetime.utcnow(),
                "resolved_by": current_user.id
            }
        }
    )
    
    # Reset zone status
    await db.zones.update_one({"id": alarm["zone_id"]}, {"$set": {"status": ZoneStatus.NORMAL}})
    
    await log_event("alarm_resolved", f"Alarm {alarm_id} resolved", current_user.id)
    
    # Broadcast updates
    await manager.broadcast(json.dumps({
        "type": "alarm_update",
        "data": {"id": alarm_id, "status": AlarmStatus.RESOLVED}
    }))
    
    await manager.broadcast(json.dumps({
        "type": "zone_update",
        "data": {"id": alarm["zone_id"], "status": ZoneStatus.NORMAL}
    }))
    
    return {"message": "Alarm resolved successfully"}

# Dashboard endpoints
@api_router.get("/dashboard/stats", response_model=SystemStats)
async def get_system_stats(current_user: User = Depends(get_current_user)):
    total_zones = await db.zones.count_documents({})
    active_alarms = await db.alarms.count_documents({"status": AlarmStatus.ACTIVE})
    zones_armed = await db.zones.count_documents({"is_armed": True})
    zones_normal = await db.zones.count_documents({"status": ZoneStatus.NORMAL})
    zones_fault = await db.zones.count_documents({"status": ZoneStatus.FAULT})
    
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    total_events_today = await db.events.count_documents({"timestamp": {"$gte": today}})
    
    return SystemStats(
        total_zones=total_zones,
        active_alarms=active_alarms,
        zones_armed=zones_armed,
        zones_normal=zones_normal,
        zones_fault=zones_fault,
        total_events_today=total_events_today,
        system_uptime="24h 15m",
        last_maintenance=datetime.utcnow() - timedelta(days=7)
    )

@api_router.get("/events", response_model=List[Event])
async def get_events(current_user: User = Depends(get_current_user)):
    events = await db.events.find().sort("timestamp", -1).limit(100).to_list(100)
    return [Event(**event) for event in events]

# Test endpoint
@api_router.get("/")
async def root():
    return {"message": "EMA NextGen Intrusion Detection System API"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()