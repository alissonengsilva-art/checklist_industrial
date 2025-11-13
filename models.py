from datetime import datetime, timedelta, timezone
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from database import Base

# 🕒 Definir o fuso horário de Brasília (UTC -3)
brasil_tz = timezone(timedelta(hours=-3))

# =========================================================
# 📋 TABELA CHECKLIST PRINCIPAL
# =========================================================
class Checklist(Base):
    __tablename__ = "checklist"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    tecnico = Column(String(80))
    especialidade_tecnico = Column(String(80))
    team_leader = Column(String(80))
    especialidade_team_leader = Column(String(80))
    turno = Column(String(40))
    tipo_turno = Column(String(40))
    data_criacao = Column(DateTime, default=lambda: datetime.now(brasil_tz))

    registros = relationship("ItemRegistro", back_populates="checklist")
    status_operacoes = relationship("StatusOperacaoChecklist", back_populates="checklist")

# =========================================================
# 🧾 ITENS FIXOS DO CHECKLIST (MODELO BASE)
# =========================================================
class ItemChecklist(Base):
    __tablename__ = "itens_checklist"

    id = Column(Integer, primary_key=True, index=True)
    sistema = Column(String(80))
    descricao = Column(String(120))
    unidade = Column(String(10))
    valor_min = Column(Float)
    valor_max = Column(Float)

# =========================================================
# 🧾 ITENS REGISTRADOS EM CADA CHECKLIST
# =========================================================
class ItemRegistro(Base):
    __tablename__ = "itens_registro"

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("checklist.id"))
    sistema = Column(String(80))
    descricao = Column(String(120))
    unidade = Column(String(10))
    valor_min = Column(Float)
    valor_max = Column(Float)
    valor_registrado = Column(Float, nullable=True)
    status_ok = Column(Boolean, nullable=True)
    comentario = Column(String(255), nullable=True)

    checklist = relationship("Checklist", back_populates="registros")

# =========================================================
# ⚙️ STATUS GERAL DOS EQUIPAMENTOS
# =========================================================
class StatusEquipamento(Base):
    __tablename__ = "status_equipamentos"

    id = Column(Integer, primary_key=True, index=True)
    nome_equipamento = Column(String(100))
    tipo = Column(String(50))
    status = Column(String(20), default="OK")
    observacao = Column(String(255))
    tecnico = Column(String(80))
    data_atualizacao = Column(DateTime, default=lambda: datetime.now(brasil_tz))

    historicos = relationship("HistoricoStatus", back_populates="equipamento")

# =========================================================
# 📊 HISTÓRICO DE ALTERAÇÃO DE STATUS
# =========================================================
class HistoricoStatus(Base):
    __tablename__ = "historico_status"

    id = Column(Integer, primary_key=True, index=True)
    equipamento_id = Column(Integer, ForeignKey("status_equipamentos.id"))
    status_anterior = Column(String(20))
    status_novo = Column(String(20))
    observacao = Column(String(255))
    tecnico = Column(String(80))
    data_modificacao = Column(DateTime, default=lambda: datetime.now(brasil_tz))

    equipamento = relationship("StatusEquipamento", back_populates="historicos")

# =========================================================
# 🏭 STATUS DOS EQUIPAMENTOS NO MOMENTO DO CHECKLIST
# =========================================================
class StatusOperacaoChecklist(Base):
    __tablename__ = "status_operacao_checklist"
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, index=True)
    checklist_id = Column(Integer, ForeignKey("checklist.id"))
    nome_equipamento = Column(String(100))
    tipo = Column(String(50))
    status = Column(String(20))  # Operando, Parado, Manutenção
    tecnico = Column(String(80))
    turno = Column(String(40))
    data_registro = Column(DateTime, default=datetime.now)

    checklist = relationship("Checklist", back_populates="status_operacoes")
