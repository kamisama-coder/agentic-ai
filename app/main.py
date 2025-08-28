from fastapi import FastAPI, Form, Request, Depends, status, Response, HTTPException, Query, Header
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import json
from fastapi.templating import Jinja2Templates
import threading
from sqlalchemy.orm import Session
from google import genai
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel
import database 
import secrets
from collections import defaultdict
import sqlite3
import hmac
import hashlib
from datetime import datetime, timedelta
import os
import time
import razorpay


app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
client = genai.Client(api_key='AIzaSyADvZjtVNSnOAnNUGJcMB1oWiC3ZgwAhFY')

def generate_token():
    return secrets.token_hex(32)  # 64-character secure token


class VerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

def check():
    while True:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()

        for it in rows:
            expiry_time = it[3]

            if expiry_time is not None and isinstance(expiry_time, str):
                expiry_time = datetime.fromisoformat(expiry_time)

            if expiry_time is None or datetime.utcnow() >= expiry_time:
                
                cursor.execute("UPDATE users SET created_at=?, paid=?, remaining_token=? WHERE id=?",
                               (datetime.utcnow() + timedelta(days=31), "no", 100, it[0]))

        conn.commit()
        conn.close()

        time.sleep(5)  
        

# Run in background thread
thread = threading.Thread(target=check, daemon=True)
thread.start()
    

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


save_id = None
       
session_data = {
    "roles": {},
    "arg_counts": {},
    "arg_names": defaultdict(dict) 
}

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=('rzp_test_R9HkZqqt7zcFbc','HDjWGyYijxIUzns4hVy8cuwd'))

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

SECRET_KEY = "hts5eh45w54hh46h46h66srd" 
COOKIE_NAME = "session"

serializer = URLSafeSerializer(SECRET_KEY)

def create_session(response: Response, user_id: int):
    session_data = {"user_id": user_id}
    session_token = serializer.dumps(session_data)
    response.set_cookie(
        key=COOKIE_NAME, 
        value=session_token, 
        httponly=True, 
        secure=False,  
        max_age=3600   
    )


def get_current_user(request: Request):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        session = serializer.loads(session_token, max_age=3600)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    user_id = session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid session data")
    return user_id   

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.get("/users")
def read_users(extraction_id: int = Depends(get_current_user)):
    global save_id
    save_id = extraction_id


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})

@app.get("/roles", response_class=HTMLResponse)
def roles_get(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "roles_msg": True})


@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "msg": None})


@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    response: Response, 
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    global save_id
    user = db.query(database.User).filter(database.User.username == username).first()
    if user:
        return templates.TemplateResponse(
            "register.html", {"request": request, "msg": "User already exists!"}
        )
    hashed_password = hash_password(password)
    new_user = database.User(username=username, hashed_password=hashed_password)
    new_user.remaining_token = 100 
    save_id = new_user.id
    create_session(response, new_user.id)
    db.add(new_user)
    db.commit()
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "msg": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    response: Response, 
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)

):
    user = db.query(database.User).filter(database.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "msg": "Invalid username or password"}
        )
    global save_id
    save_id = user.id
    create_session(response, user.id)
    if db.query(database.UserData).filter(database.UserData.user_id == user.id).first():
        return templates.TemplateResponse("home.html", {"request": request, "api_key":True})
    return templates.TemplateResponse("form.html", {"request": request, "username": username, "roles_msg":True})

@app.post("/roles", response_class=HTMLResponse)
def post_roles(request: Request, functions: str = Form(...), roles: str = Form(...)):
    """
    functions: comma-separated function names
    roles: comma-separated descriptions
    """
    func_list = [f.strip() for f in functions.split(",")]
    role_list = [r.strip() for r in roles.split(",")]
    session_data["roles"] = dict(zip(func_list, role_list))
    return templates.TemplateResponse("form.html", {"request": request, "functions": func_list, "arg_counts_msg": True})

@app.get("/arg_counts", response_class=HTMLResponse)
def post_arg_counts(request: Request):
    all_query_params = dict(request.query_params)
    session_data["arg_counts"] = {func: int(count) for func, count in all_query_params.items()}
    print(session_data)
    return templates.TemplateResponse("form.html", {"request": request, "functions": list(session_data["roles"].keys()), "arg_names_msg": True})

@app.get("/arg_names", response_class=HTMLResponse)
def post_arg_names(request: Request):
    all_query_params = dict(request.query_params)
    for func, names in all_query_params.items():
        for a in names.split(","):
            session_data["arg_names"][func][a.strip()] = {}
    print(session_data)
    return templates.TemplateResponse("form.html", {"request": request, "functions": list(session_data["roles"].keys()), "arg_meaning": True})


@app.get('/arg_roles',response_class=HTMLResponse)
def arg_functions(request: Request,db: Session = Depends(get_db)):
    all_query_params = dict(request.query_params)
    for func,role in all_query_params.items():
        for key in session_data['arg_names'][func]:
            for a in role.split(","):
                session_data['arg_names'][func][key]['role'] = a.strip()
    id: int = save_id
    json_data = json.dumps(session_data)
    stored_json = database.UserData(user_id=id, json_data=json_data)
    db.add(stored_json)
    db.commit()            
    return templates.TemplateResponse("home.html", {"request": request,"api_key": True})        
    
@app.post('/api_key',response_class=HTMLResponse)
def api_key(request: Request,db: Session = Depends(get_db), source: str = Form(None)):
    token = generate_token()
    id:int = save_id
    user_data = db.query(database.User).filter(database.User.id == id).first()
    user_data.api_key = token
    db.commit()  
    return templates.TemplateResponse("home.html", {"request": request, "api_key": True, "key":token})   

@app.get("/pay",response_class=HTMLResponse)
def pay(request: Request):
    return templates.TemplateResponse("payment.html", {"request": request})   
    
@app.post('/create-order',response_class=HTMLResponse)
def payment(amount:int):
    order = client.order.create({
    "amount": amount * 100,   # amount in paise (₹1000 = 1000*100)
    "currency": "INR",
    "payment_capture": "1"
})
    JSONResponse(content=order)

@app.post("/verify-payment",response_class=HTMLResponse)
def verify_payment(data: VerifyPayment, db: Session = Depends(get_db)
):
    generated_signature = hmac.new(
        RAZORPAY_KEY_SECRET.encode(),
        (data.razorpay_order_id + "|" + data.razorpay_payment_id).encode(),
        hashlib.sha256
    ).hexdigest()
    id:int = save_id
    if generated_signature == data.razorpay_signature:
        user = db.query(database.User).filter(database.User.id == id).first()
        
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        user.created_at = datetime.utcnow() + timedelta(days=31)
        user.remaining_token = 8000
        user.paid = "yes"

        db.commit()
        db.refresh(user)
        return json.dumps({"status":"success"})  

    else:
        db.rollback()  
        return json.dumps({"status":"failure"})  

@app.get('/decrease_token')
def decrease_token(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Missing token")
   
    token = authorization.split(" ")[1]
    user_data = db.query(database.User).filter(database.User.api_key == token).first()
    if not user_data:
        raise HTTPException(status_code=401, detail="Missing user")
    user_data.remaining_token = user_data.remaining_token - 1
    db.commit()


@app.get("/valid")
def valid(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Missing token")
   
    token = authorization.split(" ")[1]
    user_data = db.query(database.User).filter(database.User.api_key == token).first()
    if not user_data:
        return {"result":False}
    time_diff = user_data.created_at
    if time_diff is not None and isinstance(time_diff, str):
                time_diff = datetime.fromisoformat(time_diff)
    if time_diff > datetime.utcnow():
        if user_data.remaining_token == 0:
            return {'result':False}
  
    return {"result":True}

@app.get("/connect")
def view_data(
    db: Session = Depends(get_db),
    authorization: str = Header(None)
):
    if not authorization or not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Missing token")
    token = authorization.split(" ")[1]
    user_data = db.query(database.User).filter(database.User.api_key == token).first()
    if not user_data:
        raise HTTPException(status_code=404, detail="No data found for this user")
    
    data = db.query(database.UserData).filter(database.UserData.user_id == user_data.id).first()
    return json.loads(data.json_data)
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

