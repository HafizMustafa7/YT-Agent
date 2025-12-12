"""
Complete Payment Structure Backend for YouTube Agent Web App
Built with FastAPI, SQLAlchemy, and Pydantic
"""

from fastapi import FastAPI, HTTPException, Depends, status, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Session, sessionmaker, relationship, declarative_base
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
import json
import os
import hmac
import hashlib
from paddle_billing import Client, Environment, Options
from paddle_billing.Entities.Transaction import Transaction
from paddle_billing.Resources.Transactions.Operations import CreateTransaction
from paddle_billing.Entities.Shared import Money, CurrencyCode
import supabase_client

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
# Removed subscription-related enums - only credits now

# ==================== DATABASE MODELS ====================

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    credits = relationship("CreditBalance", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="user")



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

class CreditPurchase(BaseModel):
    user_id: int
    package_name: str

# ==================== PRICING CONFIGURATION ====================

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
        # Only credit packages - no subscriptions
        self.credit_packages = [
            CreditPackage("Starter Pack", 20, 15.00, 0),
            CreditPackage("Creator Pack", 60, 42.00, 0),
            CreditPackage("Professional Pack", 100, 70.00, 0),
        ]
        # Paddle Price ID mapping
        self.paddle_price_ids = {
            "Starter Pack": "pri_01kc4e4qnk16tcx6kpv4h7snr6",
            "Creator Pack": "pri_01kc4eckfdsjbpeh78zabv4rdm",
            "Professional Pack": "pri_01kc4ef3s5x2n53gcp4vangx9v",
        }
        self.api_costs = [
            {
                "api_name": "YouTube Data API",
                "cost_per_call": 0.01,
                "description": "Fetch video metadata, statistics, and channel information",
                "included_in_tiers": ["basic", "pro", "enterprise"]
            },
            {
                "api_name": "YouTube Analytics API",
                "cost_per_call": 0.02,
                "description": "Advanced analytics and reporting data",
                "included_in_tiers": ["pro", "enterprise"]
            },
            {
                "api_name": "OpenAI GPT-4 Analysis",
                "cost_per_call": 0.15,
                "description": "AI-powered content analysis and insights",
                "included_in_tiers": ["pro", "enterprise"]
            },
            {
                "api_name": "Sentiment Analysis API",
                "cost_per_call": 0.05,
                "description": "Analyze comments and audience sentiment",
                "included_in_tiers": ["pro", "enterprise"]
            },
            {
                "api_name": "Computer Vision API",
                "cost_per_call": 0.08,
                "description": "Thumbnail performance and visual analysis",
                "included_in_tiers": ["enterprise"]
            }
        ]
    
    def export(self):
        # Only export credit packages
        packages_list = []
        for pkg in self.credit_packages:
            pkg_dict = vars(pkg).copy()
            pkg_dict['total_credits'] = pkg.total_credits
            pkg_dict['price_per_credit'] = round(pkg.price / pkg.total_credits, 2)
            # Add validity days based on package
            if pkg.name == "Starter Pack":
                pkg_dict['validity_days'] = 90
            elif pkg.name == "Creator Pack":
                pkg_dict['validity_days'] = 180
            else:
                pkg_dict['validity_days'] = 365
            packages_list.append(pkg_dict)
        
        return {
            "credit_packages": packages_list
        }

payment_structure = PaymentStructure()

# ==================== STARTUP FUNCTION ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    Base.metadata.create_all(bind=engine)
    print("[OK] Database initialized successfully!")
    
    # Create static directory if it doesn't exist
    os.makedirs("static", exist_ok=True)
    
    with open("static/pricing_config.json", "w") as f:
        json.dump(payment_structure.export(), f, indent=2)
    print("[OK] Pricing config exported to static/pricing_config.json")
    yield
    # Shutdown (if needed)
    pass

# ==================== FASTAPI APP SETUP ====================

app = FastAPI(
    title="YouTube Agent Payment API",
    lifespan=lifespan
)

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

# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    return {"message": "YouTube Payment API running successfully"}

@app.get("/api/pricing")
def get_pricing():
    return payment_structure.export()

@app.get("/api/pricing/config")
def get_pricing_config():
    """Get full pricing configuration including API costs"""
    config = payment_structure.export()
    # Add API costs to the config
    config['api_costs'] = payment_structure.api_costs
    return config



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






# ==================== PADDLE INTEGRATION ====================
from dotenv import load_dotenv
load_dotenv()

# Paddle Configuration
PADDLE_API_KEY = os.getenv("PADDLE_API_KEY")
PADDLE_WEBHOOK_SECRET = os.getenv("PADDLE_WEBHOOK_SECRET")
PADDLE_ENVIRONMENT = os.getenv("PADDLE_ENVIRONMENT", "sandbox")  # 'sandbox' or 'production'

if not PADDLE_API_KEY:
    print("WARNING: PADDLE_API_KEY not set in environment variables")

# Initialize Paddle client
paddle_client = None
if PADDLE_API_KEY:
    env = Environment.SANDBOX if PADDLE_ENVIRONMENT == "sandbox" else Environment.PRODUCTION
    paddle_client = Client(PADDLE_API_KEY, options=Options(environment=env))

class PaddleCheckoutRequest(BaseModel):
    user_id: str
    package_name: str  # Required - only credit packages
    success_url: str = "http://localhost:5173/success"
    cancel_url: str = "http://localhost:5173/checkout"

@app.post("/api/paddle/create-checkout")
async def create_paddle_checkout(request: PaddleCheckoutRequest):
    """Create a Paddle checkout session"""
    
    print(f"\n{'='*60}")
    print(f"[CHECKOUT REQUEST] Received checkout request")
    print(f"User ID: {request.user_id}")
    print(f"Package: {request.package_name}")
    print(f"{'='*60}\n")
    
    if not paddle_client:
        error_msg = "Paddle client not initialized. Check PADDLE_API_KEY in .env file."
        print(f"[ERROR] {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)
    
    try:
        # Credit package purchase only
        print(f"[STEP 1] Looking up package '{request.package_name}' in Supabase...")
        package = await supabase_client.get_package_by_name(request.package_name)
        
        if not package:
            error_msg = f"Package '{request.package_name}' not found in Supabase packages table"
            print(f"[ERROR] {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        print(f"[SUCCESS] Package found: {package}")
        
        amount = float(package["price"])
        description = f"Credits: {package['name']}"
        package_id = package["id"]
        package_name = package["name"]
        
        # Get Paddle Price ID
        print(f"[STEP 2] Looking up Paddle Price ID for '{package_name}'...")
        price_id = payment_structure.paddle_price_ids.get(package_name)
        
        if not price_id:
            error_msg = f"Paddle Price ID not configured for package '{package_name}'. Check payment_backend.py paddle_price_ids mapping."
            print(f"[ERROR] {error_msg}")
            print(f"Available mappings: {payment_structure.paddle_price_ids}")
            raise HTTPException(status_code=404, detail=error_msg)
        
        print(f"[SUCCESS] Paddle Price ID: {price_id}")
        
        # Create order in Supabase with pending status
        print(f"[STEP 3] Creating order in Supabase...")
        
        order = await supabase_client.create_order(
            user_id=request.user_id,
            package_id=package_id,
            amount=amount,
            payment_method="paddle"
        )
        
        if not order:
            error_msg = "Failed to create order in Supabase. Check supabase_client.py logs for details."
            print(f"[ERROR] {error_msg}")
            raise HTTPException(status_code=500, detail=error_msg)
        
        print(f"[SUCCESS] Order created: ID={order['id']}")
        
        # KEY CHANGE: Create Transaction on Server Side
        print(f"[STEP 4] Creating Transaction with Paddle API...")
        try:
            transaction = paddle_client.transactions.create(
                items=[{
                    "price_id": price_id,
                    "quantity": 1
                }],
                custom_data={
                    "order_id": str(order["id"]),
                    "user_id": request.user_id,
                    "package_name": package_name
                },
                currency_code=CurrencyCode.USD,
                # Optional: Pass user details if available
                # customer_id=... 
            )
            
            print(f"[SUCCESS] Paddle Transaction Created!")
            print(f"Transaction ID: {transaction.id}")
            print(f"Status: {transaction.status}")
            
            # Return checkout data with transactionId for frontend
            checkout_data = {
                "transactionId": transaction.id,  # Start with lowercase for JS compat if needed, usually passed as transactionId
                "success_url": request.success_url,
                "cancel_url": request.cancel_url,
                # Legacy fields for debug/compat
                "price_id": price_id,
                "order_id": str(order["id"]),
                "amount": amount,
                "package_name": package_name
            }
            
            print(f"[STEP 5] Returning transaction ID to frontend")
            print(f"{'='*60}\n")
            
            return checkout_data

        except Exception as paddle_error:
            print(f"[PADDLE API ERROR] Failed to create transaction:")
            print(f"Error: {str(paddle_error)}")
            # Log full error for debug
            import traceback
            traceback.print_exc()
            
            # Revert order or mark as failed?
            # For now just fail
            raise HTTPException(status_code=400, detail=f"Paddle API Error: {str(paddle_error)}")
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"\n[CRITICAL ERROR] Unexpected error in create_paddle_checkout:")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        print(f"{'='*60}\n")
        raise HTTPException(status_code=500, detail=f"Failed to create checkout: {str(e)}")




@app.post("/api/paddle/webhook")
async def paddle_webhook(request: Request):
    """Handle Paddle webhook events"""
    
    try:
        # Get raw body for signature verification
        body = await request.body()
        signature = request.headers.get("Paddle-Signature")
        
        # Verify webhook signature
        if PADDLE_WEBHOOK_SECRET and signature:
            # Paddle signature format: ts=timestamp;h1=signature
            sig_parts = dict(part.split('=') for part in signature.split(';'))
            timestamp = sig_parts.get('ts', '')
            received_signature = sig_parts.get('h1', '')
            
            # Create expected signature
            signed_payload = f"{timestamp}:{body.decode()}"
            expected_signature = hmac.new(
                PADDLE_WEBHOOK_SECRET.encode(),
                signed_payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(received_signature, expected_signature):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        # Parse webhook data
        data = await request.json()
        event_type = data.get("event_type")
        
        print(f"Received Paddle webhook: {event_type}")
        
        # Handle transaction.completed event
        if event_type == "transaction.completed":
            transaction_data = data.get("data", {})
            transaction_id = transaction_data.get("id")
            status = transaction_data.get("status")
            custom_data = transaction_data.get("custom_data", {})
            order_id = custom_data.get("order_id")
            
            if status == "completed" and order_id:
                # Update order status in Supabase
                success = await supabase_client.update_order_status(
                    transaction_id=transaction_id,
                    status="completed"
                )
                
                if success:
                    print(f"Order {order_id} marked as completed")
                    # Credits will be added automatically by Supabase trigger
                else:
                    print(f"Failed to update order {order_id}")
        
        # Handle transaction.payment_failed event
        elif event_type == "transaction.payment_failed":
            transaction_data = data.get("data", {})
            transaction_id = transaction_data.get("id")
            custom_data = transaction_data.get("custom_data", {})
            order_id = custom_data.get("order_id")
            
            if order_id:
                await supabase_client.update_order_status(
                    transaction_id=transaction_id,
                    status="failed"
                )
                print(f"Order {order_id} marked as failed")
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==================== MAIN ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("payment_backend:app", host="127.0.0.1", port=8000, reload=True)

