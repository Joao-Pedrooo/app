from sqlalchemy import Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from database import Base

class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    senha = Column(String, nullable=False)

class Escola(Base):
    __tablename__ = 'escolas'
    id = Column(Integer, primary_key=True, index=True)
    nome_escola = Column(String, index=True)
    logradouro = Column(String)
    numero = Column(Integer)
    bairro = Column(String)
    municipio = Column(String)
    #unidade = Column(String)
    fotos = relationship("Foto", back_populates="escola")

class Foto(Base):
    __tablename__ = 'fotos'
    id = Column(Integer, primary_key=True, index=True)
    escola_id = Column(Integer, ForeignKey("escolas.id"))
    tipo = Column(String, nullable=False)  # 'antes' ou 'depois'
    campo = Column(String, nullable=False)  # A, B, C...
    caminho_foto = Column(String, nullable=False)  # URL ou caminho do arquivo
    escola = relationship("Escola", back_populates="fotos")


class OrdemServico(Base):
    __tablename__ = 'ordens_servico'
    id = Column(Integer, primary_key=True, index=True)
    numero_os = Column(String, index=True)
    data_inicio = Column(DateTime)
    data_fim = Column(DateTime)
    status = Column(String)