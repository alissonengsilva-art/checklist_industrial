from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Caminho para o seu banco
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:5665@localhost/energy_center"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# ✅ Essa função é a que estava faltando
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
