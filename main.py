from fastapi import FastAPI, Form, Request, Depends
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import HTTPException
from starlette.responses import Response
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Usuario, Escola
from pydantic import BaseModel

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


## fotos
@app.post("/escolas/{id}/edit")
async def atualizar_escola_fotos(
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


# Rota para logout
@app.get("/logout")
async def logout(response: Response):
    response = RedirectResponse(url="/", status_code=303)
    response.delete_cookie("authenticated")
    return response
