from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="Dominion Fitness API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
client = AsyncIOMotorClient(MONGO_URL)
db = client[os.getenv("DB_NAME", "dominion_db")]

# Security setup
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# WebSocket manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def broadcast(self, message: str, exclude: str = None):
        for client_id, connection in self.active_connections.items():
            if client_id != exclude:
                await connection.send_text(message)

manager = ConnectionManager()

# Models
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    age: Optional[int] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    university: Optional[str] = None
    city: Optional[str] = None

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: str
    created_at: datetime

class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class Exercise(BaseModel):
    id: str
    name: str
    description: str
    pillar: str
    skill_level: str
    progression_order: int
    video_url: Optional[str] = None
    tips: List[str]
    prerequisites: List[str]

class ProgressLog(BaseModel):
    id: str
    user_id: str
    exercise_id: str
    reps: int
    sets: int
    notes: Optional[str] = None
    date: datetime

class Community(BaseModel):
    id: str
    name: str
    description: str
    members_count: int
    created_at: datetime

class Product(BaseModel):
    id: str
    name: str
    description: str
    price: float
    image_url: str
    category: str
    in_stock: bool

class MobilityExercise(BaseModel):
    id: str
    name: str
    description: str
    target_areas: List[str]
    difficulty: str
    duration: int
    video_url: Optional[str] = None
    instructions: List[str]

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid authentication token")
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication token")

# Routes
@app.post("/api/auth/register", response_model=Token)
async def register(user: UserCreate):
    if await db.users.find_one({"email": user.email}):
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = pwd_context.hash(user.password)
    user_dict = user.dict()
    user_dict["password"] = hashed_password
    user_dict["created_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)
    user_dict["id"] = str(result.inserted_id)
    
    access_token = create_access_token({"sub": str(result.inserted_id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(**user_dict)
    }

@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"email": form_data.username})
    if not user or not pwd_context.verify(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token({"sub": str(user["_id"])})
    user["id"] = str(user["_id"])
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": User(**user)
    }

@app.get("/api/exercises", response_model=List[Exercise])
async def get_exercises(pillar: Optional[str] = None, skill_level: Optional[str] = None):
    query = {}
    if pillar:
        query["pillar"] = pillar
    if skill_level:
        query["skill_level"] = skill_level
    
    exercises = await db.exercises.find(query).to_list(length=100)
    return [Exercise(**exercise) for exercise in exercises]

@app.post("/api/progress", response_model=ProgressLog)
async def log_progress(progress: ProgressLog, current_user: User = Depends(get_current_user)):
    progress_dict = progress.dict()
    progress_dict["user_id"] = current_user.id
    result = await db.progress_logs.insert_one(progress_dict)
    progress_dict["id"] = str(result.inserted_id)
    return ProgressLog(**progress_dict)

@app.get("/api/progress", response_model=List[ProgressLog])
async def get_user_progress(current_user: User = Depends(get_current_user)):
    progress_logs = await db.progress_logs.find({"user_id": current_user.id}).to_list(length=100)
    return [ProgressLog(**log) for log in progress_logs]

@app.websocket("/api/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client {client_id}: {data}", exclude=client_id)
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        await manager.broadcast(f"Client {client_id} left the chat")

@app.get("/api/communities", response_model=List[Community])
async def get_communities():
    communities = await db.communities.find().to_list(length=100)
    return [Community(**community) for community in communities]

@app.get("/api/products", response_model=List[Product])
async def get_products(category: Optional[str] = None):
    query = {"category": category} if category else {}
    products = await db.products.find(query).to_list(length=100)
    return [Product(**product) for product in products]

@app.get("/api/mobility", response_model=List[MobilityExercise])
async def get_mobility_exercises(difficulty: Optional[str] = None):
    query = {"difficulty": difficulty} if difficulty else {}
    exercises = await db.mobility_exercises.find(query).to_list(length=100)
    return [MobilityExercise(**exercise) for exercise in exercises]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)