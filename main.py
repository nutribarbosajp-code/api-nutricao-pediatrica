import io
import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ReportLab para geração de PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

app = FastAPI(
    title="API de Nutrição Pediátrica & Terapia Sensorial",
    description="Ferramenta clínica com cálculos de necessidade energética, curvas de crescimento (OMS), gestão de pacientes e relatórios em PDF."
)

# --- CONFIGURAÇÃO DO BANCO DE DADOS (SQLite) ---
def inicializar_banco():
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
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

# --- FUNÇÕES AUXILIARES E LÓGICA CLÍNICA ---
def calcular_necessidade_hidrica(peso: float) -> float:
    if peso <= 10:
        return peso * 100
    elif peso <= 20:
        return 1000 + ((peso - 10) * 50)
    else:
        return 1500 + ((peso - 20) * 20)

def calcular_macronutrientes(tdee: float):
    ptn_kcal = tdee * 0.15
    lip_kcal = tdee * 0.30
    cho_kcal = tdee * 0.55
    
    return {
        "proteinas_g": round(ptn_kcal / 4, 1),
        "lipidios_g": round(lip_kcal / 9, 1),
        "carboidratos_g": round(cho_kcal / 4, 1)
    }

def avaliar_curva_crescimento_oms(peso_kg: float, altura_cm: float, idade_anos: int):
    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m ** 2)
    
    # Classificação simplificada baseada no IMC para faixas etárias pediátricas
    if imc < 14.0:
        classificacao = "Magreza Acentuada"
        risco = "Alto risco de desnutrição. Requer intervenção nutricional urgente."
    elif 14.0 <= imc < 15.5:
        classificacao = "Magreza"
        risco = "Risco moderado. Acompanhar ganho ponderal."
    elif 15.5 <= imc < 18.0:
        classificacao = "Eutrofia (Adequado)"
        risco = "Estado nutricional adequado para a faixa etária."
    elif 18.0 <= imc < 20.0:
        classificacao = "Sobrepeso"
        risco = "Alerta para hábitos alimentares e estilo de vida."
    else:
        classificacao = "Obesidade"
        risco = "Recomenda-se readequação do plano alimentar e acompanhamento contínuo."

    return {
        "imc": round(imc, 2),
        "classificacao_oms": classificacao,
        "orientacao_clinica": risco
    }

def analisar_perfil_sensorial(itens: Optional[List[ItemSensorial]]):
    if not itens:
        return {"diagnostico": "Sem registro sensorial cadastrado", "alerta": "Nenhum"}
    
    total = len(itens)
    recusas = sum(1 for item in itens if item.nivel_aceitacao.lower() == "recusa")
    percentual_recusa = (recusas / total) * 100

    if percentual_recusa >= 50:
        alerta = "Alto risco de seletividade alimentar severa."
    elif percentual_recusa > 20:
        alerta = "Seletividade moderada. Manter exposição gradual."
    else:
        alerta = "Aceitação alimentar dentro do esperado."

    return {
        "total_avaliados": total,
        "total_recusas": recusas,
        "percentual_recusa": round(percentual_recusa, 1),
        "alerta_clinico": alerta
    }

# --- ROTAS DA API ---
@app.get("/")
def home():
    return {"mensagem": "API de Nutrição Pediátrica com Curvas de Crescimento da OMS online!"}

# 1. CREATE: Cadastrar Paciente
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

    avaliacao_oms = avaliar_curva_crescimento_oms(paciente.peso_kg, paciente.altura_cm, paciente.idade_anos)
    analise_sensorial = analisar_perfil_sensorial(paciente.registro_sensorial)

    return {
        "id_cadastrado": paciente_id,
        "mensagem": f"Paciente {paciente.nome} cadastrado com sucesso!",
        "avaliacao_antropometrica": avaliacao_oms,
        "triagem_sensorial": analise_sensorial
    }

# 2. READ ALL: Listar Todos
@app.get("/pacientes/")
def listar_pacientes():
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes")
    registros = cursor.fetchall()
    conn.close()

    resultado = []
    for reg in registros:
        resultado.append({
            "id": reg[0],
            "nome": reg[1],
            "idade_anos": reg[2],
            "peso_kg": reg[3],
            "altura_cm": reg[4],
            "tmb_kcal": reg[5],
            "gasto_energetico_total_kcal": reg[6],
            "necessidade_hidrica_ml": reg[7]
        })

    return {"total_pacientes": len(resultado), "pacientes": resultado}

# 3. READ ONE: Buscar Paciente por ID
@app.get("/pacientes/{paciente_id}")
def buscar_paciente(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = ?", (paciente_id,))
    reg = cursor.fetchone()
    conn.close()

    if not reg:
        raise HTTPException(status_code=404, detail="Paciente não encontrado no banco de dados.")

    macros = calcular_macronutrientes(reg[6])
    avaliacao_oms = avaliar_curva_crescimento_oms(reg[3], reg[4], reg[2])

    return {
        "id": reg[0],
        "nome": reg[1],
        "idade_anos": reg[2],
        "peso_kg": reg[3],
        "altura_cm": reg[4],
        "tmb_kcal": reg[5],
        "gasto_energetico_total_kcal": reg[6],
        "necessidade_hidrica_ml": reg[7],
        "distribuicao_macronutrientes": macros,
        "avaliacao_antropometrica_oms": avaliacao_oms
    }

# 4. UPDATE: Atualizar Dados do Paciente
@app.put("/pacientes/{paciente_id}")
def atualizar_paciente(paciente_id: int, paciente: PacientePediatrico):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM pacientes WHERE id = ?", (paciente_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Paciente não encontrado para atualização.")

    tmb = (22.7 * paciente.peso_kg) + 495
    tdee = tmb * paciente.nivel_atividade
    agua_ml = calcular_necessidade_hidrica(paciente.peso_kg)

    cursor.execute("""
        UPDATE pacientes
        SET nome = ?, idade_anos = ?, peso_kg = ?, altura_cm = ?, tmb_kcal = ?, tdee_kcal = ?, agua_ml = ?
        WHERE id = ?
    """, (paciente.nome, paciente.idade_anos, paciente.peso_kg, paciente.altura_cm, round(tmb, 2), round(tdee, 2), round(agua_ml, 2), paciente_id))
    
    conn.commit()
    conn.close()

    return {"mensagem": f"Dados do paciente ID {paciente_id} atualizados com sucesso!"}

# 5. DELETE: Remover Paciente
@app.delete("/pacientes/{paciente_id}")
def deletar_paciente(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, nome FROM pacientes WHERE id = ?", (paciente_id,))
    reg = cursor.fetchone()
    if not reg:
        conn.close()
        raise HTTPException(status_code=404, detail="Paciente não encontrado para remoção.")

    cursor.execute("DELETE FROM pacientes WHERE id = ?", (paciente_id,))
    conn.commit()
    conn.close()

    return {"mensagem": f"Paciente '{reg[1]}' (ID: {paciente_id}) foi removido com sucesso."}

# 6. GERAR RELATÓRIO EM PDF COM AVALIAÇÃO OMS
@app.get("/pacientes/{paciente_id}/relatorio-pdf")
def gerar_relatorio_pdf(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = ?", (paciente_id,))
    reg = cursor.fetchone()
    conn.close()

    if not reg:
        raise HTTPException(status_code=404, detail="Paciente não encontrado para geração de PDF.")

    nome, idade, peso, altura, tmb, tdee, agua = reg[1], reg[2], reg[3], reg[4], reg[5], reg[6], reg[7]
    copos_agua = round(agua / 200, 1)
    macros = calcular_macronutrientes(tdee)
    avaliacao_oms = avaliar_curva_crescimento_oms(peso, altura, idade)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []

    styles = getSampleStyleSheet()
    titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=18, textColor=colors.HexColor('#1E3A8A'), spaceAfter=12)
    subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=14, textColor=colors.HexColor('#2563EB'), spaceAfter=8)
    texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=11, spaceAfter=6)

    story.append(Paragraph("AVALIAÇÃO DE NUTRIÇÃO PEDIÁTRICA & CRESCIMENTO", titulo_style))
    story.append(Spacer(1, 10))

    dados = [
        ["Paciente:", nome, "Idade:", f"{idade} anos"],
        ["Peso:", f"{peso} kg", "Altura:", f"{altura} cm"],
        ["IMC:", f"{avaliacao_oms['imc']} kg/m²", "Classificação OMS:", avaliacao_oms['classificacao_oms']],
        ["Meta Hídrica:", f"{agua} ml/dia ({copos_agua} copos)", "GET (Total):", f"{tdee} kcal/dia"]
    ]
    tabela = Table(dados, colWidths=[110, 150, 110, 150])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TEXTCOLOR', (0,0), (-1,-1), colors.HexColor('#1F2937')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tabela)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Distribuição de Macronutrientes Recomendada", subtitulo_style))
    macros_dados = [
        ["Macronutriente", "Percentual", "Gramas Diárias"],
        ["Proteínas", "15%", f"{macros['proteinas_g']} g"],
        ["Lipídios", "30%", f"{macros['lipidios_g']} g"],
        ["Carboidratos", "55%", f"{macros['carboidratos_g']} g"]
    ]
    tabela_macros = Table(macros_dados, colWidths=[180, 150, 190])
    tabela_macros.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
        ('ALIGN', (1,0), (-1,-1), 'CENTER'),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(tabela_macros)
    story.append(Spacer(1, 15))

    story.append(Paragraph("Diagnóstico do Estado Nutricional", subtitulo_style))
    story.append(Paragraph(f"• <b>Avaliação Antropométrica:</b> {avaliacao_oms['orientacao_clinica']}", texto_style))
    story.append(Paragraph("• <b>Hidratação:</b> Distribuir o consumo de água ao longo do dia.", texto_style))
    story.append(Paragraph("• <b>Conduta:</b> Respeitar o ritmo de aceitação e os limites sensoriais do paciente.", texto_style))

    doc.build(story)
    buffer.seek(0)

    filename = f"Relatorio_Nutricional_{nome.replace(' ', '_')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
