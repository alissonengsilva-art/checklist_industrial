from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Configuração da URL do banco de dados MySQL
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://root:5665@localhost/energy_center"

# Cria o engine de conexão
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Cria a sessão local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria a base para os modelos ORM
Base = declarative_base()
