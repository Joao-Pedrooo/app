from fastapi import FastAPI, Form, Request, Depends , UploadFile , File, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from starlette.responses import Response
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Usuario, Escola, Cronograma
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from pathlib import Path
from datetime import datetime
import shutil
import os
import uuid

Base.metadata.create_all(bind=engine)

app = FastAPI()

# Configuração de arquivos estáticos e templates
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


# Função para verificar autenticação
def is_authenticated(request: Request):
    return request.cookies.get("authenticated") == "true"


# Rota para exibir a página de login
@app.get("/", response_class=HTMLResponse)
async def read_login(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# Rota de login com verificação no banco de dados
@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(Usuario).filter(Usuario.nome == username).first()
    if not user or user.senha != password:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Usuário ou senha inválidos."},
        )

    # Definir cookie de autenticação
    response = RedirectResponse(url="/index", status_code=303)
    response.set_cookie(key="authenticated", value="true", httponly=True)
    return response


# Página protegida (apenas para usuários autenticados)
@app.get("/index", response_class=HTMLResponse)
async def index(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("index.html", {"request": request})


# Rota para Gestão de Área Verde (HTML)
@app.get("/gestao_area_verde", response_class=HTMLResponse)
async def gestao_area_verde(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/")
    return templates.TemplateResponse("gestao_area_verde.html", {"request": request})


# Rota para retornar JSON das escolas
@app.get("/escolas", response_model=list[dict])
async def listar_escolas(db: Session = Depends(get_db)):
    escolas = db.query(Escola).all()
    return [
        {
            "id": escola.id,
            "nome": escola.nome_escola,
            "logradouro": escola.logradouro,
            "bairro": escola.bairro,
            "municipio": escola.municipio,
        }
        for escola in escolas
    ]


# Rota para o HTML da edição
@app.get("/editar-escola", response_class=HTMLResponse)
async def editar_escola_html(request: Request, id: int, db: Session = Depends(get_db)):
    escola = db.query(Escola).filter(Escola.id == id).first()
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    return templates.TemplateResponse(
        "editar_escola.html", {"request": request, "escola": escola}
    )

## fotos  rota
# Rota para o HTML da edição 2
@app.get("/editar-escola-fotos", response_class=HTMLResponse)
async def editar_escola_fotos_html(request: Request, id: int, db: Session = Depends(get_db)):
    escola = db.query(Escola).filter(Escola.id == id).first()
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")
    return templates.TemplateResponse(
        "editar_escola_fotos.html", {"request": request, "escola": escola}
    )



# Atualização da escola
class EscolaAtualizacao(BaseModel):
    nome_escola: str
    logradouro: str
    bairro: str
    municipio: str
######################################## Cronograma #############################################
# Rota: Listar cronogramas
@app.get("/gestao_cronograma", response_class=HTMLResponse)
async def gestao_cronograma(
    request: Request,
    db: Session = Depends(get_db),
    search: str = None,
    order_by_priority: bool = True,
):
    try:
        query = db.query(Cronograma).join(Escola)

        if search:
            query = query.filter(Escola.nome_escola.ilike(f"%{search}%"))

        if order_by_priority:
            query = query.order_by(Cronograma.prioridade.desc())

        cronogramas = query.all()

        realizados = [c for c in cronogramas if c.realizado]
        nao_realizados = [c for c in cronogramas if not c.realizado]

        return templates.TemplateResponse("gestao_cronograma.html", {
            "request": request,
            "realizados": realizados,
            "nao_realizados": nao_realizados,
            "search": search or "",
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar cronogramas: {str(e)}")
# Rota: Adicionar ou Editar cronograma (HTML)
@app.get("/novo-cronograma", response_class=HTMLResponse)
async def novo_cronograma(request: Request, id: int = None, db: Session = Depends(get_db)):
    """
    Renderiza a página para adicionar ou editar cronograma.
    """
    try:
        # Obter lista de escolas
        escolas = db.query(Escola).all()

        # Inicializar cronograma como None
        cronograma = None

        if id:  # Se for edição, buscar o cronograma
            cronograma = db.query(Cronograma).filter(Cronograma.id == id).first()
            if not cronograma:
                raise HTTPException(status_code=404, detail="Cronograma não encontrado")

        # Renderizar o template com as informações do cronograma e escolas
        return templates.TemplateResponse("novo_cronograma.html", {
            "request": request,
            "cronograma": cronograma,
            "escolas": escolas,
            "selected_escola": cronograma.escola_id if cronograma else None  # Seleção da escola
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao carregar cronograma ou escolas: {str(e)}")

# Rota: Criar ou Atualizar cronograma (POST)
@app.post("/salvar-cronograma")
async def salvar_cronograma(
    id: int = Form(None),
    numero_os: str = Form(...),
    previsao_realizacao: str = Form(...),
    realizado: str = Form(None),
    escola_id: str = Form(...),  # Capturar como string para validação
    email: str = Form(None),
    bairro: str = Form(None),
    metros: int = Form(None),
    grupos: str = Form(None),
    equipe_responsavel: str = Form(None),
    gerado_os: bool = Form(False),
    os_entregue: bool = Form(False),
    observacao: str = Form(None),
    mes_realizado: str = Form(None),
    prioridade: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        if not escola_id.isdigit():
            raise HTTPException(status_code=422, detail="Escola inválida. Selecione uma escola válida.")

        # Converter valores
        realizado = True if realizado == "on" else False
        escola_id = int(escola_id)  # Converter para inteiro

        if id:
            # Atualizar cronograma existente
            cronograma = db.query(Cronograma).filter(Cronograma.id == id).first()
            if not cronograma:
                raise HTTPException(status_code=404, detail="Cronograma não encontrado")
            cronograma.numero_os = numero_os
            cronograma.previsao_realizacao = datetime.strptime(previsao_realizacao, "%Y-%m-%d")
            cronograma.realizado = realizado
            cronograma.escola_id = escola_id
            cronograma.email = email
            cronograma.bairro = bairro
            cronograma.metros = metros
            cronograma.grupos = grupos
            cronograma.equipe_responsavel = equipe_responsavel
            cronograma.gerado_os = gerado_os
            cronograma.os_entregue = os_entregue
            cronograma.observacao = observacao
            cronograma.mes_realizado = mes_realizado
            cronograma.prioridade = prioridade
        else:
            # Criar novo cronograma
            novo_cronograma = Cronograma(
                numero_os=numero_os,
                previsao_realizacao=datetime.strptime(previsao_realizacao, "%Y-%m-%d"),
                realizado=realizado,
                escola_id=escola_id,
                email=email,
                bairro=bairro,
                metros=metros,
                grupos=grupos,
                equipe_responsavel=equipe_responsavel,
                gerado_os=gerado_os,
                os_entregue=os_entregue,
                observacao=observacao,
                mes_realizado=mes_realizado,
                prioridade=prioridade,
            )
            db.add(novo_cronograma)

        db.commit()
        return RedirectResponse(url="/gestao_cronograma", status_code=303)
    except ValueError:
        raise HTTPException(status_code=422, detail="Valores inválidos fornecidos.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar cronograma: {str(e)}")

# Rota: Excluir cronograma
@app.get("/deletar-cronograma/{id}")
async def deletar_cronograma(id: int, db: Session = Depends(get_db)):
    """
    Exclui um cronograma existente.
    """
    try:
        cronograma = db.query(Cronograma).filter(Cronograma.id == id).first()
        if not cronograma:
            raise HTTPException(status_code=404, detail="Cronograma não encontrado")
        db.delete(cronograma)
        db.commit()
        return RedirectResponse(url="/gestao_cronograma", status_code=303)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao deletar cronograma: {str(e)}")
##################################################################################################
## editar
@app.post("/escolas/{id}/editar")
async def atualizar_escola(
    id: int,
    dados: EscolaAtualizacao,
    db: Session = Depends(get_db),
):
    escola = db.query(Escola).filter(Escola.id == id).first()
    if not escola:
        raise HTTPException(status_code=404, detail="Escola não encontrada")

    escola.nome_escola = dados.nome_escola
    escola.logradouro = dados.logradouro
    escola.bairro = dados.bairro
    escola.municipio = dados.municipio
    db.commit()

    return {"message": "Escola atualizada com sucesso"}


# #############Rota para listar fotos de uma escola
# Diretório para armazenar as imagens


# Rota para logout
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("authenticated")
    return response
