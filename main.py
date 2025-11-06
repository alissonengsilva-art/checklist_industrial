import sys, os
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import SessionLocal, engine

# ==========================================================
# ⚙️ AJUSTE DE CAMINHOS COMPATÍVEL COM PYINSTALLER
# ==========================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS  # Diretório temporário do executável
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

templates_dir = os.path.join(BASE_DIR, "templates")
static_dir = os.path.join(BASE_DIR, "static")

# ==========================================================
# 🔧 CONFIGURAÇÃO GERAL
# ==========================================================
app = FastAPI()
models.Base.metadata.create_all(bind=engine)

# 🔹 Monta diretórios de templates e estáticos
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
else:
    print(f"⚠️ Pasta 'static' não encontrada em {static_dir}")

templates = Jinja2Templates(directory=templates_dir)

# 🕒 Fuso horário de Brasília (UTC-3)
brasil_tz = timezone(timedelta(hours=-3))

# ==========================================================
# 🔌 DEPENDÊNCIA DO BANCO
# ==========================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==========================================================
# 📋 PÁGINA PRINCIPAL - FORMULÁRIO
# ==========================================================
@app.get("/", response_class=HTMLResponse)
def checklist_form(request: Request, db: Session = Depends(get_db)):
    itens = db.query(models.ItemChecklist).all()

    itens_ar = [i for i in itens if i.sistema == "Ar Comprimido"]
    itens_agua_resfriamento = [i for i in itens if i.sistema == "Água de Resfriamento"]
    itens_agua_gelada = [i for i in itens if i.sistema == "Água Gelada"]
    itens_funilaria_climatizacao = [i for i in itens if i.sistema == "Climatizacao_f"]
    itens_montagem_climatizacao = [i for i in itens if i.sistema == "Climatizacao_m"]
    itens_communication_climatizacao = [i for i in itens if i.sistema == "Climatizacao_c"]

    return templates.TemplateResponse("checklist.html", {
        "request": request,
        "itens_ar": itens_ar,
        "itens_agua_resfriamento": itens_agua_resfriamento,
        "itens_agua_gelada": itens_agua_gelada,
        "itens_funilaria_climatizacao": itens_funilaria_climatizacao,
        "itens_montagem_climatizacao": itens_montagem_climatizacao,
        "itens_communication_climatizacao": itens_communication_climatizacao
    })

# ==========================================================
# 💾 SALVAR CHECKLIST E ITENS
# ==========================================================
@app.post("/salvar")
async def salvar_checklist(request: Request, db: Session = Depends(get_db)):
    form = await request.form()

    checklist = models.Checklist(
        tecnico=form.get("tecnico"),
        especialidade_tecnico=form.get("especialidade_tecnico"),
        team_leader=form.get("team_leader"),
        especialidade_team_leader=form.get("especialidade_team_leader"),
        turno=form.get("turno"),
        tipo_turno=form.get("tipo_turno"),
        data_criacao=datetime.now()
    )
    db.add(checklist)
    db.commit()
    db.refresh(checklist)

    # 🔹 Busca todos os itens cadastrados
    todos_itens = db.query(models.ItemChecklist).all()

    # 🔹 Agora tudo dentro do loop!
    for item in todos_itens:
        valor_raw = form.get(f"valor_{item.id}")

        if valor_raw in (None, ""):
            valor = None
        else:
            try:
                valor = float(valor_raw)
            except ValueError:
                valor = None

        ok_marcado = form.get(f"ok_{item.id}") is not None
        nok_marcado = form.get(f"nok_{item.id}") is not None

        # Define status_ok apenas se o técnico marcou algo
        if ok_marcado:
            status_ok = True
        elif nok_marcado:
            status_ok = False
        else:
            status_ok = None  # Nenhum marcado


        

        comentario = form.get(f"coment_{item.id}")

        registro = models.ItemRegistro(
            checklist_id=checklist.id,
            sistema=item.sistema,
            descricao=item.descricao,
            unidade=item.unidade,
            valor_min=item.valor_min,
            valor_max=item.valor_max,
            valor_registrado=valor,
            status_ok=status_ok,
            comentario=comentario
)

        
        db.add(registro)

    db.commit()
    return RedirectResponse(url="/", status_code=303)


@app.get("/checklist/{checklist_id}", response_class=HTMLResponse)
def detalhes(request: Request, checklist_id: int, db: Session = Depends(get_db)):
    checklist = db.query(models.Checklist).filter(models.Checklist.id == checklist_id).first()
    if not checklist:
        return HTMLResponse("Checklist não encontrado", status_code=404)

    itens_ar = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Ar Comprimido"
    ).all()

    itens_agua_resfriamento = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Água de Resfriamento"
    ).all()

    itens_agua_gelada = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Água Gelada"
    ).all()

    itens_funilaria_climatizacao = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Climatizacao_f"
    ).all()

    itens_montagem_climatizacao = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Climatizacao_m"
    ).all()

    itens_communication_climatizacao = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Climatizacao_c"
    ).all()

    return templates.TemplateResponse("detalhes.html", {
        "request": request,
        "checklist": checklist,
        "itens_ar": itens_ar,
        "itens_agua_resfriamento": itens_agua_resfriamento,
        "itens_agua_gelada": itens_agua_gelada,
        "itens_funilaria_climatizacao": itens_funilaria_climatizacao,
        "itens_montagem_climatizacao": itens_montagem_climatizacao,
        "itens_communication_climatizacao": itens_communication_climatizacao
    })



# ==========================================================
# 📊 DASHBOARD PRINCIPAL
# ==========================================================
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    checklists = db.query(models.Checklist).order_by(models.Checklist.data_criacao.desc()).all()
    return templates.TemplateResponse("dashboard.html", {"request": request, "checklists": checklists})

# ==========================================================
# 📄 DETALHES DE UM CHECKLIST
# ==========================================================
@app.get("/checklist/{checklist_id}", response_class=HTMLResponse)
def detalhes(request: Request, checklist_id: int, db: Session = Depends(get_db)):
    checklist = db.query(models.Checklist).filter(models.Checklist.id == checklist_id).first()
    if not checklist:
        return HTMLResponse("Checklist não encontrado", status_code=404)

    itens_ar = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Ar Comprimido"
    ).all()

    itens_agua = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "Água de Resfriamento"
    ).all()

    return templates.TemplateResponse("detalhes.html", {
        "request": request,
        "checklist": checklist,
        "itens_ar": itens_ar,
        "itens_agua": itens_agua
    })

# ==========================================================
# 📊 DASHBOARD DE STATUS
# ==========================================================
@app.get("/dashboard_status", response_class=HTMLResponse)
def dashboard_status(request: Request, db: Session = Depends(get_db)):
    equipamentos = db.query(models.StatusEquipamento).all()
    total_ok = sum(1 for e in equipamentos if e.status == "OK")
    total_nok = sum(1 for e in equipamentos if e.status == "NOK")
    total_man = sum(1 for e in equipamentos if e.status == "Manutenção")

    resumo = {}
    for e in equipamentos:
        tipo = e.tipo or "Sem Tipo"
        if tipo not in resumo:
            resumo[tipo] = {"ok": 0, "nok": 0, "man": 0}
        if e.status == "OK":
            resumo[tipo]["ok"] += 1
        elif e.status == "NOK":
            resumo[tipo]["nok"] += 1
        elif e.status == "Manutenção":
            resumo[tipo]["man"] += 1

    return templates.TemplateResponse("dashboard_status.html", {
        "request": request,
        "equipamentos": equipamentos,
        "resumo": resumo,
        "total_ok": total_ok,
        "total_nok": total_nok,
        "total_man": total_man
    })

# ==========================================================
# 🔍 DETALHES POR TIPO
# ==========================================================
@app.get("/detalhes/{tipo}", response_class=HTMLResponse)
def detalhes_tipo(request: Request, tipo: str, db: Session = Depends(get_db)):
    equipamentos = (
        db.query(models.StatusEquipamento)
        .filter(models.StatusEquipamento.tipo == tipo)
        .order_by(models.StatusEquipamento.nome_equipamento.asc())
        .all()
    )

    historico = (
        db.query(models.HistoricoStatus)
        .join(models.StatusEquipamento)
        .filter(models.StatusEquipamento.tipo == tipo)
        .order_by(models.HistoricoStatus.data_modificacao.desc())
        .limit(20)
        .all()
    )

    total_ok = sum(1 for e in equipamentos if e.status == "OK")
    total_nok = sum(1 for e in equipamentos if e.status == "NOK")
    total_man = sum(1 for e in equipamentos if e.status == "Manutenção")

    total_all = total_ok + total_nok + total_man
    disponibilidade = round((total_ok / total_all) * 100, 1) if total_all > 0 else 0

    return templates.TemplateResponse("detalhes_tipo.html", {
        "request": request,
        "tipo": tipo,
        "equipamentos": equipamentos,
        "historico": historico,
        "total_ok": total_ok,
        "total_nok": total_nok,
        "total_man": total_man,
        "disponibilidade": disponibilidade
    })

# ==========================================================
# 📜 HISTÓRICO
# ==========================================================
@app.get("/historico", response_class=HTMLResponse)
async def historico_page(
    request: Request,
    db: Session = Depends(get_db),
    equipamento_id: int = Query(None),
    tecnico: str = Query(None),
    tipo: str = Query(None),
    data_inicio: str = Query(None),
    data_fim: str = Query(None),
):
    query = (
        db.query(models.HistoricoStatus)
        .join(models.StatusEquipamento)
        .order_by(models.HistoricoStatus.data_modificacao.desc())
    )

    if equipamento_id:
        query = query.filter(models.HistoricoStatus.equipamento_id == equipamento_id)
    if tecnico:
        query = query.filter(models.HistoricoStatus.tecnico.ilike(f"%{tecnico}%"))
    if tipo:
        query = query.filter(models.StatusEquipamento.tipo.ilike(f"%{tipo}%"))
    if data_inicio and data_fim:
        try:
            data_i = datetime.strptime(data_inicio, "%Y-%m-%d")
            data_f = datetime.strptime(data_fim, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(models.HistoricoStatus.data_modificacao.between(data_i, data_f))
        except ValueError:
            pass

    historico = query.all()
    tecnicos = sorted({h.tecnico for h in db.query(models.HistoricoStatus).filter(models.HistoricoStatus.tecnico.isnot(None))})
    tipos = sorted({e.tipo for e in db.query(models.StatusEquipamento).filter(models.StatusEquipamento.tipo.isnot(None))})

    return templates.TemplateResponse("historico.html", {
        "request": request,
        "historico": historico,
        "equipamento_id": equipamento_id,
        "tecnico_selecionado": tecnico,
        "tipo_selecionado": tipo,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "tecnicos": tecnicos,
        "tipos": tipos
    })

# ==========================================================
# ⚙️ ATUALIZAR STATUS DOS EQUIPAMENTOS
# ==========================================================
@app.get("/status", response_class=HTMLResponse)
async def status_page(request: Request, db: Session = Depends(get_db), tipo: str = None):
    query = db.query(models.StatusEquipamento)
    if tipo and tipo != "Todos":
        query = query.filter(models.StatusEquipamento.tipo == tipo)

    equipamentos = query.order_by(models.StatusEquipamento.nome_equipamento.asc()).all()
    tipos = [t[0] for t in db.query(models.StatusEquipamento.tipo).distinct().all()]
    tipos = sorted(tipos)
    tipos.insert(0, "Todos")

    return templates.TemplateResponse("status.html", {
        "request": request,
        "equipamentos": equipamentos,
        "tipos": tipos,
        "tipo_selecionado": tipo or "Todos"
    })

@app.get("/atualizar_status", response_class=HTMLResponse)
async def atualizar_status_get(request: Request, db: Session = Depends(get_db), tipo: str = None):
    if not tipo:
        return RedirectResponse(url="/atualizar_status?tipo=Bomba%20Resfriamento", status_code=303)

    query = db.query(models.StatusEquipamento)
    if tipo != "Todos":
        query = query.filter(models.StatusEquipamento.tipo == tipo)

    equipamentos = query.order_by(models.StatusEquipamento.nome_equipamento.asc()).all()
    tipos = [t[0] for t in db.query(models.StatusEquipamento.tipo).distinct().all()]
    tipos = sorted(tipos)

    return templates.TemplateResponse("status.html", {
        "request": request,
        "equipamentos": equipamentos,
        "tipos": tipos,
        "tipo_selecionado": tipo
    })

@app.post("/atualizar_status")
async def atualizar_status(
    request: Request,
    equipamento_id: int = Form(...),
    tipo_atual: str = Form("Todos"),
    db: Session = Depends(get_db)
):
    form = await request.form()
    equipamento = db.query(models.StatusEquipamento).filter(models.StatusEquipamento.id == equipamento_id).first()

    if equipamento:
        novo_status = form.get(f"status_{equipamento_id}")
        observacao = form.get(f"obs_{equipamento_id}")
        tecnico = form.get(f"tec_{equipamento_id}")

        historico = models.HistoricoStatus(
            equipamento_id=equipamento.id,
            status_anterior=equipamento.status,
            status_novo=novo_status,
            observacao=observacao,
            tecnico=tecnico
        )
        db.add(historico)

        equipamento.status = novo_status
        equipamento.observacao = observacao
        equipamento.tecnico = tecnico
        equipamento.data_atualizacao = datetime.now(brasil_tz)
        db.commit()

    return RedirectResponse(url=f"/atualizar_status?tipo={tipo_atual}", status_code=303)

# ==========================================================
# ▶️ PONTO DE ENTRADA
# ==========================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
