from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Pegue a URL de conexão do banco de dados das variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://root:root@db:5432/app_db")

# Cria o engine para conectar ao banco de dados
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Função para obter a sessão do banco de dados
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
