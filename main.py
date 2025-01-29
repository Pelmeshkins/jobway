from fastapi import FastAPI, Depends, HTTPException, status, Request, Form, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, sessionmaker
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from models import User, Post
from schemas import UserCreate, UserOut
from auth import get_password_hash, create_access_token, verify_password, get_current_user
from sqlalchemy import create_engine
from models import Base
from fastapi.responses import JSONResponse
from typing import Optional, List

from fastapi.responses import RedirectResponse

from fastapi import Cookie

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="templates/static"), name="static")
app.mount("/assets", StaticFiles(directory="templates/assets"), name="assets")



DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


# @app.get("/")
# def get_main_page(request: Request):
#     return templates.TemplateResponse("main.html", {"request": request})


@app.post("/register", response_model=UserOut)
def register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    is_admin: bool = Form(False)
):
    db: Session = SessionLocal()
    try:
        hashed_password = get_password_hash(password)
        db_user = User(username=username, password=hashed_password, is_admin=is_admin)

        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        return templates.TemplateResponse("login.html", {"request": request})
    finally:
        db.close()



@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()

        if not user or not verify_password(form_data.password, user.password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail="Incorrect username or password",
                                headers={"WWW-Authenticate": "Bearer"})

        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()


@app.get("/dashboard")
def dashboard(request: Request, access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    current_user = get_current_user(access_token.split(" ")[1])

    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == current_user).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})
    finally:
        db.close()


@app.get("/register")
def get_register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/login")
def get_login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/loginp")
def handle_login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()

        if not user or not verify_password(form_data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(data={"sub": user.username})

        redirect_response = RedirectResponse(url="/dashboard", status_code=302)
        redirect_response.set_cookie(key="access_token", value=f"Bearer {access_token}", httponly=True)

        return redirect_response
    finally:
        db.close()

@app.get("/logout")
def logout(response: Response):
    redirect_response = RedirectResponse(url="/login", status_code=302)
    redirect_response.delete_cookie(key="access_token")
    return redirect_response

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers,
    )

@app.get("/posts")
def get_posts(request: Request):
    db: Session = SessionLocal()
    try:
        posts = db.query(Post).all()
        return templates.TemplateResponse("posts.html", {"request": request, "posts": posts})
    finally:
        db.close()


@app.put("/posts/{post_id}")
def edit_post(post_id: int, title: str = Form(...), content: str = Form(...), access_token: str = Cookie(None)):
    current_user = get_current_user(access_token.split(" ")[1])

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access forbidden")

    db: Session = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        post.title = title
        post.content = content
        db.commit()
        return RedirectResponse(url="/dashboard", status_code=302)
    finally:
        db.close()


@app.delete("/posts/{post_id}")
def delete_post(post_id: int, access_token: str = Cookie(None)):
    current_user = get_current_user(access_token.split(" ")[1])

    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Access forbidden")

    db: Session = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        db.delete(post)
        db.commit()
        return RedirectResponse(url="/dashboard", status_code=302)
    finally:
        db.close()
