from sqlalchemy.orm import Session
from models import Material, User
from datetime import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Хеширование пароля
def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Материалы
def get_materials(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Material).order_by(Material.created_at.desc()).offset(skip).limit(limit).all()

def get_material(db: Session, material_id: int):
    return db.query(Material).filter(Material.id == material_id).first()

def create_material(db: Session, title: str, content: str, category: str = "general"):
    db_material = Material(
        title=title,
        content=content,
        category=category,
        created_at=datetime.utcnow()
    )
    db.add(db_material)
    db.commit()
    db.refresh(db_material)
    return db_material

def delete_material(db: Session, material_id: int):
    db_material = get_material(db, material_id)
    if db_material:
        db.delete(db_material)
        db.commit()
    return db_material

# Пользователи
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()

def create_user(db: Session, username: str, password: str):
    hashed_password = get_password_hash(password)
    db_user = User(username=username, password_hash=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user