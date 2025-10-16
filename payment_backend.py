"""
Complete Payment Structure Backend for YouTube Agent Web App
Built with FastAPI, SQLAlchemy, and Pydantic
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker, relationship
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
import os
from fastapi.responses import HTMLResponse


# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title="YouTube Agent Payment API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ==================== DATABASE SETUP ====================

SQLALCHEMY_DATABASE_URL = "sqlite:///./youtube_agent.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== ENUMS ====================

class TierLevel(str, Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class SubscriptionInterval(str, Enum):
    MONTHLY = "monthly"
    YEARLY = "yearly"

# ==================== DATABASE MODELS ====================

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    credits = relationship("CreditBalance", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    tier_level = Column(String, nullable=False)
    interval = Column(String, nullable=False)
    status = Column(String, default="active")
    start_date = Column(DateTime, default=datetime.utcnow)
    next_billing_date = Column(DateTime)
    user = relationship("User", back_populates="subscriptions")

class CreditBalance(Base):
    __tablename__ = 'credit_balances'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    total_credits = Column(Integer, default=0)
    used_credits = Column(Integer, default=0)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship("User", back_populates="credits")

class Transaction(Base):
    __tablename__ = 'transactions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    transaction_type = Column(String)
    amount = Column(Float)
    status = Column(String, default="completed")
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="transactions")

# ==================== PYDANTIC SCHEMAS ====================

class UserCreate(BaseModel):
    email: EmailStr
    username: str

class UserResponse(BaseModel):
    id: int
    email: str
    username: str
    created_at: datetime
    class Config:
        from_attributes = True

class SubscriptionCreate(BaseModel):
    user_id: int
    tier_level: TierLevel
    interval: SubscriptionInterval

class CreditPurchase(BaseModel):
    user_id: int
    package_name: str

# ==================== PRICING CONFIGURATION ====================

@dataclass
class SubscriptionTier:
    name: str
    level: TierLevel
    monthly_price: float
    yearly_price: float
    videos_per_month: int
    features: List[str]

    def get_price(self, interval: SubscriptionInterval):
        return self.monthly_price if interval == SubscriptionInterval.MONTHLY else self.yearly_price

@dataclass
class CreditPackage:
    name: str
    credits: int
    price: float
    bonus_credits: int = 0

    @property
    def total_credits(self):
        return self.credits + self.bonus_credits

class PaymentStructure:
    def __init__(self):
        self.subscription_tiers = {
            TierLevel.BASIC: SubscriptionTier("Basic Plan", TierLevel.BASIC, 29.99, 299.99, 50, ["Basic analytics"]),
            TierLevel.PRO: SubscriptionTier("Pro Plan", TierLevel.PRO, 79.99, 799.99, 200, ["Advanced analytics", "AI insights"]),
            TierLevel.ENTERPRISE: SubscriptionTier("Enterprise Plan", TierLevel.ENTERPRISE, 249.99, 2499.99, -1, ["Unlimited analytics"])
        }
        self.credit_packages = [
            CreditPackage("Starter Pack", 10, 9.99),
            CreditPackage("Creator Pack", 50, 39.99, 5),
            CreditPackage("Business Pack", 500, 299.99, 100),
        ]
    def export(self):
        return {
            "subscription_tiers": [vars(v) for v in self.subscription_tiers.values()],
            "credit_packages": [vars(v) for v in self.credit_packages]
        }

payment_structure = PaymentStructure()

# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    return {"message": "🚀 YouTube Payment API running successfully"}

@app.get("/api/pricing")
def get_pricing():
    return payment_structure.export()


@app.get("/pricing", response_class=HTMLResponse)
def serve_frontend():
    """Serve the payment frontend page"""
    with open("frontend/payment.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.post("/api/users", response_model=UserResponse)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter((User.email == user.email) | (User.username == user.username)).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    db_user = User(email=user.email, username=user.username)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/api/subscriptions")
def create_subscription(sub: SubscriptionCreate, db: Session = Depends(get_db)):
    user = db.query(User).get(sub.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    tier = payment_structure.subscription_tiers[sub.tier_level]
    next_billing = datetime.utcnow() + timedelta(days=30 if sub.interval == SubscriptionInterval.MONTHLY else 365)
    subscription = Subscription(user_id=user.id, tier_level=sub.tier_level, interval=sub.interval, next_billing_date=next_billing)
    db.add(subscription)
    db.commit()
    return {"message": f"{tier.name} subscription created", "next_billing": next_billing}

@app.post("/api/credits")
def buy_credits(purchase: CreditPurchase, db: Session = Depends(get_db)):
    user = db.query(User).get(purchase.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    package = next((p for p in payment_structure.credit_packages if p.name == purchase.package_name), None)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    balance = db.query(CreditBalance).filter(CreditBalance.user_id == user.id).first()
    if not balance:
        balance = CreditBalance(user_id=user.id)
        db.add(balance)
    balance.total_credits += package.total_credits
    transaction = Transaction(user_id=user.id, transaction_type="credits", amount=package.price, description=package.name)
    db.add(transaction)
    db.commit()
    return {"message": f"Purchased {package.total_credits} credits", "total_credits": balance.total_credits}

# ==================== STARTUP ====================

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully!")
    with open("static/pricing_config.json", "w") as f:
        json.dump(payment_structure.export(), f, indent=2)
    print("💾 Pricing config exported to static/pricing_config.json")

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("payment_backend:app", host="0.0.0.0", port=8000, reload=True)
