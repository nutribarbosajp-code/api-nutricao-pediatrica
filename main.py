import io
import os
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# ReportLab para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. INSTÂNCIA DO FASTAPI
app = FastAPI(
    title="API de Nutrição Pediátrica & IA Sensorial",
    description="Plataforma clínica completa com gestão de insumos, alertas, anamnese, recordatório 24h e IA para pontes alimentares."
)

UPLOAD_DIR = "uploads_fotos"
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# --- BASE DE DADOS E TABELAS ---
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
    
    # Tabela de Comunicação e Diário Sensorial
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS atividades_comunicacao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_registro TEXT NOT NULL,
            remetente TEXT NOT NULL,
            mensagem_tarefa TEXT NOT NULL,
            nivel_reacao TEXT,
            caminho_foto TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)
    
    # Tabela de Anamnese Pediátrica & Sensorial
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anamnese (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL UNIQUE,
            historico_clinico TEXT,
            comportamento_refeicao TEXT,
            marcas_especificas TEXT,
            ambiente_refeicao TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)
    
    # Tabela de Recordatório 24h
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS recordatorio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            refeicao TEXT NOT NULL,
            alimento TEXT NOT NULL,
            quantidade TEXT NOT NULL,
            data_registro TEXT NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)
    
    # Tabela de Repertório Alimentar
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS repertorio_alimentar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            alimento TEXT NOT NULL,
            status TEXT NOT NULL,
            textura TEXT NOT NULL,
            sabor TEXT NOT NULL,
            cor TEXT NOT NULL,
            temperatura TEXT NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)

    # Tabela de Solicitação de Insumos / Alimentos para Sessão
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS solicitacoes_insumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER NOT NULL,
            data_consulta TEXT NOT NULL,
            alimentos_solicitados TEXT NOT NULL,
            orientacoes_preparo TEXT,
            status TEXT DEFAULT 'pendente',
            lembrete_config TEXT NOT NULL,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    """)
    
    conn.commit()
    conn.close()

inicializar_banco()

# --- MODELOS DE DADOS ---
class PacientePediatrico(BaseModel):
    nome: str = Field(..., example="Joãozinho")
    idade_anos: int = Field(..., ge=1, le=17)
    peso_kg: float = Field(..., gt=0, le=120)
    altura_cm: float = Field(..., gt=30, le=200)
    nivel_atividade: float = Field(1.3, ge=1.0, le=2.0)

class AnamneseSchema(BaseModel):
    paciente_id: int
    historico_clinico: str
    comportamento_refeicao: str
    marcas_especificas: str
    ambiente_refeicao: str

class RecordatorioItem(BaseModel):
    paciente_id: int
    refeicao: str
    alimento: str
    quantidade: str

class AlimentoRepertorioSchema(BaseModel):
    paciente_id: int
    alimento: str
    status: str
    textura: str
    sabor: str
    cor: str
    temperatura: str

class TarefaProfissional(BaseModel):
    paciente_id: int
    orientacao_tarefa: str

class SolicitacaoInsumoSchema(BaseModel):
    paciente_id: int
    data_consulta: str
    alimentos_solicitados: str
    orientacoes_preparo: str
    lembrete_config: str

# --- BASE DE CONHECIMENTO DE PONTES ALIMENTARES (IA) ---
BANCO_ALIMENTOS_IA = [
    {"alimento": "Chips de Mandioquinha", "textura": "Crocante", "sabor": "Salgado", "cor": "Amarelo/Bege", "temperatura": "Morno", "justificativa": "Ponte sensorial perfeita para crianças que aceitam batata palha ou batata frita pela cor e crocância."},
    {"alimento": "Biscoito de Polvilho", "textura": "Crocante", "sabor": "Salgado", "cor": "Amarelo/Bege", "temperatura": "Frio", "justificativa": "Mantém alta aceitabilidade tátil e oral sem gerar rejeição por umidade."},
    {"alimento": "Cenoura assada em palito", "textura": "Crocante", "sabor": "Doce", "cor": "Laranja", "temperatura": "Morno", "justificativa": "Transição ideal a partir de salgadinhos crocantes amarelos para introduzir vegetais de cor quente."},
    {"alimento": "Purê de Batata com Maçã cozida", "textura": "Pastoso", "sabor": "Doce", "cor": "Amarelo/Bege", "temperatura": "Morno", "justificativa": "Adaptação de textura macia/pastosa neutra para introdução de saborear frutas sem fibras aparentes."},
    {"alimento": "Maçã seca desidratada", "textura": "Crocante", "sabor": "Doce", "cor": "Amarelo/Bege", "temperatura": "Frio", "justificativa": "Excelente ponte entre biscoitos doces industriais e a fruta in natura."},
    {"alimento": "Brócolis empanado no forno", "textura": "Crocante", "sabor": "Salgado", "cor": "Verde", "temperatura": "Quente", "justificativa": "A casca crocante disfarça a textura interna do vegetal verde, facilitando o primeiro contato oral."}
]

# --- AUXILIARES E CALCULADORES CLÍNICOS ---
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
    return {"mensagem": "API de Nutrição Pediátrica, IA Sensorial & Gestão de Insumos Ativa!"}

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
    return {"id_cadastrado": paciente_id, "mensagem": f"Paciente {paciente.nome} cadastrado!"}

@app.get("/pacientes/")
def listar_pacientes():
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm FROM pacientes")
    registros = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "nome": r[1], "idade_anos": r[2], "peso_kg": r[3], "altura_cm": r[4]} for r in registros]

# --- ANAMNESE ---
@app.post("/anamnese/")
def salvar_anamnese(dados: AnamneseSchema):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO anamnese (paciente_id, historico_clinico, comportamento_refeicao, marcas_especificas, ambiente_refeicao)
        VALUES (?, ?, ?, ?, ?)
    """, (dados.paciente_id, dados.historico_clinico, dados.comportamento_refeicao, dados.marcas_especificas, dados.ambiente_refeicao))
    conn.commit()
    conn.close()
    return {"mensagem": "Ficha de Anamnese salva com sucesso!"}

@app.get("/anamnese/{paciente_id}")
def obter_anamnese(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT historico_clinico, comportamento_refeicao, marcas_especificas, ambiente_refeicao FROM anamnese WHERE paciente_id = ?", (paciente_id,))
    reg = cursor.fetchone()
    conn.close()
    if not reg:
        return {"anamnese": None}
    return {
        "historico_clinico": reg[0],
        "comportamento_refeicao": reg[1],
        "marcas_especificas": reg[2],
        "ambiente_refeicao": reg[3]
    }

# --- RECORDATÓRIO 24H ---
@app.post("/recordatorio/")
def adicionar_item_recordatorio(item: RecordatorioItem):
    data_atual = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO recordatorio (paciente_id, refeicao, alimento, quantidade, data_registro)
        VALUES (?, ?, ?, ?, ?)
    """, (item.paciente_id, item.refeicao, item.alimento, item.quantidade, data_atual))
    conn.commit()
    conn.close()
    return {"mensagem": "Item adicionado ao Recordatório 24h!"}

@app.get("/recordatorio/{paciente_id}")
def obter_recordatorio(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, refeicao, alimento, quantidade, data_registro FROM recordatorio WHERE paciente_id = ? ORDER BY id DESC", (paciente_id,))
    registros = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "refeicao": r[1], "alimento": r[2], "quantidade": r[3], "data": r[4]} for r in registros]

# --- REPERTÓRIO ALIMENTAR & MOTOR DE IA SENSORIAL ---
@app.post("/repertorio/")
def adicionar_alimento_repertorio(item: AlimentoRepertorioSchema):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO repertorio_alimentar (paciente_id, alimento, status, textura, sabor, cor, temperatura)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item.paciente_id, item.alimento, item.status, item.textura, item.sabor, item.cor, item.temperatura))
    conn.commit()
    conn.close()
    return {"mensagem": f"Alimento '{item.alimento}' registrado no repertório!"}

@app.get("/repertorio/{paciente_id}")
def listar_repertorio(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, alimento, status, textura, sabor, cor, temperatura FROM repertorio_alimentar WHERE paciente_id = ?", (paciente_id,))
    registros = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "alimento": r[1], "status": r[2], "textura": r[3], "sabor": r[4], "cor": r[5], "temperatura": r[6]} for r in registros]

@app.get("/ia/sugerir-pontes/{paciente_id}")
def sugerir_pontes_alimentares_ia(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT alimento, textura, sabor, cor, temperatura FROM repertorio_alimentar WHERE paciente_id = ? AND status = 'seguro'", (paciente_id,))
    alimentos_seguros = cursor.fetchall()
    conn.close()

    if not alimentos_seguros:
        return {
            "paciente_id": paciente_id,
            "sugestoes": [],
            "mensagem": "Cadastre pelo menos 1 alimento no 'Repertório Seguro' para ativar a Inteligência Artificial Sensorial."
        }

    sugestoes = []
    for seguro in alimentos_seguros:
        nome_seguro, text_s, sab_s, cor_s, temp_s = seguro[0], seguro[1], seguro[2], seguro[3], seguro[4]
        
        for opcao in BANCO_ALIMENTOS_IA:
            score = 0
            if opcao["textura"] == text_s: score += 3
            if opcao["sabor"] == sab_s: score += 2
            if opcao["cor"] == cor_s: score += 2
            if opcao["temperatura"] == temp_s: score += 1

            if score >= 4:
                sugestoes.append({
                    "baseado_em": nome_seguro,
                    "sugestao_alimento": opcao["alimento"],
                    "afinidade_score": f"{int((score/8)*100)}%",
                    "propriedades": f"{opcao['textura']} | {opcao['sabor']} | {opcao['cor']}",
                    "justificativa_clinica": opcao["justificativa"]
                })

    return {"paciente_id": paciente_id, "total_sugestoes": len(sugestoes), "sugestoes": sugestoes}

# --- SOLICITAÇÃO DE INSUMOS & ALERTAS ---
@app.post("/insumos/solicitar/")
def solicitar_insumo_sessao(dados: SolicitacaoInsumoSchema):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO solicitacoes_insumos (paciente_id, data_consulta, alimentos_solicitados, orientacoes_preparo, lembrete_config)
        VALUES (?, ?, ?, ?, ?)
    """, (dados.paciente_id, dados.data_consulta, dados.alimentos_solicitados, dados.orientacoes_preparo, dados.lembrete_config))
    conn.commit()
    conn.close()
    return {"mensagem": "Solicitação enviada e lembretes configurados!"}

@app.get("/insumos/paciente/{paciente_id}")
def obter_insumos_paciente(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, data_consulta, alimentos_solicitados, orientacoes_preparo, status, lembrete_config
        FROM solicitacoes_insumos
        WHERE paciente_id = ?
        ORDER BY id DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "data_consulta": r[1],
            "alimentos": r[2],
            "orientacoes": r[3],
            "status": r[4],
            "lembrete": r[5]
        } for r in registros
    ]

@app.post("/insumos/confirmar/{solicitacao_id}")
def confirmar_preparo_pais(solicitacao_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE solicitacoes_insumos SET status = 'confirmado_pais' WHERE id = ?", (solicitacao_id,))
    conn.commit()
    conn.close()
    return {"mensagem": "Confirmação registrada com sucesso!"}

@app.get("/insumos/alertas-pendentes/")
def verificar_alertas_profissionais():
    """Busca pacientes sem solicitação de alimentos cadastrada."""
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.nome, MAX(s.data_consulta)
        FROM pacientes p
        LEFT JOIN solicitacoes_insumos s ON p.id = s.paciente_id
        GROUP BY p.id
    """)
    pacientes = cursor.fetchall()
    conn.close()

    alertas = []
    hoje_str = datetime.now().strftime("%Y-%m-%d")

    for p in pacientes:
        paciente_id, nome, ultima_data = p[0], p[1], p[2]
        if not ultima_data or ultima_data < hoje_str:
            alertas.append({
                "paciente_id": paciente_id,
                "nome": nome,
                "mensagem": f"Atenção: O paciente {nome} (ID {paciente_id}) não possui alimentos solicitados para a próxima sessão!"
            })

    return {"total_alertas": len(alertas), "alertas": alertas}

# --- COMUNICAÇÃO ---
@app.post("/comunicacao/prescrever-tarefa/")
def prescrever_tarefa(tarefa: TarefaProfissional):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    data_atual = datetime.now().strftime("%Y-%m-%d %H:%M")
    cursor.execute("""
        INSERT INTO atividades_comunicacao (paciente_id, data_registro, remetente, mensagem_tarefa, nivel_reacao, caminho_foto)
        VALUES (?, ?, 'profissional', ?, 'Orientação Clínica', NULL)
    """, (tarefa.paciente_id, data_atual, tarefa.orientacao_tarefa))
    conn.commit()
    conn.close()
    return {"mensagem": "Tarefa prescrevida!"}

@app.post("/comunicacao/registrar-oferta-familia/")
async def registrar_oferta_familia(
    paciente_id: int = Form(...),
    comentario_pais: str = Form(...),
    nivel_reacao: str = Form(...),
    foto: Optional[UploadFile] = File(None)
):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
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
    return {"mensagem": "Registro enviado!"}

@app.get("/comunicacao/historico/{paciente_id}")
def obter_historico_comunicacao(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, data_registro, remetente, mensagem_tarefa, nivel_reacao, caminho_foto FROM atividades_comunicacao WHERE paciente_id = ? ORDER BY id DESC", (paciente_id,))
    registros = cursor.fetchall()
    conn.close()
    return {"feed": [{"id": r[0], "data": r[1], "enviado_por": r[2], "mensagem": r[3], "nivel_reacao": r[4], "foto_url": r[5]} for r in registros]}

# --- LAUDO EM PDF COMPLETO COM OMS E MACRONUTRIENTES ---
@app.get("/pacientes/{paciente_id}/relatorio-pdf")
def gerar_relatorio_pdf(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = ?", (paciente_id,))
    reg = cursor.fetchone()
    conn.close()

    if not reg:
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    nome, idade, peso, altura, tmb, tdee, agua = reg[0], reg[1], reg[2], reg[3], reg[4], reg[5], reg[6]
    
    oms = avaliar_curva_crescimento_oms(peso, altura, idade)
    macros = calcular_macronutrientes(tdee)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=35, bottomMargin=35)
    story = []

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=16, textColor=colors.HexColor('#1E3A8A'), spaceAfter=10)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=12, textColor=colors.HexColor('#2563EB'), spaceBefore=10, spaceAfter=6)
    texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#1F2937'), spaceBefore=4)

    story.append(Paragraph("RELATÓRIO DE NUTRIÇÃO PEDIÁTRICA & TERAPIA SENSORIAL", titulo_style))
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
    story.append(Spacer(1, 10))

    story.append(Paragraph("Avaliação Antropométrica (Curvas da OMS)", subtitulo_style))
    oms_dados = [
        ["Indicador OMS", "Resultado Obtido"],
        ["IMC Calculado", f"{oms['imc']} kg/m²"],
        ["Escore Z (Z-Score)", oms['z_score']],
        ["Percentil Estimado", oms['percentil_estimado']],
        ["Classificação Nutricional", oms['classificacao_oms']]
    ]
    tabela_oms = Table(oms_dados, colWidths=[220, 300])
    tabela_oms.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tabela_oms)
    story.append(Paragraph(f"<b>Parecer Clínico OMS:</b> {oms['orientacao_clinica']}", texto_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Distribuição Estimada de Macronutrientes", subtitulo_style))
    macro_dados = [
        ["Proteínas (15%)", "Lipídios / Gorduras (30%)", "Carboidratos (55%)"],
        [f"{macros['proteinas_g']} g/dia", f"{macros['lipidios_g']} g/dia", f"{macros['carboidratos_g']} g/dia"]
    ]
    tabela_macro = Table(macro_dados, colWidths=[170, 180, 170])
    tabela_macro.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A7F3D0')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(tabela_macro)

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Relatorio_{nome}.pdf"})
