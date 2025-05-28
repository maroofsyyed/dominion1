from fastapi import FastAPI, APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime, timedelta
import bcrypt
import jwt
import json
import base64
from passlib.context import CryptContext
import asyncio
from collections import defaultdict

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Dominion Fitness API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "dominion_secret_key_change_in_production"
ALGORITHM = "HS256"

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, community_id: str):
        await websocket.accept()
        self.active_connections[community_id].append(websocket)

    def disconnect(self, websocket: WebSocket, community_id: str):
        self.active_connections[community_id].remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast_to_community(self, message: str, community_id: str):
        for connection in self.active_connections[community_id]:
            await connection.send_text(message)

manager = ConnectionManager()

# ========== MODELS ==========

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    password_hash: str
    full_name: str
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    university: Optional[str] = None
    city: Optional[str] = None
    profile_photo: Optional[str] = None
    goals: List[str] = []
    points: int = 0
    badges: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    university: Optional[str] = None
    city: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Exercise(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    pillar: str  # Horizontal Pull, Vertical Pull, etc.
    skill_level: str  # Beginner, Intermediate, Advanced, Elite
    description: str
    instructions: List[str]
    common_mistakes: List[str]
    video_url: Optional[str] = None
    prerequisites: List[str] = []
    progression_order: int
    created_at: datetime = Field(default_factory=datetime.utcnow)

class MobilityExercise(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    area: str  # hips, shoulders, etc.
    description: str
    instructions: List[str]
    benefits: List[str]
    video_url: Optional[str] = None
    hold_time: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserProgress(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    exercise_id: str
    date: datetime = Field(default_factory=datetime.utcnow)
    reps: Optional[int] = None
    sets: Optional[int] = None
    hold_time: Optional[float] = None
    weight: Optional[float] = None
    notes: Optional[str] = None

class Workout(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    name: str
    exercises: List[Dict[str, Any]]
    scheduled_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    duration: Optional[int] = None  # in minutes
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Community(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: str  # city, university, general
    description: str
    members: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    community_id: str
    username: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    category: str
    image_url: Optional[str] = None
    in_stock: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

# ========== AUTH HELPERS ==========

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"id": user_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# ========== INITIAL DATA ==========

async def initialize_exercises():
    """Initialize the exercise database with the bodyweight fitness progression"""
    
    # Force refresh of exercises
    await db.exercises.delete_many({})
    
    exercises_data = [
        # Horizontal Pull - Beginner
        {"name": "German Hang", "pillar": "Horizontal Pull", "skill_level": "Beginner", "description": "A static hanging position that builds shoulder flexibility and strength.", "instructions": ["Hang from a bar with arms fully extended", "Keep shoulders engaged", "Hold for specified time"], "common_mistakes": ["Letting shoulders sag", "Not maintaining grip strength"], "progression_order": 1},
        {"name": "Skin the Cat", "pillar": "Horizontal Pull", "skill_level": "Beginner", "description": "A dynamic movement that improves shoulder mobility and core strength.", "instructions": ["Start in dead hang", "Lift knees to chest", "Continue rotating backwards"], "common_mistakes": ["Moving too fast", "Not controlling the movement"], "progression_order": 2},
        {"name": "Tuck Back Lever", "pillar": "Horizontal Pull", "skill_level": "Beginner", "description": "Beginning static hold for back lever progression.", "instructions": ["Start in inverted position", "Tuck knees to chest", "Hold horizontal position"], "common_mistakes": ["Not keeping body tight", "Dropping hips"], "progression_order": 3},
        
        # Horizontal Pull - Intermediate
        {"name": "Tuck Front Lever", "pillar": "Horizontal Pull", "skill_level": "Intermediate", "description": "Core static hold building towards front lever.", "instructions": ["Dead hang from bar", "Lift legs into tuck position", "Keep body horizontal"], "common_mistakes": ["Piking at hips", "Not engaging lats"], "progression_order": 4},
        {"name": "Advanced Tuck Front Lever", "pillar": "Horizontal Pull", "skill_level": "Intermediate", "description": "Extended tuck position for front lever progression.", "instructions": ["From tuck front lever", "Extend knees slightly", "Maintain horizontal body"], "common_mistakes": ["Extending too far too fast", "Losing shoulder engagement"], "progression_order": 5},
        {"name": "Front Lever", "pillar": "Horizontal Pull", "skill_level": "Intermediate", "description": "Full front lever - advanced static hold.", "instructions": ["Dead hang position", "Lift body to horizontal", "Keep legs straight"], "common_mistakes": ["Sagging hips", "Not pulling with lats"], "progression_order": 6},
        
        # Horizontal Push - Beginner
        {"name": "Incline Push Up", "pillar": "Horizontal Push", "skill_level": "Beginner", "description": "Easier variation of push up with hands elevated.", "instructions": ["Hands on elevated surface", "Lower chest to edge", "Push back up"], "common_mistakes": ["Sagging hips", "Not keeping elbows in"], "progression_order": 1},
        {"name": "Push Up", "pillar": "Horizontal Push", "skill_level": "Beginner", "description": "Standard push up on floor.", "instructions": ["Hands shoulder width", "Lower chest to floor", "Push back up"], "common_mistakes": ["Flaring elbows", "Not full range of motion"], "progression_order": 2},
        {"name": "Diamond Push Up", "pillar": "Horizontal Push", "skill_level": "Beginner", "description": "Push up with hands close together.", "instructions": ["Hands forming diamond", "Elbows close to body", "Lower chest to hands"], "common_mistakes": ["Hands too far forward", "Shoulders rising"], "progression_order": 3},
        
        # Horizontal Push - Advanced
        {"name": "One Arm Push Up Progression", "pillar": "Horizontal Push", "skill_level": "Advanced", "description": "Single arm push up progression building unilateral strength.", "instructions": ["Start in staggered position", "Shift weight to working arm", "Lower chest to ground", "Push up with one arm"], "common_mistakes": ["Not shifting enough weight", "Rotating torso", "Using momentum"], "progression_order": 6},
        {"name": "Handstand Push Up", "pillar": "Horizontal Push", "skill_level": "Advanced", "description": "Push up performed in handstand position.", "instructions": ["Hold handstand against wall", "Lower head to ground", "Press back to start"], "common_mistakes": ["Not going deep enough", "Losing balance", "Arching back"], "progression_order": 7},
        
        # Horizontal Push - Elite
        {"name": "One Arm Handstand Push Up", "pillar": "Horizontal Push", "skill_level": "Elite", "description": "Ultimate pushing exercise combining handstand and one arm strength.", "instructions": ["One arm handstand hold", "Lower head to ground", "Press back up"], "common_mistakes": ["Insufficient strength base", "Poor handstand balance", "Rushing progression"], "progression_order": 8},
        {"name": "Planche Push Up", "pillar": "Horizontal Push", "skill_level": "Elite", "description": "Push up performed in planche position.", "instructions": ["Hold planche position", "Lower body as unit", "Press back to planche"], "common_mistakes": ["Breaking planche form", "Not maintaining lean", "Insufficient strength"], "progression_order": 9},
        
        # Vertical Pull - Beginner
        {"name": "Vertical Row", "pillar": "Vertical Pull", "skill_level": "Beginner", "description": "Basic rowing movement for building pulling strength.", "instructions": ["Set bar at chest height", "Lean back at angle", "Pull chest to bar"], "common_mistakes": ["Not keeping body straight", "Using momentum"], "progression_order": 1},
        {"name": "Incline Row", "pillar": "Vertical Pull", "skill_level": "Beginner", "description": "Angled rowing for progression to horizontal row.", "instructions": ["Bar at waist height", "Body at 45-degree angle", "Pull with control"], "common_mistakes": ["Sagging hips", "Not squeezing shoulder blades"], "progression_order": 2},
        {"name": "Pull Up", "pillar": "Vertical Pull", "skill_level": "Beginner", "description": "Classic vertical pulling exercise.", "instructions": ["Dead hang from bar", "Pull until chin over bar", "Lower with control"], "common_mistakes": ["Kipping unnecessarily", "Not full range of motion"], "progression_order": 3},
        
        # Vertical Pull - Advanced
        {"name": "Wide Grip Pull Up", "pillar": "Vertical Pull", "skill_level": "Advanced", "description": "Pull up with hands wider than shoulders.", "instructions": ["Hands 1.5x shoulder width", "Pull chest to bar", "Focus on lat engagement"], "common_mistakes": ["Not going full range", "Using momentum", "Insufficient lat activation"], "progression_order": 6},
        {"name": "Archer Pull Up", "pillar": "Vertical Pull", "skill_level": "Advanced", "description": "Unilateral pull up variation.", "instructions": ["Pull to one side", "Straighten opposite arm", "Alternate sides"], "common_mistakes": ["Not shifting weight enough", "Using both arms equally", "Poor control"], "progression_order": 7},
        
        # Vertical Pull - Elite
        {"name": "One Arm Pull Up", "pillar": "Vertical Pull", "skill_level": "Elite", "description": "Ultimate pulling exercise using single arm.", "instructions": ["Hang from one arm", "Pull chin over bar", "Lower with control"], "common_mistakes": ["Insufficient strength base", "Body swinging", "Not full range"], "progression_order": 8},
        {"name": "Weighted Pull Up", "pillar": "Vertical Pull", "skill_level": "Elite", "description": "Pull up with additional weight.", "instructions": ["Add weight to body", "Maintain perfect form", "Full range of motion"], "common_mistakes": ["Too much weight too soon", "Compromising form", "Incomplete range"], "progression_order": 9},
        
        # Vertical Push - Beginner
        {"name": "Push Up", "pillar": "Vertical Push", "skill_level": "Beginner", "description": "Basic pushing exercise for chest and arms.", "instructions": ["Plank position", "Lower chest to ground", "Push back up"], "common_mistakes": ["Sagging hips", "Not full range of motion"], "progression_order": 1},
        {"name": "Pike Push Up", "pillar": "Vertical Push", "skill_level": "Beginner", "description": "Inverted push up targeting shoulders.", "instructions": ["Pike position", "Lower head towards ground", "Push back up"], "common_mistakes": ["Not keeping legs straight", "Going too low"], "progression_order": 2},
        {"name": "Wall Handstand", "pillar": "Vertical Push", "skill_level": "Beginner", "description": "Static handstand hold against wall.", "instructions": ["Kick up to wall", "Hold handstand position", "Keep body straight"], "common_mistakes": ["Arching back", "Not engaging core"], "progression_order": 3},
        
        # Vertical Push - Advanced
        {"name": "Freestanding Handstand", "pillar": "Vertical Push", "skill_level": "Advanced", "description": "Handstand without wall support.", "instructions": ["Kick up to handstand", "Balance without support", "Hold for time"], "common_mistakes": ["Over-balancing", "Under-balancing", "Tense shoulders"], "progression_order": 6},
        {"name": "90 Degree Push Up", "pillar": "Vertical Push", "skill_level": "Advanced", "description": "Push up with feet elevated to 90 degrees.", "instructions": ["Feet at chest height", "Lower head to ground", "Press back up"], "common_mistakes": ["Not going deep enough", "Losing form", "Too much elevation"], "progression_order": 7},
        
        # Vertical Push - Elite
        {"name": "One Arm Handstand", "pillar": "Vertical Push", "skill_level": "Elite", "description": "Ultimate balance skill on one arm.", "instructions": ["Shift weight to one arm", "Lift other arm", "Hold balance"], "common_mistakes": ["Insufficient two-arm base", "Poor weight distribution", "Rushing progression"], "progression_order": 8},
        {"name": "Planche", "pillar": "Vertical Push", "skill_level": "Elite", "description": "Horizontal body hold supported by arms.", "instructions": ["Lean forward from plank", "Lift feet off ground", "Hold horizontal position"], "common_mistakes": ["Insufficient lean", "Not engaging properly", "Poor progression"], "progression_order": 9},
        
        # Core - Beginner
        {"name": "Plank", "pillar": "Core", "skill_level": "Beginner", "description": "Basic core strengthening hold.", "instructions": ["Forearm position", "Keep body straight", "Hold for time"], "common_mistakes": ["Sagging hips", "Holding breath"], "progression_order": 1},
        {"name": "Foot Supported L-Sit", "pillar": "Core", "skill_level": "Beginner", "description": "L-sit with foot support for progression.", "instructions": ["Sit with legs extended", "Support weight on hands", "Lift hips slightly"], "common_mistakes": ["Not engaging arms", "Leaning back"], "progression_order": 2},
        {"name": "Tuck L-Sit", "pillar": "Core", "skill_level": "Beginner", "description": "L-sit with knees tucked to chest.", "instructions": ["Support on hands", "Tuck knees to chest", "Hold position"], "common_mistakes": ["Not lifting hips", "Rounding shoulders"], "progression_order": 3},
        
        # Core - Intermediate
        {"name": "L-Sit", "pillar": "Core", "skill_level": "Intermediate", "description": "Full L-sit with straight legs.", "instructions": ["Support on hands", "Lift legs to horizontal", "Keep legs straight"], "common_mistakes": ["Piking at hips", "Not pressing down"], "progression_order": 4},
        {"name": "V-Sit", "pillar": "Core", "skill_level": "Intermediate", "description": "Advanced core hold with legs elevated.", "instructions": ["Sit with hands by hips", "Lift legs high", "Balance on hands"], "common_mistakes": ["Not keeping legs together", "Rounding back"], "progression_order": 5},
        
        # Legs - Beginner
        {"name": "Assisted Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Squat with assistance for learning movement.", "instructions": ["Hold onto support", "Lower into squat", "Stand back up"], "common_mistakes": ["Knees caving in", "Not going deep enough"], "progression_order": 1},
        {"name": "Bodyweight Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Basic unassisted squat movement.", "instructions": ["Feet shoulder width", "Lower until thighs parallel", "Stand back up"], "common_mistakes": ["Forward lean", "Shallow depth"], "progression_order": 2},
        {"name": "Split Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Single leg squat variation.", "instructions": ["One foot forward", "Lower rear knee", "Push back up"], "common_mistakes": ["Forward lean", "Not dropping knee"], "progression_order": 3},
        
        # Legs - Intermediate
        {"name": "Pistol Squat", "pillar": "Legs", "skill_level": "Intermediate", "description": "Single leg squat to full depth.", "instructions": ["Stand on one leg", "Lower while extending other", "Stand back up"], "common_mistakes": ["Using momentum", "Not full depth"], "progression_order": 4},
        {"name": "Shrimp Squat", "pillar": "Legs", "skill_level": "Intermediate", "description": "Advanced single leg squat variation.", "instructions": ["Stand on one leg", "Grab rear foot", "Lower into squat"], "common_mistakes": ["Losing balance", "Not maintaining grab"], "progression_order": 5},
    ]
    
    for exercise_data in exercises_data:
        exercise = Exercise(**exercise_data)
        await db.exercises.insert_one(exercise.dict())

async def initialize_mobility_exercises():
    """Initialize mobility exercises"""
    
    existing_mobility = await db.mobility_exercises.count_documents({})
    if existing_mobility > 0:
        return
    
    mobility_data = [
        {"name": "Jefferson Curl", "area": "Spine", "description": "Slow spinal flexion exercise for back health", "instructions": ["Start standing tall", "Slowly curl spine vertebra by vertebra", "Return to start with control"], "benefits": ["Spinal mobility", "Posterior chain flexibility", "Back strength"], "hold_time": "30-60 seconds"},
        {"name": "Pancake Stretch", "area": "Hips", "description": "Forward fold stretch for hip flexibility", "instructions": ["Sit with legs wide", "Fold forward from hips", "Keep spine long"], "benefits": ["Hip flexibility", "Hamstring stretch", "Spinal mobility"], "hold_time": "1-2 minutes"},
        {"name": "Shoulder Dislocates", "area": "Shoulders", "description": "Shoulder mobility with resistance band", "instructions": ["Hold band wide", "Bring overhead and behind", "Return to front"], "benefits": ["Shoulder mobility", "Posture improvement", "Upper body flexibility"], "hold_time": "10-15 reps"},
        {"name": "Couch Stretch", "area": "Hip Flexors", "description": "Deep hip flexor stretch", "instructions": ["Rear foot elevated", "Lunge position", "Drive hips forward"], "benefits": ["Hip flexor length", "Posture improvement", "Lower back relief"], "hold_time": "1-2 minutes per side"},
        {"name": "Thoracic Extension", "area": "Thoracic Spine", "description": "Upper back extension exercise", "instructions": ["Foam roller at mid-back", "Hands behind head", "Extend over roller"], "benefits": ["Upper back mobility", "Posture improvement", "Breathing enhancement"], "hold_time": "30 seconds"},
    ]
    
    for mobility_data in mobility_data:
        mobility = MobilityExercise(**mobility_data)
        await db.mobility_exercises.insert_one(mobility.dict())

async def initialize_products():
    """Initialize shop products"""
    
    existing_products = await db.products.count_documents({})
    if existing_products > 0:
        return
    
    products_data = [
        {"name": "Parallettes", "description": "Wooden parallette bars for handstand and L-sit training", "price": 89.99, "category": "Equipment"},
        {"name": "Gymnastics Rings", "description": "Professional gymnastics rings with straps", "price": 59.99, "category": "Equipment"},
        {"name": "Resistance Bands Set", "description": "Complete set of resistance bands for strength training", "price": 39.99, "category": "Equipment"},
        {"name": "Pull-up Bar", "description": "Doorway pull-up bar for home workouts", "price": 29.99, "category": "Equipment"},
        {"name": "Yoga Mat", "description": "High-quality yoga mat for floor exercises", "price": 49.99, "category": "Accessories"},
        {"name": "Foam Roller", "description": "Muscle recovery foam roller", "price": 34.99, "category": "Recovery"},
    ]
    
    for product_data in products_data:
        product = Product(**product_data)
        await db.products.insert_one(product.dict())

# ========== AUTH ROUTES ==========

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        age=user_data.age,
        height=user_data.height,
        weight=user_data.weight,
        university=user_data.university,
        city=user_data.city
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return {"access_token": access_token, "token_type": "bearer", "user": user}

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user["id"]})
    return {"access_token": access_token, "token_type": "bearer", "user": User(**user)}

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# ========== EXERCISE ROUTES ==========

@api_router.get("/exercises")
async def get_exercises(pillar: Optional[str] = None, skill_level: Optional[str] = None):
    query = {}
    if pillar:
        query["pillar"] = pillar
    if skill_level:
        query["skill_level"] = skill_level
    
    exercises = await db.exercises.find(query).sort("progression_order", 1).to_list(1000)
    return [Exercise(**exercise) for exercise in exercises]

@api_router.get("/exercises/pillars")
async def get_pillars():
    pillars = await db.exercises.distinct("pillar")
    return {"pillars": pillars}

@api_router.get("/exercises/{exercise_id}")
async def get_exercise(exercise_id: str):
    exercise = await db.exercises.find_one({"id": exercise_id})
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    return Exercise(**exercise)

# ========== MOBILITY ROUTES ==========

@api_router.get("/mobility")
async def get_mobility_exercises():
    exercises = await db.mobility_exercises.find().to_list(1000)
    return [MobilityExercise(**exercise) for exercise in exercises]

@api_router.get("/mobility/{exercise_id}")
async def get_mobility_exercise(exercise_id: str):
    exercise = await db.mobility_exercises.find_one({"id": exercise_id})
    if not exercise:
        raise HTTPException(status_code=404, detail="Mobility exercise not found")
    return MobilityExercise(**exercise)

# ========== PROGRESS ROUTES ==========

@api_router.post("/progress")
async def log_progress(progress_data: UserProgress, current_user: User = Depends(get_current_user)):
    progress_data.user_id = current_user.id
    await db.user_progress.insert_one(progress_data.dict())
    
    # Award points for logging progress
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"points": 10}}
    )
    
    return progress_data

@api_router.get("/progress")
async def get_user_progress(current_user: User = Depends(get_current_user)):
    progress = await db.user_progress.find({"user_id": current_user.id}).sort("date", -1).to_list(1000)
    return [UserProgress(**p) for p in progress]

@api_router.get("/progress/{exercise_id}")
async def get_exercise_progress(exercise_id: str, current_user: User = Depends(get_current_user)):
    progress = await db.user_progress.find({
        "user_id": current_user.id,
        "exercise_id": exercise_id
    }).sort("date", 1).to_list(1000)
    return [UserProgress(**p) for p in progress]

# ========== WORKOUT ROUTES ==========

@api_router.post("/workouts")
async def create_workout(workout_data: Workout, current_user: User = Depends(get_current_user)):
    workout_data.user_id = current_user.id
    await db.workouts.insert_one(workout_data.dict())
    return workout_data

@api_router.get("/workouts")
async def get_user_workouts(current_user: User = Depends(get_current_user)):
    workouts = await db.workouts.find({"user_id": current_user.id}).sort("created_at", -1).to_list(1000)
    return [Workout(**w) for w in workouts]

# ========== SHOP ROUTES ==========

@api_router.get("/products")
async def get_products():
    products = await db.products.find().to_list(1000)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}")
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

# ========== COMMUNITY ROUTES ==========

@api_router.get("/communities")
async def get_communities():
    communities = await db.communities.find().to_list(1000)
    return [Community(**community) for community in communities]

@api_router.post("/communities/{community_id}/join")
async def join_community(community_id: str, current_user: User = Depends(get_current_user)):
    await db.communities.update_one(
        {"id": community_id},
        {"$addToSet": {"members": current_user.id}}
    )
    return {"message": "Joined community successfully"}

@api_router.get("/communities/{community_id}/messages")
async def get_community_messages(community_id: str):
    messages = await db.messages.find({"community_id": community_id}).sort("timestamp", -1).limit(50).to_list(50)
    return [Message(**message) for message in messages]

# ========== LEADERBOARD ROUTES ==========

@api_router.get("/leaderboard")
async def get_leaderboard():
    users = await db.users.find().sort("points", -1).limit(10).to_list(10)
    leaderboard = []
    for i, user in enumerate(users):
        leaderboard.append({
            "rank": i + 1,
            "username": user["username"],
            "points": user["points"],
            "university": user.get("university", ""),
            "city": user.get("city", "")
        })
    return leaderboard

# ========== WEBSOCKET ==========

@app.websocket("/ws/chat/{community_id}")
async def websocket_endpoint(websocket: WebSocket, community_id: str):
    await manager.connect(websocket, community_id)
    try:
        while True:
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Save message to database
            message = Message(
                user_id=message_data["user_id"],
                community_id=community_id,
                username=message_data["username"],
                content=message_data["content"]
            )
            await db.messages.insert_one(message.dict())
            
            # Broadcast to community
            await manager.broadcast_to_community(data, community_id)
    except WebSocketDisconnect:
        manager.disconnect(websocket, community_id)

# ========== FILE UPLOAD ==========

@api_router.post("/upload/profile-photo")
async def upload_profile_photo(file: UploadFile = File(...), current_user: User = Depends(get_current_user)):
    # Read file content
    content = await file.read()
    
    # Convert to base64
    base64_content = base64.b64encode(content).decode('utf-8')
    photo_data = f"data:{file.content_type};base64,{base64_content}"
    
    # Update user profile
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"profile_photo": photo_data}}
    )
    
    return {"photo_url": photo_data}

# ========== STARTUP EVENT ==========

@app.on_event("startup")
async def startup_event():
    await initialize_exercises()
    await initialize_mobility_exercises()
    await initialize_products()

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
