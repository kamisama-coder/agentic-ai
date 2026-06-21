from fastapi import FastAPI, Form, Request, Depends, status, Response, HTTPException, Query, Header, WebSocket
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
import json
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel
from . import database
import secrets
from collections import defaultdict
import sqlite3
import hmac
import hashlib
from datetime import datetime, timedelta
import os
import io
from fastapi.concurrency import run_in_threadpool 
import sys
from . import llm 
from contextlib import redirect_stdout, asynccontextmanager
import time
import razorpay

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.Base.metadata.create_all(bind=database.engine)
    yield

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def generate_token():
    return secrets.token_hex(32)  

def increase_time():
    return datetime.now() + timedelta(days=30)

def check_time(store_datetime):
    return datetime.now() > store_datetime   

class VerifyPayment(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def default_session():
    return {}

session_data = defaultdict(default_session)

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

client = razorpay.Client(auth=(RAZORPAY_KEY_ID,RAZORPAY_KEY_SECRET))

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

SECRET_KEY = os.getenv("SECRET_KEY")
COOKIE_NAME = "session"

serializer = URLSafeSerializer(SECRET_KEY)

def create_session(response: Response, user_id: int):
    session_data = {"user_id": user_id}
    session_token = serializer.dumps(session_data)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_token,
        httponly=True,
        secure=True,   
        max_age=3600
    )
    return response

def verify_session(request: Request):
    session_token = request.cookies.get(COOKIE_NAME)
    if not session_token:
        return None
    try:
        session = serializer.loads(session_token, max_age=3600)
    except Exception:
        return None
    return session.get("user_id")

def get_current_user(request: Request):
    user_id = verify_session(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

@app.get("/users")
def read_users(user_id: int = Depends(get_current_user)):
    return {"current_user": user_id}

@app.get("/add")
def add_function(request: Request):
    return templates.TemplateResponse("form.html", {"request": request, "roles_msg": True})

@app.get("/", response_class=HTMLResponse)
def home(request: Request, msg: str = Query(None)):
    user_id = verify_session(request)
    logged_in = user_id is not None
    api_key = False

    if logged_in:
        api_key = True

    return templates.TemplateResponse("home.html", {"request": request, "msg": msg, "logged_in": logged_in, "api_key": api_key})

@app.get("/register", response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "msg": None})

@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(database.User).filter(database.User.username == username).first()
    if user:
        return templates.TemplateResponse(
            "register.html", {"request": request, "msg": "User already exists!"}
        )

    hashed_password = hash_password(password)
    new_user = database.User(username=username, hashed_password=hashed_password)
    new_user.created_at = increase_time()

    db.add(new_user)
    db.commit()
    db.refresh(new_user) # ✅ get new_user.id after commit
    set = database.UserData(user_id=new_user.id,json_data=llm.database()) 
    db.add(set)
    db.commit()

    # create response and set cookie
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    create_session(resp, new_user.id)
    return resp

@app.get("/documentation", response_class=HTMLResponse)
def documentation(request: Request):
    return templates.TemplateResponse("documentation.html", {"request": request})


@app.get("/functions", response_class=HTMLResponse)
def documentation(request: Request):
    return templates.TemplateResponse("functions.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "msg": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(database.User).filter(database.User.username == username).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html", {"request": request, "msg": "Invalid username or password"}
        )

    # ✅ store session cookie
    resp: Response

    # Change to RedirectResponse to ensure cookie is set and then verified by the home route
    resp = RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

    create_session(resp, user.id)  
    return resp


@app.post("/roles", response_class=HTMLResponse,)
def post_roles(request: Request, function: str = Form(...), role: str = Form(...),return_type: str = Form(...),save_id: int = Depends(get_current_user)):
    """
    functions: comma-separated function names
    roles: comma-separated descriptions
    """
    func = function
    return_type = return_type
    role = role
    if func not in session_data[save_id]:
        session_data[save_id][func] = {}
    session_data[save_id][func]["return_type"] = return_type
    session_data[save_id][func]["role"] = role
    print(session_data)
    print(list(session_data[save_id].keys()))
    return templates.TemplateResponse("form.html", {"request": request, "functions": list(session_data[save_id].keys()), "arg_counts_msg": True})

@app.get("/arg_counts", response_class=HTMLResponse)
def post_arg_counts(request: Request,save_id: int = Depends(get_current_user)):
    all_query_params = dict(request.query_params)
    for func, count in all_query_params.items():
         session_data[save_id][func]["argument_count"] = count 
    print(session_data)
    print(list(session_data[save_id].keys()))
    return templates.TemplateResponse("form.html", {"request": request, "functions": list(session_data[save_id].keys()), "arg_names_msg": True})

@app.get("/arg_names", response_class=HTMLResponse)
def post_arg_names(request: Request,save_id: int = Depends(get_current_user)):
    all_query_params = dict(request.query_params)
    fink = list(session_data[save_id].keys())
    session_data[save_id][fink[0]]["args"] = {}
    for func, names in all_query_params.items():
        for a in names.split(","):
            session_data[save_id][func]['args'][a.strip()] = {}
    print(session_data)
    return templates.TemplateResponse("form.html", {"request": request, "functions": list(session_data[save_id].keys()), "arg_meaning": True})


@app.get('/arg_roles', response_class=HTMLResponse)
def arg_functions(
    request: Request,
    db: Session = Depends(get_db),
    save_id: int = Depends(get_current_user)
):
    all_query_params = dict(request.query_params)

    for func, role in all_query_params.items():

        role_list = [r.strip() for r in role.split(";")]

        
        for key, r in zip(session_data[save_id][func]['args'].keys(), role_list):
            session_data[save_id][func]['args'][key] = r

    user = db.query(database.UserData).filter(database.UserData.user_id == save_id).first()
    for key, value in session_data[save_id].items():
        save = user.json_data
        save = save['functions']
        save[key] = value
        user.json_data = save

    db.commit()

    del session_data[save_id]
    return templates.TemplateResponse("home.html", {"request": request, "api_key": True})    
    
@app.post('/api_key',response_class=HTMLResponse)
def api_key(request: Request,db: Session = Depends(get_db), source: str = Form(None),save_id: int = Depends(get_current_user)):
    token = generate_token()
    id:int = save_id
    user_data = db.query(database.User).filter(database.User.id == id).first()
    user_data.api_key = token
    db.commit()  
    return templates.TemplateResponse("home.html", {"request": request, "api_key": True, "key":token})   

@app.get("/pay",response_class=HTMLResponse)
def pay(request: Request):
    return templates.TemplateResponse("payment.html", {"request": request, "key_id": RAZORPAY_KEY_ID})

@app.post("/call")
async def call_api(request: Request, authorization: str = Header(None), x_gemini_api_key: str = Header(None)):
    if not authorization or not authorization.startswith("token "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization token")
    
    if not x_gemini_api_key:
        raise HTTPException(status_code=400, detail="Missing X-Gemini-API-Key header")
    
    token = authorization.split(" ")[1]

    try:
        params = await request.json()
        prompt = params['prompt']
        function_registry = params.get('function_registry', '')
        header_row = params.get('header_row', [])
    except (json.JSONDecodeError, KeyError) as e:
        raise HTTPException(status_code=400, detail=f"Invalid or missing parameters in request body: {e}")

    log_stream = io.StringIO()
    result = None

    def run_llm_logic():
            """Wrapper function for the synchronous LLM code."""
            with redirect_stdout(log_stream):
                controller = llm.creator(prompt, token, x_gemini_api_key, function_registry, header_row)
                return controller.get_output()

    result = await run_in_threadpool(run_llm_logic)

    logs = log_stream.getvalue().splitlines()

    return result

    
@app.post('/create-order',response_class=JSONResponse)
def payment(amount:int):
    order = client.order.create({
    "amount": amount * 100,  
    "currency": "INR",
    "payment_capture": "1"
})
    return JSONResponse(content=order)

@app.post("/verify-payment")
def verify_payment(data: VerifyPayment, db: Session = Depends(get_db),save_id: int = Depends(get_current_user)
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

        user.created_at = increase_time()

        db.commit()
        db.refresh(user)
        return JSONResponse(content={"status": "success"})

    else:
        db.rollback()  
        return JSONResponse(content={"status": "failure"}, status_code=400)

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
    if check_time(user_data.created_at):
        return {"result":False}    
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
    return json.dumps(data.json_data)
    
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

