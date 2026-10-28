import io
import os
import sqlite3
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ReportLab para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(
    title="API de Nutrição Pediátrica & Terapia Sensorial",
    description="Ferramenta clínica com cálculos de necessidade energética, curvas de crescimento detalhadas (OMS), Z-score, diário sensorial com envio de fotos e relatórios em PDF."
)

# Diretório para salvar fotos das refeições e atividades
UPLOAD_DIR = "uploads_fotos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SQLite) ---
def inicializar_banco():
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    # Tabela de Pacientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            idade_anos INTEGER NOT NULL,
            peso_kg REAL NOT NULL,
            altura_cm REAL NOT NULL,
            tmb_kcal REAL NOT NULL,
            tdee_kcal REAL NOT NULL,
            agua_ml REAL NOT NULL
        )
    """)
    # Tabela de Comunicação e Diário Sensorial (Pais <-> Profissional)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atividades_comunicacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_registro TEXT NOT NULL,
            remetente TEXT NOT NULL, -- 'profissional' ou 'familia'
            mensagem_tarefa TEXT NOT NULL,
            nivel_reacao TEXT, -- Ex: Tocou, Cheirou, Provou, Recusou
            caminho_foto TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)
    conn.commit()
    conn.close()

inicializar_banco()

# --- MODELOS DE DADOS (Pydantic) ---
class ItemSensorial(BaseModel):
    alimento: str = Field(..., example="Cenoura crua")
    grupo_alimentar: str = Field(..., example="Vegetais")
    textura: str = Field(..., example="Crocante")
    nivel_aceitacao: str = Field(..., example="Recusa")

class PacientePediatrico(BaseModel):
    nome: str = Field(..., example="Joãozinho")
    idade_anos: int = Field(..., ge=1, le=17)
    peso_kg: float = Field(..., gt=0, le=120)
    altura_cm: float = Field(..., gt=30, le=200, example=110.0)
    nivel_atividade: float = Field(1.3, ge=1.0, le=2.0)
    registro_sensorial: Optional[List[ItemSensorial]] = None

class TarefaProfissional(BaseModel):
    paciente_id: int
    orientacao_tarefa: str = Field(..., example="Trabalhar aproximação da maçã em rodelas na hora do lanche.")

# --- LÓGICA CLÍNICA E AUXILIARES ---
def calcular_necessidade_hidrica(peso: float) -> float:
    if peso <= 10:
        return peso * 100
    elif peso <= 20:
        return 1000 + ((peso - 10) * 50)
    else:
        return 1500 + ((peso - 20) * 20)

def calcular_macronutrientes(tdee: float):
    return {
        "proteinas_g": round((tdee * 0.15) / 4, 1),
        "lipidios_g": round((tdee * 0.30) / 9, 1),
        "carboidratos_g": round((tdee * 0.55) / 4, 1)
    }

def avaliar_curva_crescimento_oms(peso_kg: float, altura_cm: float, idade_anos: int):
    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m ** 2)
    z_score = (imc - 15.5) / 1.2

    if z_score < -3:
        classificacao, percentil, risco = "Magreza Acentuada", "< P0.1", "Risco severo de desnutrição. Intervenção imediata recomendada."
    elif -3 <= z_score < -2:
        classificacao, percentil, risco = "Magreza", "P0.1 - P3", "Risco moderado de desnutrição. Acompanhamento do ganho ponderal."
    elif -2 <= z_score <= 1:
        classificacao, percentil, risco = "Eutrofia (Adequado)", "P3 - P85", "Crescimento dentro da faixa esperada."
    elif 1 < z_score <= 2:
        classificacao, percentil, risco = "Risco de Sobrepeso", "P85 - P97", "Alerta para hábitos alimentares e incentivo à atividade."
    elif 2 < z_score <= 3:
        classificacao, percentil, risco = "Sobrepeso / Obesidade", "P97 - P99.9", "Readequação do plano alimentar e acompanhamento."
    else:
        classificacao, percentil, risco = "Obesidade Grave", "> P99.9", "Acompanhamento especializado necessário."

    return {
        "imc": round(imc, 2),
        "z_score": f"{z_score:+.1f} SD",
        "percentil_estimado": percentil,
        "classificacao_oms": classificacao,
        "orientacao_clinica": risco
    }

# --- ROTAS DA API ---
@app.get("/")
def home():
    return {"mensagem": "API de Nutrição Pediátrica & Módulo de Comunicação Terapêutica Online!"}

@app.post("/cadastrar-paciente/")
def cadastrar_paciente(paciente: PacientePediatrico):
    tmb = (22.7 * paciente.peso_kg) + 495
    tdee = tmb * paciente.nivel_atividade
    agua_ml = calcular_necessidade_hidrica(paciente.peso_kg)
    
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes (nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (paciente.nome, paciente.idade_anos, paciente.peso_kg, paciente.altura_cm, round(tmb, 2), round(tdee, 2), round(agua_ml, 2)))
    
    paciente_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"id_cadastrado": paciente_id, "mensagem": f"Paciente {paciente.nome} cadastrado com sucesso!"}

@app.get("/pacientes/")
def listar_pacientes():
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes")
    registros = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "nome": r[1], "idade_anos": r[2], "peso_kg": r[3], "altura_cm": r[4]} for r in registros]

# --- NOVAS ROTAS: COMUNICAÇÃO & DIÁRIO SENSORIAL ---

@app.post("/comunicacao/prescrever-tarefa/")
def prescrever_tarefa(tarefa: TarefaProfissional):
    """Permite que o nutricionista envie a atividade de casa antes da próxima sessão."""
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM pacientes WHERE id = ?", (tarefa.paciente_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")
        
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
        INSERT INTO atividades_comunicacao (paciente_id, data_registro, remetente, mensagem_tarefa, nivel_reacao, caminho_foto)
        VALUES (?, ?, 'profissional', ?, 'Orientação Clínica', NULL)
    """, (tarefa.paciente_id, data_atual, tarefa.orientacao_tarefa))
    
    conn.commit()
    conn.close()
    return {"mensagem": "Atividade registrada com sucesso para a família!"}

@app.post("/comunicacao/registrar-oferta-familia/")
async def registrar_oferta_familia(
    paciente_id: int = Form(...),
    comentario_pais: str = Form(...),
    nivel_reacao: str = Form(...),  # Ex: Recusou, Tocou, Provou, Ingeriu
    foto: Optional[UploadFile] = File(None)
):
    """Permite que os pais enviem fotos da refeição e registrem a reação da criança."""
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    caminho_foto_relativo = None
    if foto:
        nome_ficheiro = f"paciente_{paciente_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{foto.filename}"
        caminho_completo = os.path.join(UPLOAD_DIR, nome_ficheiro)
        
        with open(caminho_completo, "wb") as buffer:
            buffer.write(await foto.read())
            
        caminho_foto_relativo = f"/uploads/{nome_ficheiro}"

    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
        INSERT INTO atividades_comunicacao (paciente_id, data_registro, remetente, mensagem_tarefa, nivel_reacao, caminho_foto)
        VALUES (?, ?, 'familia', ?, ?, ?)
    """, (paciente_id, data_atual, comentario_pais, nivel_reacao, caminho_foto_relativo))

    conn.commit()
    conn.close()
    return {"mensagem": "Registro alimentar enviado com sucesso para o profissional!"}

@app.get("/comunicacao/historico/{paciente_id}")
def obter_historico_comunicacao(paciente_id: int):
    """Retorna todo o feed de tarefas e fotos trocadas entre a família e o terapeuta."""
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, data_registro, remetente, mensagem_tarefa, nivel_reacao, caminho_foto
        FROM atividades_comunicacao
        WHERE paciente_id = ?
        ORDER BY id DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    conn.close()

    feed = []
    for reg in registros:
        feed.append({
            "id": reg[0],
            "data": reg[1],
            "enviado_por": reg[2],
            "mensagem": reg[3],
            "nivel_reacao": reg[4],
            "foto_url": reg[5]
        })

    return {"paciente_id": paciente_id, "total_registros": len(feed), "feed": feed}

@app.get("/pacientes/{paciente_id}/relatorio-pdf")
def gerar_relatorio_pdf(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = ?", (paciente_id,))
    reg = cursor.fetchone()
    conn.close()

    if not reg:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    nome, idade, peso, altura, tmb, tdee, agua = reg[1], reg[2], reg[3], reg[4], reg[5], reg[6], reg[7]
    macros = calcular_macronutrientes(tdee)
    avaliacao_oms = avaliar_curva_crescimento_oms(peso, altura, idade)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=35, bottomMargin=35)
    story = []

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#2563EB'), spaceAfter=6)

    story.append(Paragraph("AVALIAÇÃO DE NUTRIÇÃO PEDIÁTRICA & TERAPIA SENSORIAL", titulo_style))
    story.append(Spacer(1, 8))

    dados = [
        ["Paciente:", nome, "Idade:", f"{idade} anos"],
        ["Peso:", f"{peso} kg", "Altura:", f"{altura} cm"],
        ["Meta Hídrica:", f"{agua} ml/dia", "GET Total:", f"{tdee} kcal/dia"]
    ]
    tabela = Table(dados, colWidths=[100, 160, 100, 160])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tabela)
    story.append(Spacer(1, 12))

    story.append(Paragraph("Avaliação Antropométrica (OMS)", subtitulo_style))
    oms_dados = [
        ["IMC", f"{avaliacao_oms['imc']} kg/m²"],
        ["Z-Score", avaliacao_oms['z_score']],
        ["Classificação", avaliacao_oms['classificacao_oms']]
    ]
    tabela_oms = Table(oms_dados, colWidths=[200, 320])
    tabela_oms.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A7F3D0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tabela_oms)

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Relatorio_{nome}.pdf"})
