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
    interests: List[str] = []
    fitness_level: str = "Beginner"
    points: int = 0
    badges: List[str] = []
    achievements: List[Dict[str, Any]] = []
    streak_count: int = 0
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    following: List[str] = []
    followers: List[str] = []
    privacy_settings: Dict[str, bool] = Field(default={"profile_public": True, "progress_public": True})
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

class MobilityAssessment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    assessment_type: str  # overhead_squat, shoulder_reach, ankle_dorsiflexion
    score: int  # 0-3 scoring system
    notes: Optional[str] = None
    areas_of_concern: List[str] = []
    recommendations: List[str] = []
    date_taken: datetime = Field(default_factory=datetime.utcnow)

class Challenge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    type: str  # weekly, monthly, community
    goal_type: str  # reps, time, consistency
    goal_value: int
    start_date: datetime
    end_date: datetime
    participants: List[str] = []
    rewards: List[str] = []
    created_by: str
    status: str = "active"  # active, completed, cancelled

class Achievement(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    category: str  # strength, consistency, social, mobility
    criteria: Dict[str, Any]  # Requirements to unlock
    badge_icon: str
    points_reward: int
    rarity: str = "common"  # common, rare, epic, legendary

class UserConnection(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    follower_id: str
    following_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ChatChannel(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    type: str  # general, workout_chat, mobility_chat, beginner_help
    community_id: Optional[str] = None
    members: List[str] = []
    moderators: List[str] = []
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
        
        # Core - Advanced
        {"name": "Human Flag", "pillar": "Core", "skill_level": "Advanced", "description": "Horizontal body hold using vertical pole.", "instructions": ["Grip vertical pole", "Lift body horizontal", "Hold flag position"], "common_mistakes": ["Not engaging enough", "Poor grip position", "Insufficient strength"], "progression_order": 6},
        {"name": "Dragon Flag", "pillar": "Core", "skill_level": "Advanced", "description": "Full body lever on bench or bar.", "instructions": ["Lie on bench", "Grip behind head", "Lift entire body straight"], "common_mistakes": ["Piking at hips", "Not keeping rigid", "Poor control"], "progression_order": 7},
        
        # Core - Elite
        {"name": "Front Lever", "pillar": "Core", "skill_level": "Elite", "description": "Horizontal body hold facing down.", "instructions": ["Dead hang position", "Lift body horizontal", "Keep perfectly straight"], "common_mistakes": ["Sagging hips", "Bent knees", "Insufficient lat strength"], "progression_order": 8},
        {"name": "Back Lever", "pillar": "Core", "skill_level": "Elite", "description": "Horizontal body hold facing up.", "instructions": ["Start in support", "Lower to horizontal", "Keep body straight"], "common_mistakes": ["Poor shoulder mobility", "Bent body", "Rushed progression"], "progression_order": 9},
        
        # Legs - Beginner
        {"name": "Assisted Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Squat with assistance for learning movement.", "instructions": ["Hold onto support", "Lower into squat", "Stand back up"], "common_mistakes": ["Knees caving in", "Not going deep enough"], "progression_order": 1},
        {"name": "Bodyweight Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Basic unassisted squat movement.", "instructions": ["Feet shoulder width", "Lower until thighs parallel", "Stand back up"], "common_mistakes": ["Forward lean", "Shallow depth"], "progression_order": 2},
        {"name": "Split Squat", "pillar": "Legs", "skill_level": "Beginner", "description": "Single leg squat variation.", "instructions": ["One foot forward", "Lower rear knee", "Push back up"], "common_mistakes": ["Forward lean", "Not dropping knee"], "progression_order": 3},
        
        # Legs - Advanced
        {"name": "Shrimp Squat", "pillar": "Legs", "skill_level": "Advanced", "description": "Advanced single leg squat with rear foot hold.", "instructions": ["Stand on one leg", "Grab rear foot behind", "Lower into deep squat"], "common_mistakes": ["Losing balance", "Not maintaining rear foot grip", "Insufficient flexibility"], "progression_order": 6},
        {"name": "Matrix Squat", "pillar": "Legs", "skill_level": "Advanced", "description": "Deep squat transitioning to matrix position.", "instructions": ["Deep squat position", "Lean back dramatically", "Touch ground with hands"], "common_mistakes": ["Poor ankle mobility", "Losing balance", "Not going deep enough"], "progression_order": 7},
        
        # Legs - Elite
        {"name": "Jump Squat to Pistol", "pillar": "Legs", "skill_level": "Elite", "description": "Explosive jump followed by pistol squat.", "instructions": ["Jump from deep squat", "Land in pistol position", "Control the descent"], "common_mistakes": ["Poor landing control", "Losing balance", "Insufficient power"], "progression_order": 8},
        {"name": "Weighted Pistol Squat", "pillar": "Legs", "skill_level": "Elite", "description": "Pistol squat with additional weight.", "instructions": ["Hold weight while performing pistol", "Maintain perfect form", "Full range of motion"], "common_mistakes": ["Too much weight too soon", "Compromising form", "Poor balance"], "progression_order": 9},
    ]
    
    for exercise_data in exercises_data:
        exercise = Exercise(**exercise_data)
        await db.exercises.insert_one(exercise.dict())

async def initialize_mobility_exercises():
    """Initialize comprehensive mobility system with assessments and routines"""
    
    existing_mobility = await db.mobility_exercises.count_documents({})
    if existing_mobility > 0:
        return
    
    # Mobility Assessments
    assessments_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Overhead Squat Assessment",
            "area": "Full Body",
            "type": "assessment",
            "description": "Comprehensive movement screen to evaluate whole-body mobility and stability",
            "instructions": [
                "Stand with feet shoulder-width apart",
                "Raise arms overhead with thumbs pointing back",
                "Squat down as deep as possible while keeping arms overhead",
                "Hold for 3 seconds and observe any compensations"
            ],
            "benefits": ["Identifies mobility restrictions", "Evaluates movement patterns", "Guides exercise selection"],
            "what_to_look_for": [
                "Arms falling forward - thoracic/shoulder mobility",
                "Knees caving in - hip/ankle mobility",
                "Heels lifting - ankle dorsiflexion restriction",
                "Forward lean - hip flexor tightness"
            ],
            "scoring": {
                "3": "Perfect squat with arms overhead",
                "2": "Minor compensation in one area",
                "1": "Multiple compensations present",
                "0": "Unable to perform movement"
            },
            "hold_time": "3 seconds",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Shoulder Reach Test",
            "area": "Shoulders",
            "type": "assessment",
            "description": "Assess shoulder flexibility and internal/external rotation",
            "instructions": [
                "Reach one arm overhead and down your back",
                "Reach other arm behind back and up",
                "Try to touch fingers behind your back",
                "Measure gap between fingertips"
            ],
            "benefits": ["Evaluates shoulder mobility", "Identifies rotation restrictions", "Tracks improvement"],
            "what_to_look_for": [
                "Gap between fingers indicates tightness",
                "Compare both sides for asymmetry",
                "Note any pain or discomfort"
            ],
            "scoring": {
                "3": "Fingers overlap behind back",
                "2": "Fingertips touch",
                "1": "Gap less than 2 inches",
                "0": "Gap greater than 2 inches"
            },
            "hold_time": "5 seconds",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ankle Dorsiflexion Test",
            "area": "Ankles",
            "type": "assessment",
            "description": "Evaluate ankle mobility for proper squat depth and balance",
            "instructions": [
                "Stand facing a wall in lunge position",
                "Place front foot 4 inches from wall",
                "Keep heel down and knee straight",
                "Try to touch knee to wall without lifting heel"
            ],
            "benefits": ["Tests ankle flexibility", "Predicts squat performance", "Identifies restrictions"],
            "what_to_look_for": [
                "Heel lifting off ground",
                "Knee unable to reach wall",
                "Arch collapsing inward"
            ],
            "scoring": {
                "3": "Knee easily touches wall",
                "2": "Knee barely touches wall",
                "1": "Knee 1 inch from wall",
                "0": "Knee more than 1 inch from wall"
            },
            "hold_time": "3 seconds",
            "created_at": datetime.utcnow()
        }
    ]
    
    # Dynamic Mobility Routines
    routines_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "Morning Mobility Flow",
            "area": "Full Body",
            "type": "routine",
            "description": "Energizing 10-minute routine to start your day with improved mobility",
            "duration": "10 minutes",
            "difficulty": "Beginner",
            "exercises": [
                "Cat-Cow Stretch", "World's Greatest Stretch", "Leg Swings", 
                "Arm Circles", "Hip Circles", "Spinal Waves"
            ],
            "instructions": ["Perform each exercise for 30-60 seconds", "Move slowly and controlled", "Focus on breath"],
            "benefits": ["Increases circulation", "Prepares body for activity", "Reduces stiffness"],
            "best_time": "Morning or pre-workout",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Desk Worker Relief",
            "area": "Neck, Shoulders, Hips",
            "type": "routine",
            "description": "Combat the effects of prolonged sitting with targeted stretches",
            "duration": "8 minutes",
            "difficulty": "Beginner",
            "exercises": [
                "Neck Rolls", "Shoulder Blade Squeezes", "Hip Flexor Stretch",
                "Thoracic Extension", "Seated Spinal Twist"
            ],
            "instructions": ["Can be done at desk or standing", "Hold stretches for 30 seconds", "Repeat 2-3 times daily"],
            "benefits": ["Reduces neck tension", "Opens tight hips", "Improves posture"],
            "best_time": "During work breaks",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pre-Workout Dynamic Warmup",
            "area": "Full Body",
            "type": "routine",
            "description": "Dynamic movements to prepare your body for intense training",
            "duration": "12 minutes",
            "difficulty": "Intermediate",
            "exercises": [
                "Walking High Knees", "Butt Kicks", "Leg Swings", "Arm Swings",
                "Walking Lunges", "Inchworms", "Dynamic Pigeon"
            ],
            "instructions": ["Keep movements controlled", "Gradually increase range of motion", "Focus on activation"],
            "benefits": ["Increases body temperature", "Activates muscles", "Prevents injury"],
            "best_time": "Before workouts",
            "created_at": datetime.utcnow()
        }
    ]
    
    # Enhanced Individual Mobility Exercises
    exercises_data = [
        {
            "id": str(uuid.uuid4()),
            "name": "World's Greatest Stretch",
            "area": "Hips, Ankles, Thoracic",
            "type": "exercise",
            "description": "The most comprehensive single stretch for lower body mobility",
            "instructions": [
                "Start in lunge position with hands on ground",
                "Drop back knee to ground",
                "Place inside elbow to front ankle",
                "Rotate opposite arm toward ceiling",
                "Hold and breathe deeply"
            ],
            "benefits": ["Opens hip flexors", "Stretches IT band", "Improves thoracic rotation", "Enhances ankle mobility"],
            "targets": ["Hip flexors", "IT band", "Thoracic spine", "Ankle dorsiflexion"],
            "common_mistakes": ["Dropping into stretch too quickly", "Not maintaining front knee alignment", "Holding breath"],
            "progressions": [
                "Beginner: Hold static position",
                "Intermediate: Add gentle rocking",
                "Advanced: Add posterior reach"
            ],
            "contraindications": ["Recent hip surgery", "Acute lower back pain"],
            "hold_time": "30-60 seconds each side",
            "video_url": "placeholder_for_worlds_greatest_stretch",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Thoracic Spine Cat-Cow",
            "area": "Thoracic Spine",
            "type": "exercise",
            "description": "Improve upper back mobility and posture with controlled spinal movement",
            "instructions": [
                "Start on hands and knees",
                "Arch your back and look up (cow)",
                "Round your spine and tuck chin (cat)",
                "Move slowly between positions",
                "Focus on mid-back movement"
            ],
            "benefits": ["Increases spinal mobility", "Reduces upper back tension", "Improves posture", "Relieves stiffness"],
            "targets": ["Thoracic vertebrae", "Spinal erectors", "Deep core muscles"],
            "common_mistakes": ["Moving too fast", "Using only lower back", "Not breathing with movement"],
            "progressions": [
                "Beginner: Gentle range of motion",
                "Intermediate: Hold end positions",
                "Advanced: Add side bending"
            ],
            "contraindications": ["Acute spinal injury", "Recent back surgery"],
            "hold_time": "10-15 slow repetitions",
            "video_url": "placeholder_for_cat_cow",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "90/90 Hip Stretch",
            "area": "Hips",
            "type": "exercise", 
            "description": "Target both internal and external hip rotation simultaneously",
            "instructions": [
                "Sit with both legs bent at 90 degrees",
                "Front leg in external rotation",
                "Back leg in internal rotation",
                "Lean forward over front leg",
                "Switch sides after hold"
            ],
            "benefits": ["Improves hip internal rotation", "Increases external rotation", "Balances hip mobility", "Reduces hip tightness"],
            "targets": ["Hip internal rotators", "Hip external rotators", "Hip capsule"],
            "common_mistakes": ["Sitting on one hip", "Forcing the stretch", "Not maintaining spine alignment"],
            "progressions": [
                "Beginner: Sit upright",
                "Intermediate: Gentle forward lean", 
                "Advanced: Deep forward fold"
            ],
            "contraindications": ["Hip replacement", "Acute hip pain"],
            "hold_time": "45-90 seconds each side",
            "video_url": "placeholder_for_90_90_hip",
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Ankle ABC's",
            "area": "Ankles",
            "type": "exercise",
            "description": "Improve ankle mobility in all directions through alphabet tracing",
            "instructions": [
                "Sit or lie down comfortably",
                "Lift one foot off ground",
                "Trace the alphabet with your big toe",
                "Make large, controlled movements",
                "Complete full alphabet each foot"
            ],
            "benefits": ["Increases ankle range of motion", "Improves circulation", "Strengthens small muscles", "Prevents stiffness"],
            "targets": ["Ankle dorsiflexors", "Ankle plantarflexors", "Ankle invertors", "Ankle evertors"],
            "common_mistakes": ["Moving too quickly", "Making letters too small", "Using whole leg instead of ankle"],
            "progressions": [
                "Beginner: Capital letters only",
                "Intermediate: Upper and lowercase",
                "Advanced: Cursive or backwards"
            ],
            "contraindications": ["Recent ankle injury", "Acute ankle sprain"],
            "hold_time": "2-3 minutes each foot",
            "video_url": "placeholder_for_ankle_abcs",
            "created_at": datetime.utcnow()
        }
    ]
    
    # Insert all data
    for assessment in assessments_data:
        await db.mobility_exercises.insert_one(assessment)
    
    for routine in routines_data:
        await db.mobility_exercises.insert_one(routine)
        
    for exercise in exercises_data:
        await db.mobility_exercises.insert_one(exercise)

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

async def initialize_achievements():
    """Initialize achievement system"""
    
    existing_achievements = await db.achievements.count_documents({})
    if existing_achievements > 0:
        return
    
    achievements_data = [
        {
            "name": "First Steps",
            "description": "Complete your first workout",
            "category": "strength",
            "criteria": {"workouts_completed": 1},
            "badge_icon": "🎯",
            "points_reward": 50,
            "rarity": "common"
        },
        {
            "name": "Consistency Champion",
            "description": "Log workouts for 7 consecutive days",
            "category": "consistency",
            "criteria": {"streak_days": 7},
            "badge_icon": "🔥",
            "points_reward": 200,
            "rarity": "rare"
        },
        {
            "name": "Mobility Master",
            "description": "Complete 5 mobility assessments",
            "category": "mobility",
            "criteria": {"assessments_completed": 5},
            "badge_icon": "🧘",
            "points_reward": 150,
            "rarity": "rare"
        },
        {
            "name": "Social Butterfly",
            "description": "Follow 10 other users",
            "category": "social",
            "criteria": {"following_count": 10},
            "badge_icon": "🦋",
            "points_reward": 100,
            "rarity": "common"
        },
        {
            "name": "Legendary Warrior",
            "description": "Reach 5000 points",
            "category": "strength",
            "criteria": {"total_points": 5000},
            "badge_icon": "⚡",
            "points_reward": 500,
            "rarity": "legendary"
        }
    ]
    
    for achievement_data in achievements_data:
        achievement = Achievement(**achievement_data)
        await db.achievements.insert_one(achievement.dict())

async def initialize_challenges():
    """Initialize challenges"""
    
    existing_challenges = await db.challenges.count_documents({})
    if existing_challenges > 0:
        return
    
    now = datetime.utcnow()
    week_later = now + timedelta(days=7)
    month_later = now + timedelta(days=30)
    
    challenges_data = [
        {
            "name": "Weekly Push-up Challenge",
            "description": "Complete 100 push-ups this week",
            "type": "weekly",
            "goal_type": "reps",
            "goal_value": 100,
            "start_date": now,
            "end_date": week_later,
            "rewards": ["Weekly Champion Badge", "200 points"],
            "created_by": "system"
        },
        {
            "name": "Daily Mobility Quest",
            "description": "Complete mobility exercises for 7 consecutive days",
            "type": "weekly",
            "goal_type": "consistency",
            "goal_value": 7,
            "start_date": now,
            "end_date": week_later,
            "rewards": ["Mobility Master Badge", "150 points"],
            "created_by": "system"
        },
        {
            "name": "30-Day Transformation",
            "description": "Log progress every day for 30 days",
            "type": "monthly",
            "goal_type": "consistency",
            "goal_value": 30,
            "start_date": now,
            "end_date": month_later,
            "rewards": ["Transformation Champion", "500 points"],
            "created_by": "system"
        }
    ]
    
    for challenge_data in challenges_data:
        challenge = Challenge(**challenge_data)
        await db.challenges.insert_one(challenge.dict())

async def initialize_chat_channels():
    """Initialize chat channels"""
    
    existing_channels = await db.chat_channels.count_documents({})
    if existing_channels > 0:
        return
    
    channels_data = [
        {
            "name": "General Discussion",
            "description": "General fitness discussion and motivation",
            "type": "general"
        },
        {
            "name": "Workout Chat",
            "description": "Share your workouts and get feedback",
            "type": "workout_chat"
        },
        {
            "name": "Mobility & Recovery",
            "description": "Discuss mobility, stretching, and recovery",
            "type": "mobility_chat"
        },
        {
            "name": "Beginner Help",
            "description": "Questions and support for beginners",
            "type": "beginner_help"
        },
        {
            "name": "Advanced Training",
            "description": "Advanced techniques and challenges",
            "type": "advanced_training"
        }
    ]
    
    for channel_data in channels_data:
        channel = ChatChannel(**channel_data)
        await db.chat_channels.insert_one(channel.dict())

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
    # Get real users first
    users = await db.users.find().sort("points", -1).limit(10).to_list(10)
    leaderboard = []
    
    # Add real users to leaderboard
    for i, user in enumerate(users):
        leaderboard.append({
            "rank": i + 1,
            "username": user["username"],
            "points": user["points"],
            "university": user.get("university", ""),
            "city": user.get("city", "")
        })
    
    # Fill remaining spots with sample Indian users if needed
    sample_users = [
        {"username": "arjun_warrior", "points": 2850, "university": "IIT Delhi", "city": "New Delhi"},
        {"username": "priya_fitness", "points": 2720, "university": "IIT Bombay", "city": "Mumbai"},
        {"username": "raj_calisthenics", "points": 2645, "university": "IIT Madras", "city": "Chennai"},
        {"username": "kavya_strength", "points": 2580, "university": "IIT Kanpur", "city": "Kanpur"},
        {"username": "rohit_beast", "points": 2495, "university": "IIT Kharagpur", "city": "Kharagpur"},
        {"username": "sneha_moves", "points": 2420, "university": "BITS Pilani", "city": "Pilani"},
        {"username": "vikram_elite", "points": 2350, "university": "IIT Roorkee", "city": "Roorkee"},
        {"username": "ananya_power", "points": 2275, "university": "Delhi University", "city": "Delhi"},
        {"username": "karan_muscle", "points": 2190, "university": "NIT Trichy", "city": "Tiruchirappalli"},
        {"username": "riya_champion", "points": 2105, "university": "Pune University", "city": "Pune"},
        {"username": "aarav_legend", "points": 2020, "university": "IIT Guwahati", "city": "Guwahati"},
        {"username": "isha_ninja", "points": 1945, "university": "Jadavpur University", "city": "Kolkata"},
        {"username": "dev_titan", "points": 1870, "university": "IIIT Hyderabad", "city": "Hyderabad"},
        {"username": "pooja_strong", "points": 1795, "university": "Manipal University", "city": "Manipal"},
        {"username": "harsh_alpha", "points": 1720, "university": "VIT Vellore", "city": "Vellore"}
    ]
    
    # Add sample users to fill the leaderboard
    current_rank = len(leaderboard) + 1
    for sample in sample_users:
        if len(leaderboard) >= 15:  # Limit to top 15
            break
        leaderboard.append({
            "rank": current_rank,
            "username": sample["username"],
            "points": sample["points"],
            "university": sample["university"],
            "city": sample["city"]
        })
        current_rank += 1
    
    return leaderboard

# ========== ENHANCED MOBILITY ROUTES ==========

@api_router.post("/mobility/assessments")
async def create_mobility_assessment(assessment: MobilityAssessment, current_user: User = Depends(get_current_user)):
    assessment.user_id = current_user.id
    await db.mobility_assessments.insert_one(assessment.dict())
    
    # Award points for assessment completion
    await db.users.update_one(
        {"id": current_user.id},
        {"$inc": {"points": 50}}
    )
    
    return assessment

@api_router.get("/mobility/assessments")
async def get_user_mobility_assessments(current_user: User = Depends(get_current_user)):
    assessments = await db.mobility_assessments.find({"user_id": current_user.id}).sort("date_taken", -1).to_list(1000)
    return [MobilityAssessment(**assessment) for assessment in assessments]

@api_router.get("/mobility/assessments/latest")
async def get_latest_mobility_assessment(current_user: User = Depends(get_current_user)):
    assessment = await db.mobility_assessments.find_one(
        {"user_id": current_user.id},
        sort=[("date_taken", -1)]
    )
    if not assessment:
        return None
    return MobilityAssessment(**assessment)

@api_router.get("/mobility/recommendations")
async def get_mobility_recommendations(current_user: User = Depends(get_current_user)):
    # Get latest assessment
    latest_assessment = await db.mobility_assessments.find_one(
        {"user_id": current_user.id},
        sort=[("date_taken", -1)]
    )
    
    if not latest_assessment:
        # Return general mobility exercises for beginners
        exercises = await db.mobility_exercises.find({"difficulty": "Beginner"}).to_list(5)
        return {
            "message": "Complete a mobility assessment to get personalized recommendations",
            "general_exercises": [MobilityExercise(**ex) for ex in exercises]
        }
    
    # Get recommended exercises based on assessment
    recommendations = []
    for area in latest_assessment.get("areas_of_concern", []):
        exercises = await db.mobility_exercises.find({"target_areas": area}).limit(3).to_list(3)
        recommendations.extend(exercises)
    
    return {
        "assessment_based": True,
        "recommended_exercises": [MobilityExercise(**ex) for ex in recommendations[:6]]
    }

# ========== ENHANCED SOCIAL FEATURES ==========

@api_router.post("/users/follow/{user_id}")
async def follow_user(user_id: str, current_user: User = Depends(get_current_user)):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")
    
    # Check if user exists
    target_user = await db.users.find_one({"id": user_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create connection
    connection = UserConnection(follower_id=current_user.id, following_id=user_id)
    await db.user_connections.insert_one(connection.dict())
    
    # Update user following/followers lists
    await db.users.update_one(
        {"id": current_user.id},
        {"$addToSet": {"following": user_id}}
    )
    await db.users.update_one(
        {"id": user_id},
        {"$addToSet": {"followers": current_user.id}}
    )
    
    return {"message": "Successfully followed user"}

@api_router.delete("/users/unfollow/{user_id}")
async def unfollow_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Remove connection
    await db.user_connections.delete_one({
        "follower_id": current_user.id,
        "following_id": user_id
    })
    
    # Update user following/followers lists
    await db.users.update_one(
        {"id": current_user.id},
        {"$pull": {"following": user_id}}
    )
    await db.users.update_one(
        {"id": user_id},
        {"$pull": {"followers": current_user.id}}
    )
    
    return {"message": "Successfully unfollowed user"}

@api_router.get("/users/search")
async def search_users(q: str = "", interests: str = "", current_user: User = Depends(get_current_user)):
    query = {}
    
    if q:
        query["$or"] = [
            {"username": {"$regex": q, "$options": "i"}},
            {"full_name": {"$regex": q, "$options": "i"}}
        ]
    
    if interests:
        interest_list = interests.split(",")
        query["interests"] = {"$in": interest_list}
    
    # Exclude current user
    query["id"] = {"$ne": current_user.id}
    
    users = await db.users.find(query).limit(20).to_list(20)
    return [{
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "profile_photo": user.get("profile_photo"),
        "interests": user.get("interests", []),
        "fitness_level": user.get("fitness_level", "Beginner"),
        "points": user.get("points", 0)
    } for user in users]

@api_router.get("/users/{user_id}/profile")
async def get_user_profile(user_id: str, current_user: User = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check privacy settings
    if user_id != current_user.id and not user.get("privacy_settings", {}).get("profile_public", True):
        raise HTTPException(status_code=403, detail="Profile is private")
    
    # Get user's recent progress (if public)
    recent_progress = []
    if user_id == current_user.id or user.get("privacy_settings", {}).get("progress_public", True):
        progress = await db.user_progress.find({"user_id": user_id}).sort("date", -1).limit(5).to_list(5)
        recent_progress = [UserProgress(**p) for p in progress]
    
    return {
        "id": user["id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "profile_photo": user.get("profile_photo"),
        "interests": user.get("interests", []),
        "fitness_level": user.get("fitness_level", "Beginner"),
        "points": user.get("points", 0),
        "badges": user.get("badges", []),
        "achievements": user.get("achievements", []),
        "streak_count": user.get("streak_count", 0),
        "followers_count": len(user.get("followers", [])),
        "following_count": len(user.get("following", [])),
        "is_following": current_user.id in user.get("followers", []),
        "recent_progress": recent_progress
    }

# ========== CHALLENGES & GAMIFICATION ==========

@api_router.get("/challenges")
async def get_active_challenges():
    now = datetime.utcnow()
    challenges = await db.challenges.find({
        "status": "active",
        "start_date": {"$lte": now},
        "end_date": {"$gte": now}
    }).to_list(1000)
    return [Challenge(**challenge) for challenge in challenges]

@api_router.post("/challenges/{challenge_id}/join")
async def join_challenge(challenge_id: str, current_user: User = Depends(get_current_user)):
    challenge = await db.challenges.find_one({"id": challenge_id})
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if current_user.id in challenge.get("participants", []):
        raise HTTPException(status_code=400, detail="Already participating in this challenge")
    
    await db.challenges.update_one(
        {"id": challenge_id},
        {"$addToSet": {"participants": current_user.id}}
    )
    
    return {"message": "Successfully joined challenge"}

@api_router.get("/achievements")
async def get_available_achievements():
    achievements = await db.achievements.find().to_list(1000)
    return [Achievement(**achievement) for achievement in achievements]

@api_router.get("/users/{user_id}/achievements")
async def get_user_achievements(user_id: str):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user.get("achievements", [])

# ========== CHAT CHANNELS ==========

@api_router.get("/chat/channels")
async def get_chat_channels():
    channels = await db.chat_channels.find().to_list(1000)
    return [ChatChannel(**channel) for channel in channels]

@api_router.post("/chat/channels/{channel_id}/join")
async def join_chat_channel(channel_id: str, current_user: User = Depends(get_current_user)):
    await db.chat_channels.update_one(
        {"id": channel_id},
        {"$addToSet": {"members": current_user.id}}
    )
    return {"message": "Joined channel successfully"}

@api_router.get("/chat/channels/{channel_id}/messages")
async def get_channel_messages(channel_id: str, limit: int = 50):
    messages = await db.messages.find({"community_id": channel_id}).sort("timestamp", -1).limit(limit).to_list(limit)
    return [Message(**message) for message in messages]

# ========== ENHANCED ANALYTICS ==========

@api_router.get("/analytics/progress")
async def get_progress_analytics(current_user: User = Depends(get_current_user)):
    # Get progress for last 30 days
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    progress = await db.user_progress.find({
        "user_id": current_user.id,
        "date": {"$gte": thirty_days_ago}
    }).sort("date", 1).to_list(1000)
    
    # Calculate streaks and trends
    workout_days = set()
    exercise_counts = {}
    
    for p in progress:
        workout_days.add(p["date"].date())
        exercise_id = p["exercise_id"]
        exercise_counts[exercise_id] = exercise_counts.get(exercise_id, 0) + 1
    
    return {
        "total_workouts": len(progress),
        "unique_workout_days": len(workout_days),
        "most_practiced_exercises": sorted(exercise_counts.items(), key=lambda x: x[1], reverse=True)[:5],
        "current_streak": current_user.streak_count,
        "weekly_progress": len([p for p in progress if (datetime.utcnow() - p["date"]).days <= 7])
    }

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
    await initialize_achievements()
    await initialize_challenges()
    await initialize_chat_channels()

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
