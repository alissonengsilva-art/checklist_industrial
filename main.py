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
        "revest":"🏢",
        "adler":"🏢",
        "psmm":"🏢"


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
            "revest":"REVESTCOAT-SP02",
            "adler":"ADLER-SP13",
            "psmm":"PSMM-SP12",
            "fmm":"FMM-SP09"
        }

        nome_legivel = nome_map.get(sistema_normalizado, sistema_original)
        nome_exibicao = f"{icone} {nome_legivel}"

        if sistema_normalizado in ["denso", "mmh", "pmc", "tiberina","revest","adler","psmm","fmm"]:
            grupos_supplier.setdefault(nome_exibicao, []).append(item)
        else:
            grupos_main.setdefault(nome_exibicao, []).append(item)

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
    # print("Checklist MAIN PLANT recebido.")

    # ==========================================================
    # 💾 CRIA CHECKLIST PRINCIPAL
    # ==========================================================
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

    # ==========================================================
    # ⚙️ SALVAR EQUIPAMENTOS OPERANDO (CHECKBOXES)
    # ==========================================================
    for nome_campo in form.keys():
        if nome_campo.startswith(("torre_", "bac_", "bag_", "cp_", "chiller_")):
            try:
                # Extrai prefixo e número (ex: torre_1 → Torre 01)
                prefixo, numero = nome_campo.split("_", 1)
                numero_formatado = f"{int(numero):02d}"
                nome_eq = f"{prefixo.capitalize()} {numero_formatado}"

                # Define tipo do equipamento
                tipo_eq = (
                    "Torre" if "torre" in nome_campo else
                    "BAC" if "bac" in nome_campo else
                    "BAG" if "bag" in nome_campo else
                    "Compressor" if "cp" in nome_campo else
                    "Chiller"
                )

                # Cria o registro
                status_op = models.StatusOperacaoChecklist(
                    checklist_id=checklist.id,
                    nome_equipamento=nome_eq,
                    tipo=tipo_eq,
                    status="Operando",
                    tecnico=form.get("tecnico"),
                    turno=form.get("turno"),
                    data_registro=datetime.now()
                )
                db.add(status_op)

            except Exception as e:
                print(f"⚠️ Erro ao processar {nome_campo}: {e}")
                continue

    # ==========================================================
    # 🔹 SALVAR ITENS DO CHECKLIST NORMAL (Main Plant)
    # ==========================================================
    sistemas_main = [
        "Ar Comprimido",
        "Água de Resfriamento",
        "Água Gelada",
        "Climatizacao_f",
        "Climatizacao_m",
        "Climatizacao_c"
    ]

    todos_itens = db.query(models.ItemChecklist).filter(
        models.ItemChecklist.sistema.in_(sistemas_main)
    ).all()

    for item in todos_itens:
        valor_raw = form.get(f"valor_{item.id}")
        valor = float(valor_raw.replace(',', '.')) if valor_raw else None

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

    # ==========================================================
    # 💾 FINALIZA E REDIRECIONA
    # ==========================================================
    db.commit()
    print(f"✅ Checklist MAIN #{checklist.id} salvo com sucesso.")
    return RedirectResponse(url="/", status_code=303)


@app.post("/salvar_supplier")
async def salvar_supplier(request: Request, db: Session = Depends(get_db)):
    form = await request.form()
    #print("Checklist SUPPLIER PARK recebido.")

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
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest","adler","psmm","fmm"]

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
    #print(f"✅ Checklist Supplier salvo com {len(todos_itens)} itens.")
    return RedirectResponse(url="/", status_code=303)

# 📊 HISTÓRICO DE CHECKLISTS
@app.get("/historico_checklist", response_class=HTMLResponse)
def historico_checklist(request: Request, db: Session = Depends(get_db)):
    checklists = db.query(models.Checklist).order_by(models.Checklist.data_criacao.desc()).all()

    # Lista real de sistemas Supplier no banco
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest","adler","psmm","fmm"]

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

    # ---------------------------------------------------------
    # TIPO DO CHECKLIST
    # ---------------------------------------------------------
    sistemas_supplier = ["denso", "mmh", "pmc", "tiberina", "revest","adler","psmm","fmm"]
    tem_supplier = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema.in_(sistemas_supplier)
    ).first()

    tipo_checklist = "supplier" if tem_supplier else "main"

    # ---------------------------------------------------------
    # CARREGA STATUS E EQUIPAMENTOS OPERANDO
    # ---------------------------------------------------------
    status_equipamentos = db.query(models.StatusEquipamento).all()
    equipamentos_operando = db.query(models.StatusOperacaoChecklist).filter(
        models.StatusOperacaoChecklist.checklist_id == checklist_id
    ).all()

    nomes_operando = {e.nome_equipamento.strip() for e in equipamentos_operando}

    # ---------------------------------------------------------
    # NORMALIZAÇÃO
    # ---------------------------------------------------------
    def normalizar(eq):
        nome = eq.nome_equipamento.strip()
        prefix_map = {
            "Cp": "Compressor", "CP": "Compressor", "Compressor": "Compressor",
            "Bac": "BAC", "BAC": "BAC",
            "Bag": "BAG", "BAG": "BAG",
            "Torre": "Torre",
            "Chiller": "Chiller",
            "Secador": "Secador"   # << NOVO

        }

        partes = nome.split()
        prefixo = prefix_map.get(partes[0], partes[0])
        numero = partes[-1]

        if numero.isdigit():
            numero = f"{int(numero):02d}"

        eq.tipo = prefixo
        eq.nome_padronizado = f"{prefixo} {numero}"
        return eq

    # NORMALIZA AMBAS LISTAS ✔️
    for eq in status_equipamentos:
        normalizar(eq)

    for eq in equipamentos_operando:
        normalizar(eq)

    # RECRIA LISTA DE NOMES OPERANDO JÁ NORMALIZADOS ✔️
    nomes_operando = {e.nome_padronizado for e in equipamentos_operando}

    # ---------------------------------------------------------
    # FILTRA E ORDENA ✔️
    # ---------------------------------------------------------
    def gerar_lista(tipo):
        lista = []
        for eq in status_equipamentos:
            if eq.tipo == tipo:
                eq.status_ok = eq.nome_padronizado in nomes_operando
                lista.append(eq)

        return sorted(lista, key=lambda x: int(x.nome_padronizado.split()[-1]))

    torres = gerar_lista("Torre")
    bac = gerar_lista("BAC")
    bag = gerar_lista("BAG")
    comp = gerar_lista("Compressor")
    chillers = gerar_lista("Chiller")
    secadores = gerar_lista("Secador")


    # ---------------------------------------------------------
    # ITENS DO CHECKLIST (mantido)
    # ---------------------------------------------------------
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

    itens_adler = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "adler"
    ).all()

    itens_psmm = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "psmm"
    ).all()

    itens_fmm = db.query(models.ItemRegistro).filter(
        models.ItemRegistro.checklist_id == checklist_id,
        models.ItemRegistro.sistema == "fmm"
    ).all()

    # ---------------------------------------------------------
    # ENVIA AO TEMPLATE
    # ---------------------------------------------------------
    return templates.TemplateResponse("detalhes_checklist.html", {
        "request": request,
        "checklist": checklist,
        "tipo_checklist": tipo_checklist,

        "torres": torres,
        "bac": bac,
        "bag": bag,
        "comp": comp,
        "chillers": chillers,
        "secadores": secadores, 

        "itens_ar": itens_ar,
        "itens_agua_resfriamento": itens_agua_resfriamento,
        "itens_agua_gelada": itens_agua_gelada,
        "itens_funilaria_climatizacao": itens_funilaria_climatizacao,
        "itens_montagem_climatizacao": itens_montagem_climatizacao,
        "itens_communication_climatizacao": itens_communication_climatizacao,

        "itens_denso": itens_denso,
        "itens_mmh": itens_mmh,
        "itens_pmc": itens_pmc,
        "itens_tiberina": itens_tiberina,   #"adler","psmm","fmm"
        "itens_revest": itens_revest,
        "itens_adler": itens_adler,
        "itens_psmm": itens_psmm,
        "itens_fmm": itens_fmm
    })


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

    from sqlalchemy import func, cast, Integer

    equipamentos = (
    query.order_by(
        cast(func.substring_index(models.StatusEquipamento.nome_equipamento, ' ', -1), Integer)
    ).all()
)

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

from weasyprint import HTML
from io import BytesIO
from datetime import datetime

@app.get("/gerar_pdf_moderno")
def gerar_pdf_moderno(request: Request, checklist_id: int, db: Session = Depends(get_db)):
    checklist = db.query(models.Checklist).filter(models.Checklist.id == checklist_id).first()
    if not checklist:
        return {"detail": "Checklist não encontrado"}

    base_path = os.path.dirname(os.path.abspath(__file__))

    # Caminhos estáticos
    css_path = f"file:///{os.path.join(base_path, 'static', 'pdf_moderno.css').replace(os.sep, '/')}"
    ok_path = f"file:///{os.path.join(base_path, 'static', 'icons', 'ok.png').replace(os.sep, '/')}"
    nok_path = f"file:///{os.path.join(base_path, 'static', 'icons', 'nok.png').replace(os.sep, '/')}"
    logo_path = f"file:///{os.path.join(base_path, 'static', 'logo_stellantis.png').replace(os.sep, '/')}"
    icon_path = f"file:///{os.path.join(base_path, 'static', 'icons', 'checklist.png').replace(os.sep, '/')}"

    # Definir se é Main Plant ou Supplier Park
    tipo_checklist = "main"
    if checklist.tipo_turno and checklist.tipo_turno.lower().strip() == "supplier":
        tipo_checklist = "supplier"

    # Grupos
    grupos = {
        "Ar Comprimido": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Ar Comprimido").all(),
        "Água de Resfriamento": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Água de Resfriamento").all(),
        "Água Gelada": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Água Gelada").all(),
        "Climatização Funilaria": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Climatizacao_f").all(),
        "Climatização Montagem": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Climatizacao_m").all(),
        "Climatização Communication": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="Climatizacao_c").all(),
        "DENSO": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="denso").all(),
        "MMH": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="mmh").all(),
        "PMC": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="pmc").all(),
        "Tiberina": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="tiberina").all(),
        "Revestcoat": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="revest").all(),
        "Adler": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="adler").all(),
        "PSMM": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="psmm").all(),
        "FMM": db.query(models.ItemRegistro).filter_by(checklist_id=checklist_id, sistema="fmm").all(),
    }

    equipamentos_operando = db.query(models.StatusOperacaoChecklist).filter_by(checklist_id=checklist_id).all()

    # Renderização
    html_content = templates.get_template("pdf_moderno.html").render(
        checklist=checklist,
        grupos=grupos,
        equipamentos_operando=equipamentos_operando,
        logo_path=logo_path,
        icon_path=icon_path,
        ok_path=ok_path,
        nok_path=nok_path,
        css_path=css_path,
        tipo_checklist=tipo_checklist,
        now=datetime.now
    )

    # PDF
    pdf_buffer = BytesIO()
    HTML(string=html_content, base_url=f"file:///{base_path.replace(os.sep, '/')}").write_pdf(pdf_buffer)

    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=Checklist_Moderno.pdf"}
    )
