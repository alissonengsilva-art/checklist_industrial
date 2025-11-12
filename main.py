import sys, os
from datetime import datetime, timezone, timedelta
from urllib.parse import unquote
from io import BytesIO

from fastapi import FastAPI, Request, Form, Depends, Query
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from weasyprint import HTML

import models
from database import SessionLocal, engine

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ==========================================================
# ⚙️ AJUSTE DE CAMINHOS COMPATÍVEL COM PYINSTALLER
# ==========================================================
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
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
# ==========================================================
# 📋 CHECKLIST (FORMULÁRIO PRINCIPAL)
# ==========================================================
@app.get("/", response_class=HTMLResponse)
def checklist_form(request: Request, db: Session = Depends(get_db)):
    
    itens = db.query(models.ItemChecklist).all()
    grupos_main = {}
    grupos_supplier = {}

    # Ícones por sistema
    ICONES = {
        "ar comprimido": "📊",
        "agua de resfriamento": "💧",
        "água de resfriamento": "💧",
        "agua gelada": "❄️",
        "água gelada": "❄️",
        "climatizacao_f": "🌀",
        "climatização_f": "🌀",
        "climatizacao_m": "🧊",
        "climatização_m": "🧊",
        "climatizacao_c": "🌬️",
        "climatização_c": "🌬️",
        "denso": "🏢",
        "mmh":"🏢",
        "pmc":"🏢",
        "tiberina":"🏢",
        "revest":"🏢"

    }

    for item in itens:
        sistema_original = item.sistema.strip() if item.sistema else ""
        sistema_normalizado = sistema_original.lower()

        icone = ICONES.get(sistema_normalizado, "⚙️")

        nome_map = {
            "ar comprimido": "Ar Comprimido",
            "agua de resfriamento": "Água de Resfriamento",
            "água de resfriamento": "Água de Resfriamento",
            "agua gelada": "Água Gelada",
            "água gelada": "Água Gelada",
            "climatizacao_f": "Climatização Funilaria",
            "climatização_f": "Climatização Funilaria",
            "climatizacao_m": "Climatização Montagem",
            "climatização_m": "Climatização Montagem",
            "climatizacao_c": "Climatização Communication",
            "climatização_c": "Climatização Communication",
            "denso": "DENSO-SP06",
            "mmh": "MMH-SP4",
            "pmc":"PMC-SP01",
            "tiberina":"TIBERINA-SP04",
            "revest":"REVESTCOAT-SP02"
        }

        nome_legivel = nome_map.get(sistema_normalizado, sistema_original)
        nome_exibicao = f"{icone} {nome_legivel}"

        if sistema_normalizado in ["denso", "mmh", "pmc", "tiberina","revest"]:
            grupos_supplier.setdefault(nome_exibicao, []).append(item)
        else:
            grupos_main.setdefault(nome_exibicao, []).append(item)

    print(f"✅ MAIN grupos: {len(grupos_main)}")
    print(f"✅ SUPPLIER grupos: {len(grupos_supplier)}")

    print("🔧 Renderizando template checklist.html com dados:")
    print(f"MAIN grupos: {list(grupos_main.keys())}")
    print(f"SUPPLIER grupos: {list(grupos_supplier.keys())}")


    # Renderiza o HTML
    return templates.TemplateResponse("checklist.html", {
        "request": request,
        "grupos_main": grupos_main,
        "grupos_supplier": grupos_supplier
    })




# 💾 SALVAR CHECKLIST COMPLETO
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

    todos_itens = db.query(models.ItemChecklist).all()

    for item in todos_itens:
        valor_raw = form.get(f"valor_{item.id}")
        valor = None
        if valor_raw not in (None, ""):
            try:
                valor = float(valor_raw)
            except ValueError:
                valor = None

        ok_marcado = form.get(f"ok_{item.id}") is not None
        nok_marcado = form.get(f"nok_{item.id}") is not None

        status_ok = True if ok_marcado else False if nok_marcado else None
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


# ==========================================================
# 💾 SALVAR CHECKLIST PARCIAL (MAIN / SUPPLIER)
# ==========================================================
@app.post("/salvar_main")
async def salvar_main(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    print("Checklist MAIN PLANT recebido.")

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

    # 🔹 Filtra apenas sistemas do Main Plant
    sistemas_main = ["Ar Comprimido", "Água de Resfriamento", "Água Gelada",
                     "Climatizacao_f", "Climatizacao_m", "Climatizacao_c"]

    todos_itens = db.query(models.ItemChecklist).filter(models.ItemChecklist.sistema.in_(sistemas_main)).all()

    for item in todos_itens:
        valor_raw = form.get(f"valor_{item.id}")
        valor = float(valor_raw) if valor_raw else None

        ok_marcado = form.get(f"ok_{item.id}") is not None
        nok_marcado = form.get(f"nok_{item.id}") is not None
        status_ok = True if ok_marcado else False if nok_marcado else None
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


@app.post("/salvar_supplier")
async def salvar_supplier(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    print("Checklist SUPPLIER PARK recebido.")

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

    # ✅ Use os nomes reais do banco
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest"]

    todos_itens = db.query(models.ItemChecklist).filter(
        models.ItemChecklist.sistema.in_(sistemas_supplier)
    ).all()

    for item in todos_itens:
        valor_raw = form.get(f"valor_{item.id}")
        valor = float(valor_raw) if valor_raw else None

        ok_marcado = form.get(f"ok_{item.id}") is not None
        nok_marcado = form.get(f"nok_{item.id}") is not None
        status_ok = True if ok_marcado else False if nok_marcado else None
        comentario = form.get(f"coment_{item.id}")

        registro = models.ItemRegistro(
            checklist_id=checklist.id,
            sistema=item.sistema,  # ← usa exatamente o nome do banco
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
    print(f"✅ Checklist Supplier salvo com {len(todos_itens)} itens.")
    return RedirectResponse(url="/", status_code=303)



# ==========================================================
# 📊 HISTÓRICO DE CHECKLISTS
# 📊 HISTÓRICO DE CHECKLISTS
@app.get("/historico_checklist", response_class=HTMLResponse)
def historico_checklist(request: Request, db: Session = Depends(get_db)):
    checklists = db.query(models.Checklist).order_by(models.Checklist.data_criacao.desc()).all()

    # Lista real de sistemas Supplier no banco
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest"]

    for c in checklists:
        # Procura qualquer item do checklist que pertença a um supplier
        tem_supplier = db.query(models.ItemRegistro).filter(
            models.ItemRegistro.checklist_id == c.id,
            models.ItemRegistro.sistema.in_(sistemas_supplier)
        ).first()

        c.local = "supplier" if tem_supplier else "main"

    return templates.TemplateResponse(
        "historico_checklist.html",
        {"request": request, "checklists": checklists}
    )



# ==========================================================
# 📄 DETALHES DE UM CHECKLIST
# ==========================================================
@app.get("/checklist/{checklist_id}", response_class=HTMLResponse)
def detalhes_checklist(request: Request, checklist_id: int, db: Session = Depends(get_db)):
    checklist = db.query(models.Checklist).filter(models.Checklist.id == checklist_id).first()
    if not checklist:
        return HTMLResponse("Checklist não encontrado", status_code=404)

    # ✅ Verifica se é Supplier (qualquer um dos fornecedores)
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest"]

    tem_supplier = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema.in_(sistemas_supplier)
    ).first()

    tipo_checklist = "supplier" if tem_supplier else "main"

    # =========================================================
    # 🏭 ITENS MAIN PLANT
    # =========================================================
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

    # =========================================================
    # 🏢 ITENS SUPPLIER PARK
    # =========================================================
    itens_denso = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "denso"
    ).all()

    itens_mmh = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "mmh"
    ).all()

    itens_pmc = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "pmc"
    ).all()

    itens_tiberina = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "tiberina"
    ).all()

    itens_revest = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "revest"
    ).all()

    # =========================================================
    # 🧾 Envia tudo pro template
    # =========================================================
    return templates.TemplateResponse("detalhes_checklist.html", {
        "request": request,
        "checklist": checklist,
        "tipo_checklist": tipo_checklist,

        # Grupos Main
        "itens_ar": itens_ar,
        "itens_agua_resfriamento": itens_agua_resfriamento,
        "itens_agua_gelada": itens_agua_gelada,
        "itens_funilaria_climatizacao": itens_funilaria_climatizacao,
        "itens_montagem_climatizacao": itens_montagem_climatizacao,
        "itens_communication_climatizacao": itens_communication_climatizacao,

        # Grupos Supplier
        "itens_denso": itens_denso,
        "itens_mmh": itens_mmh,
        "itens_pmc": itens_pmc,
        "itens_tiberina": itens_tiberina,
        "itens_revest": itens_revest
    })


# ==========================================================
# 📊 DASHBOARD DE STATUS DOS EQUIPAMENTOS
# ==========================================================
@app.get("/dashboard_equipamentos", response_class=HTMLResponse)
def dashboard_equipamentos(request: Request, db: Session = Depends(get_db)):
    equipamentos = db.query(models.StatusEquipamento).order_by(models.StatusEquipamento.tipo.asc()).all()

    total_ok = sum(1 for e in equipamentos if e.status.upper() == "OK")
    total_nok = sum(1 for e in equipamentos if e.status.upper() == "NOK")
    total_man = sum(1 for e in equipamentos if e.status.upper() in ["MANUTENCAO", "MANUTENÇÃO"])

    total_geral = total_ok + total_nok + total_man
    disponibilidade = round((total_ok / total_geral) * 100, 1) if total_geral > 0 else 0

    tipos = {}
    for e in equipamentos:
        tipo = e.tipo or "Sem Tipo"
        if tipo not in tipos:
            tipos[tipo] = {"ok": 0, "nok": 0, "man": 0}
        if e.status.upper() == "OK":
            tipos[tipo]["ok"] += 1
        elif e.status.upper() == "NOK":
            tipos[tipo]["nok"] += 1
        elif e.status.upper() in ["MANUTENCAO", "MANUTENÇÃO"]:
            tipos[tipo]["man"] += 1

    labels = list(tipos.keys())
    valores_ok = [v["ok"] for v in tipos.values()]
    valores_nok = [v["nok"] for v in tipos.values()]
    valores_man = [v["man"] for v in tipos.values()]

    return templates.TemplateResponse("dashboard_equipamentos.html", {
        "request": request,
        "total_ok": total_ok,
        "total_nok": total_nok,
        "total_man": total_man,
        "disponibilidade": disponibilidade,
        "labels": labels,
        "valores_ok": valores_ok,
        "valores_nok": valores_nok,
        "valores_man": valores_man
    })

# ==========================================================
# 📜 HISTÓRICO DE STATUS (COM PAGINAÇÃO)
# ==========================================================
@app.get("/historico", response_class=HTMLResponse)
async def historico_page(
    request: Request,
    db: Session = Depends(get_db),
    equipamento_id: int = Query(None),
    tecnico: str = Query(None),
    tipo: str = Query(None),
    data_inicial: str = Query(None),
    data_final: str = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=10, le=200)
):
    query = db.query(models.HistoricoStatus).join(models.StatusEquipamento).order_by(models.HistoricoStatus.data_modificacao.desc())

    if equipamento_id:
        query = query.filter(models.HistoricoStatus.equipamento_id == equipamento_id)
    if tecnico:
        query = query.filter(models.HistoricoStatus.tecnico.ilike(f"%{tecnico}%"))
    if tipo:
        query = query.filter(models.StatusEquipamento.tipo.ilike(f"%{tipo}%"))
    if data_inicial and data_final:
        try:
            data_i = datetime.strptime(data_inicial, "%Y-%m-%d")
            data_f = datetime.strptime(data_final, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(models.HistoricoStatus.data_modificacao.between(data_i, data_f))
        except ValueError:
            pass

    total_registros = query.count()
    total_paginas = (total_registros + limit - 1) // limit
    offset = (page - 1) * limit
    historico = query.offset(offset).limit(limit).all()

    tecnicos = sorted({h.tecnico for h in db.query(models.HistoricoStatus) if h.tecnico})
    tipos = sorted({e.tipo for e in db.query(models.StatusEquipamento) if e.tipo})

    return templates.TemplateResponse("historico.html", {
        "request": request,
        "historico": historico,
        "tecnico_selecionado": tecnico,
        "tipo_selecionado": tipo,
        "data_inicial": data_inicial,
        "data_final": data_final,
        "tecnicos": tecnicos,
        "tipos": tipos,
        "pagina_atual": page,
        "total_paginas": total_paginas,
        "limit": limit,
        "total_registros": total_registros
    })

# ==========================================================
# ⚙️ ATUALIZAR STATUS DOS EQUIPAMENTOS
# ==========================================================
@app.get("/atualizar_status", response_class=HTMLResponse)
async def atualizar_status_get(request: Request, db: Session = Depends(get_db), tipo: str = None):
    if not tipo:
        return RedirectResponse(url="/atualizar_status?tipo=Bomba%20Resfriamento", status_code=303)

    query = db.query(models.StatusEquipamento)
    if tipo != "Todos":
        query = query.filter(models.StatusEquipamento.tipo == tipo)

    equipamentos = query.order_by(models.StatusEquipamento.nome_equipamento.asc()).all()
    tipos = sorted([t[0] for t in db.query(models.StatusEquipamento.tipo).distinct().all()])

    return templates.TemplateResponse("status.html", {
        "request": request,
        "equipamentos": equipamentos,
        "tipos": tipos,
        "tipo_selecionado": tipo
    })

@app.post("/atualizar_status")
async def atualizar_status(request: Request, equipamento_id: int = Form(...), tipo_atual: str = Form("Todos"), db: Session = Depends(get_db)):
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
# 🧾 GERAR PDF DE UM CHECKLIST
# ==========================================================
@app.get("/gerar_pdf")
def gerar_pdf(request: Request, checklist_id: int, db: Session = Depends(get_db)):
    checklist = db.query(models.Checklist).filter(models.Checklist.id == checklist_id).first()
    if not checklist:
        return {"detail": "Checklist não encontrado"}

    # Caminhos corretos para imagens (compatível com PyInstaller)
    base_path = os.path.dirname(os.path.abspath(__file__))
    logo_path = f"file:///{os.path.join(base_path, 'static', 'logo2.png').replace(os.sep, '/')}"
    icon_path = f"file:///{os.path.join(base_path, 'static', 'icons', 'checklist.png').replace(os.sep, '/')}"

    # ==========================================================
    # 📋 COLETA DOS DADOS DO CHECKLIST
    # ==========================================================
    grupos = {
        # MAIN PLANT
        "Ar Comprimido": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Ar Comprimido").all(),

        "Água de Resfriamento": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Água de Resfriamento").all(),

        "Água Gelada": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Água Gelada").all(),

        "Climatização Funilaria": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Climatizacao_f").all(),

        "Climatização Montagem": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Climatizacao_m").all(),

        "Climatização Communication": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "Climatizacao_c").all(),

        # SUPPLIER PARK
        "denso": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "denso").all(),

        "mmh": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "mmh").all(),

        "pmc": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "pmc").all(),

        "tiberina": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "tiberina").all(),

        "revest": db.query(models.ItemRegistro)
            .filter(models.ItemRegistro.checklist_id == checklist_id,
                    models.ItemRegistro.sistema == "revest").all(),
    }

    # ==========================================================
    # 🧾 GERA O CONTEÚDO HTML
    # ==========================================================
    html_content = templates.get_template("detalhes_pdf.html").render(
        checklist=checklist,
        grupos=grupos,
        logo_path=logo_path,
        icon_path=icon_path
    )

    # ==========================================================
    # 📄 GERA O PDF
    # ==========================================================
    pdf_buffer = BytesIO()
    HTML(string=html_content, base_url=base_path).write_pdf(pdf_buffer)
    pdf_bytes = pdf_buffer.getvalue()
    pdf_buffer.close()

    # ==========================================================
    # 📤 RETORNA O PDF DIRETAMENTE NO NAVEGADOR
    # ==========================================================
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Checklist.pdf"}
    )


# ==========================================================
# 🔍 DETALHES POR STATUS E TIPO DE EQUIPAMENTO
# ==========================================================
@app.get("/detalhes_status/{status}", response_class=HTMLResponse)
def detalhes_status(request: Request, status: str, db: Session = Depends(get_db)):
    status = status.upper()

    titulo = {
        "OK": "Equipamentos em Operação",
        "NOK": "Equipamentos com Falha",
        "MANUTENCAO": "Equipamentos em Manutenção"
    }.get(status, "Status Desconhecido")

    cor_status = {
        "OK": "#28a745",
        "NOK": "#dc3545",
        "MANUTENCAO": "#ffc107"
    }.get(status, "#6c757d")

    equipamentos = db.query(models.StatusEquipamento).filter(models.StatusEquipamento.status.ilike(status)).order_by(models.StatusEquipamento.tipo.asc()).all()
    tipos = sorted({eq.tipo for eq in equipamentos})

    return templates.TemplateResponse("detalhes_status.html", {
        "request": request,
        "status": status,
        "titulo": titulo,
        "equipamentos": equipamentos,
        "tipos": tipos,
        "cor_status": cor_status
    })

@app.get("/detalhes/{tipo}", response_class=HTMLResponse)
def detalhes_tipo(request: Request, tipo: str, db: Session = Depends(get_db)):
    tipo = unquote(tipo)

    # === Busca equipamentos desse tipo ===
    equipamentos = (
        db.query(models.StatusEquipamento)
        .filter(models.StatusEquipamento.tipo == tipo)
        .order_by(models.StatusEquipamento.nome_equipamento.asc())
        .all()
    )

    if not equipamentos:
        return HTMLResponse(
            f"<h3 style='text-align:center; margin-top:40px;'>⚠️ Nenhum equipamento encontrado para o tipo: <b>{tipo}</b></h3>",
            status_code=404
        )

    # === Busca histórico de alterações relacionado ===
    historico = (
        db.query(models.HistoricoStatus)
        .join(models.StatusEquipamento)
        .filter(models.StatusEquipamento.tipo == tipo)
        .order_by(models.HistoricoStatus.data_modificacao.desc())
        .limit(50)
        .all()
    )

    # === Totais ===
    total_ok = sum(1 for e in equipamentos if e.status.upper() == "OK")
    total_nok = sum(1 for e in equipamentos if e.status.upper() == "NOK")
    total_man = sum(1 for e in equipamentos if e.status.upper() in ["MANUTENCAO", "MANUTENÇÃO"])

    total_geral = total_ok + total_nok + total_man
    disponibilidade = round((total_ok / total_geral) * 100, 1) if total_geral > 0 else 0

    # === Renderiza o template ===
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

