from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from jose import JWTError, jwt

from database import get_db, create_tables
from models import Material, User
from crud import get_materials, get_material, create_material, delete_material, get_user_by_username, get_password_hash, verify_password
from auth import create_access_token, verify_token, SECRET_KEY, ALGORITHM

app = FastAPI(title="Сайт-визитка с БД")

# Создание таблиц при запуске
create_tables()

# Настройка шаблонов и статических файлов
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Создание администратора по умолчанию
def create_default_admin(db: Session):
    admin = get_user_by_username(db, "admin")
    if not admin:
        hashed_password = get_password_hash("password")
        db_admin = User(username="admin", password_hash=hashed_password)
        db.add(db_admin)
        db.commit()
        print("Создан администратор: admin/password")

@app.on_event("startup")
async def startup_event():
    db = next(get_db())
    try:
        create_default_admin(db)
    except Exception as e:
        print(f"Ошибка при создании администратора: {e}")
    finally:
        db.close()

# Функция для проверки JWT токена из cookie
async def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None
    
    username = verify_token(token)
    if not username:
        return None
    
    return get_user_by_username(db, username)

# Функция аутентификации
def authenticate_user(db: Session, username: str, password: str):
    user = get_user_by_username(db, username)
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    return user

# Маршруты
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request, db: Session = Depends(get_db)):
    materials = get_materials(db)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "materials": materials
    })

@app.get("/material/{material_id}", response_class=HTMLResponse)
async def read_material(request: Request, material_id: int, db: Session = Depends(get_db)):
    material = get_material(db, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Получаем все материалы для блока "Другие материалы"
    all_materials = get_materials(db)
    
    return templates.TemplateResponse("material.html", {
        "request": request,
        "material": material,
        "materials": all_materials  # Передаем все материалы в шаблон
    })


# Админ-роуты
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/admin/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверные учетные данные"
        })
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=30)
    )
    
    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/admin/dashboard", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if not current_user:
        return RedirectResponse(url="/admin/login")
    
    materials = get_materials(db)
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "materials": materials,
        "user": current_user
    })

@app.post("/admin/add-material")
async def add_material(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    category: str = Form("general"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if not current_user:
        return RedirectResponse(url="/admin/login")
    
    create_material(db, title, content, category)
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.post("/admin/delete-material/{material_id}")
async def delete_material(
    request: Request,
    material_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_cookie)
):
    if not current_user:
        return RedirectResponse(url="/admin/login")
    
    delete_material(db, material_id)
    return RedirectResponse(url="/admin/dashboard", status_code=303)

@app.get("/admin/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)