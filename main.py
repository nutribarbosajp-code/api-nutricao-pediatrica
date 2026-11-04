import io
import os
import sqlite3
import json
import google.generativeai as genai
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
    description="Plataforma clínica completa com gestão de insumos, alertas, anamnese detalhada e IA para pontes alimentares."
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
    
    # Tabela de Anamnese Pediátrica & Sensorial (Atualizada com os novos campos dos modelos)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anamnese (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL UNIQUE,
        nome_responsavel TEXT,
        telefone_responsavel TEXT,
        sexo TEXT,
        data_nascimento TEXT,
        acompanhamento_pediatra TEXT,
        gestacao_planejada TEXT,
        intercorrencias_gestacao TEXT,
        idade_gestacional TEXT,
        tipo_parto TEXT,
        amamentacao TEXT,
        tempo_amamentacao TEXT,
        inicio_ia TEXT,
        metodo_ia TEXT,
        uso_mamadeira TEXT,
        intercorrencias_ia TEXT,
        doencas_existentes TEXT,
        medicacoes TEXT,
        alergias TEXT,
        historico_familiar TEXT,
        comportamentos_alimentares TEXT,
        produtos_industrializados TEXT,
        preferencias_aversoes TEXT,
        ambiente_refeicao TEXT,
        funcionamento_intestinal TEXT,
        escala_bristol TEXT,
        sintomas_gastrointestinais TEXT,
        sono_medicacoes TEXT,
        opiniao_pais TEXT,
        observacoes TEXT,
                -- Novos campos adicionados das imagens:
        habito_movimentar TEXT,
        habito_concentracao TEXT,
        comportamento_diario_comer TEXT,
        padrao_mastigacao TEXT,
        utensilios_usados TEXT,
        frequencia_cafe_manha TEXT,
        freq_frutas TEXT,
        freq_verduras TEXT,
        freq_legumes TEXT,
        freq_industrializados TEXT,
        freq_refrigerante TEXT,
        freq_frituras TEXT,
        freq_carnes TEXT,
        freq_leite_derivados TEXT,
        refeicoes_por_dia TEXT,
        consumo_agua TEXT,
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
    
    # Tabela de Recordatório 24h (Atualizada)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recordatorio (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL,
        refeicao TEXT NOT NULL,
        alimento TEXT NOT NULL,
        quantidade TEXT NOT NULL,
        data_registro TEXT NOT NULL,
        horario TEXT,
        aceitacao TEXT,
        contexto TEXT,
        FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
    )
    """)
    # Adiciona as novas colunas caso a tabela antiga já exista (evita perder pacientes)
    try:
        cursor.execute("ALTER TABLE recordatorio ADD COLUMN horario TEXT DEFAULT '00:00'")
        cursor.execute("ALTER TABLE recordatorio ADD COLUMN aceitacao TEXT DEFAULT 'Não informado'")
        cursor.execute("ALTER TABLE recordatorio ADD COLUMN contexto TEXT DEFAULT 'Não informado'")
    except sqlite3.OperationalError:
        pass # As colunas já existem

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
    nome_responsavel: Optional[str] = None
    telefone_responsavel: Optional[str] = None
    sexo: Optional[str] = None
    data_nascimento: Optional[str] = None
    acompanhamento_pediatra: Optional[str] = None
    gestacao_planejada: Optional[str] = None
    intercorrencias_gestacao: Optional[str] = None
    idade_gestacional: Optional[str] = None
    tipo_parto: Optional[str] = None
    amamentacao: Optional[str] = None
    tempo_amamentacao: Optional[str] = None
    inicio_ia: Optional[str] = None
    metodo_ia: Optional[str] = None
    uso_mamadeira: Optional[str] = None
    intercorrencias_ia: Optional[str] = None
    doencas_existentes: Optional[str] = None
    medicacoes: Optional[str] = None
    alergias: Optional[str] = None
    historico_familiar: Optional[str] = None
    comportamentos_alimentares: Optional[str] = None
    produtos_industrializados: Optional[str] = None
    preferencias_aversoes: Optional[str] = None
    ambiente_refeicao: Optional[str] = None
    funcionamento_intestinal: Optional[str] = None
    escala_bristol: Optional[str] = None
    sintomas_gastrointestinais: Optional[str] = None
    sono_medicacoes: Optional[str] = None
    opiniao_pais: Optional[str] = None
    observacoes: Optional[str] = None
    # Novos campos:
    habito_movimentar: Optional[str] = None
    habito_concentracao: Optional[str] = None
    comportamento_diario_comer: Optional[str] = None
    padrao_mastigacao: Optional[str] = None
    utensilios_usados: Optional[str] = None
    frequencia_cafe_manha: Optional[str] = None
    freq_frutas: Optional[str] = None
    freq_verduras: Optional[str] = None
    freq_legumes: Optional[str] = None
    freq_industrializados: Optional[str] = None
    freq_refrigerante: Optional[str] = None
    freq_frituras: Optional[str] = None
    freq_carnes: Optional[str] = None
    freq_leite_derivados: Optional[str] = None
    refeicoes_por_dia: Optional[str] = None
    consumo_agua: Optional[str] = None

class RecordatorioItem(BaseModel):
    paciente_id: int
    refeicao: str
    alimento: str
    quantidade: str
    horario: str
    aceitacao: str
    contexto: str

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
    return {"mensagem": "API de Nutrição Pediátrica, IA Sensorial & Anamnese Completa Ativa!"}

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
    INSERT OR REPLACE INTO anamnese (
        paciente_id, nome_responsavel, telefone_responsavel, sexo, data_nascimento,
        acompanhamento_pediatra, gestacao_planejada, intercorrencias_gestacao, idade_gestacional,
        tipo_parto, amamentacao, tempo_amamentacao, inicio_ia, metodo_ia, uso_mamadeira,
        intercorrencias_ia, doencas_existentes, medicacoes, alergias, historico_familiar,
        comportamentos_alimentares, produtos_industrializados, preferencias_aversoes,
        ambiente_refeicao, funcionamento_intestinal, escala_bristol, sintomas_gastrointestinais,
        sono_medicacoes, opiniao_pais, observacoes
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        dados.paciente_id, dados.nome_responsavel, dados.telefone_responsavel, dados.sexo, dados.data_nascimento,
        dados.acompanhamento_pediatra, dados.gestacao_planejada, dados.intercorrencias_gestacao, dados.idade_gestacional,
        dados.tipo_parto, dados.amamentacao, dados.tempo_amamentacao, dados.inicio_ia, dados.metodo_ia, dados.uso_mamadeira,
        dados.intercorrencias_ia, dados.doencas_existentes, dados.medicacoes, dados.alergias, dados.historico_familiar,
        dados.comportamentos_alimentares, dados.produtos_industrializados, dados.preferencias_aversoes,
        dados.ambiente_refeicao, dados.funcionamento_intestinal, dados.escala_bristol, dados.sintomas_gastrointestinais,
        dados.sono_medicacoes, dados.opiniao_pais, dados.observacoes
    ))
    conn.commit()
    conn.close()
    return {"mensagem": "Ficha de Anamnese salva com sucesso!"}

@app.get("/anamnese/{paciente_id}")
def obter_anamnese(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT nome_responsavel, telefone_responsavel, sexo, data_nascimento, acompanhamento_pediatra,
           gestacao_planejada, intercorrencias_gestacao, idade_gestacional, tipo_parto, amamentacao,
           tempo_amamentacao, inicio_ia, metodo_ia, uso_mamadeira, intercorrencias_ia, doencas_existentes,
           medicacoes, alergias, historico_familiar, comportamentos_alimentares, produtos_industrializados,
           preferencias_aversoes, ambiente_refeicao, funcionamento_intestinal, escala_bristol,
           sintomas_gastrointestinais, sono_medicacoes, opiniao_pais, observacoes
    FROM anamnese WHERE paciente_id = ?
    """, (paciente_id,))
    reg = cursor.fetchone()
    conn.close()
    if not reg:
        return {"anamnese": None}
    
    return {
        "anamnese": {
            "nome_responsavel": reg[0], "telefone_responsavel": reg[1], "sexo": reg[2], "data_nascimento": reg[3],
            "acompanhamento_pediatra": reg[4], "gestacao_planejada": reg[5], "intercorrencias_gestacao": reg[6],
            "idade_gestacional": reg[7], "tipo_parto": reg[8], "amamentacao": reg[9], "tempo_amamentacao": reg[10],
            "inicio_ia": reg[11], "metodo_ia": reg[12], "uso_mamadeira": reg[13], "intercorrencias_ia": reg[14],
            "doencas_existentes": reg[15], "medicacoes": reg[16], "alergias": reg[17], "historico_familiar": reg[18],
            "comportamentos_alimentares": reg[19], "produtos_industrializados": reg[20], "preferencias_aversoes": reg[21],
            "ambiente_refeicao": reg[22], "funcionamento_intestinal": reg[23], "escala_bristol": reg[24],
            "sintomas_gastrointestinais": reg[25], "sono_medicacoes": reg[26], "opiniao_pais": reg[27], "observacoes": reg[28]
        }
    }

# --- RECORDATÓRIO 24H ---
@app.post("/recordatorio/")
def adicionar_item_recordatorio(item: RecordatorioItem):
    data_atual = datetime.now().strftime("%Y-%m-%d")
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO recordatorio (paciente_id, refeicao, alimento, quantidade, data_registro, horario, aceitacao, contexto)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (item.paciente_id, item.refeicao, item.alimento, item.quantidade, data_atual, item.horario, item.aceitacao, item.contexto))
    conn.commit()
    conn.close()
    return {"mensagem": "Item adicionado ao Recordatório 24h!"}

@app.get("/recordatorio/{paciente_id}")
def obter_recordatorio(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, refeicao, alimento, quantidade, data_registro, horario, aceitacao, contexto 
    FROM recordatorio WHERE paciente_id = ? 
    ORDER BY data_registro DESC, horario DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    conn.close()
    return [{
        "id": r[0], "refeicao": r[1], "alimento": r[2], "quantidade": r[3], 
        "data": r[4], "horario": r[5], "aceitacao": r[6], "contexto": r[7]
    } for r in registros]

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
            "mensagem": "Cadastre pelo menos 1 alimento no 'Repertório Seguro' para ativar a IA."
        }

    lista_seguros = []
    for item in alimentos_seguros:
        lista_seguros.append(f"- {item[0]} (Textura: {item[1]}, Sabor: {item[2]}, Cor: {item[3]}, Temperatura: {item[4]})")
    texto_seguros = "\n".join(lista_seguros)

    prompt = f"""
    És um Nutricionista Pediátrico especialista em Terapia Alimentar, Seletividade e Autismo (TEA).
    O paciente aceita APENAS os seguintes alimentos de forma segura:
    {texto_seguros}

    Baseado no conceito de "Food Chaining" (Pontes Alimentares), sugira 3 novos alimentos para introduzir na dieta.
    A regra principal é: O novo alimento DEVE ter a mesma TEXTURA e SABOR de um dos alimentos seguros. 
    Devolve EXATAMENTE no formato JSON abaixo, sem texto extra antes ou depois, e sem formatação markdown:
    [
    {{
    "baseado_em": "Nome do alimento seguro",
    "sugestao_alimento": "Novo alimento",
    "afinidade_score": "Porcentagem (ex: 90%)",
    "propriedades": "Textura | Sabor | Cor",
    "justificativa_clinica": "Por que esta ponte funciona a nível sensorial e motor"
    }}
    ]
    """

    try:
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        texto_resposta = response.text.replace("```json", "").replace("```", "").strip()
        sugestoes_geradas = json.loads(texto_resposta)
        return {
            "paciente_id": paciente_id, 
            "total_sugestoes": len(sugestoes_geradas), 
            "sugestoes": sugestoes_geradas
        }
    except Exception as e:
        return {
            "paciente_id": paciente_id,
            "total_sugestoes": 0,
            "sugestoes": [],
            "mensagem": f"Ocorreu um erro ao comunicar com a IA: {str(e)}"
        }

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
    return {"mensagem": "Tarefa prescrita!"}

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

import html

# --- LAUDO EM PDF COMPLETO (SANITIZADO E BULLETPROOF) ---
@app.get("/pacientes/{paciente_id}/relatorio-pdf")
def gerar_relatorio_pdf(paciente_id: int):
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    
    # 1. Buscar dados do paciente
    cursor.execute("SELECT nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = ?", (paciente_id,))
    reg_paciente = cursor.fetchone()
    
    if not reg_paciente:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Paciente com ID {paciente_id} não encontrado na base de dados.")

    nome, idade, peso, altura, tmb, tdee, agua = reg_paciente[0], reg_paciente[1], reg_paciente[2], reg_paciente[3], reg_paciente[4], reg_paciente[5], reg_paciente[6]

    # 2. Buscar anamnese de forma segura
    cursor.execute("""
    SELECT doencas_existentes, comportamentos_alimentares, preferencias_aversoes, opiniao_pais
    FROM anamnese WHERE paciente_id = ?
    """, (paciente_id,))
    reg_anamnese = cursor.fetchone()
    
    # 3. Buscar repertório alimentar
    cursor.execute("SELECT alimento, status, textura, sabor FROM repertorio_alimentar WHERE paciente_id = ?", (paciente_id,))
    reg_repertorio = cursor.fetchall()
    
    conn.close()

    try:
        oms = avaliar_curva_crescimento_oms(peso, altura, idade)
        macros = calcular_macronutrientes(tdee)

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=35, bottomMargin=35)
        story = []

        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle('Titulo', parent=styles['Heading1'], fontSize=15, textColor=colors.HexColor('#1E3A8A'), spaceAfter=8)
        subtitulo_style = ParagraphStyle('Subtitulo', parent=styles['Heading2'], fontSize=11, textColor=colors.HexColor('#2563EB'), spaceBefore=8, spaceAfter=4)
        texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#1F2937'), spaceBefore=3)

        # Cabeçalho
        story.append(Paragraph("RELATÓRIO DE NUTRIÇÃO PEDIÁTRICA & TERAPIA SENSORIAL", titulo_style))
        story.append(Spacer(1, 4))

        dados = [
            ["Paciente:", html.escape(str(nome)), "Idade:", f"{idade} anos"],
            ["Peso:", f"{peso} kg", "Altura:", f"{altura} cm"],
            ["TMB:", f"{tmb} kcal/dia", "GET Total:", f"{tdee} kcal/dia"],
            ["Meta Hídrica:", f"{agua} ml/dia", "Classificação OMS:", oms['classificacao_oms']]
        ]
        tabela = Table(dados, colWidths=[110, 155, 120, 155])
        tabela.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tabela)
        story.append(Spacer(1, 6))

        # Avaliação Antropométrica OMS
        story.append(Paragraph("Avaliação Antropométrica & Curvas da OMS", subtitulo_style))
        oms_dados = [
            ["Indicador OMS", "Resultado Obtido", "Interpretação Clínica"],
            ["IMC Calculado", f"{oms['imc']} kg/m²", "Relação Peso x Estatura"],
            ["Escore Z (Z-Score)", oms['z_score'], "Desvio Padrão populacional"],
            ["Percentil Estimado", oms['percentil_estimado'], "Posição na curva de referência"]
        ]
        tabela_oms = Table(oms_dados, colWidths=[130, 140, 270])
        tabela_oms.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tabela_oms)
        story.append(Paragraph(f"<b>Parecer Clínico OMS:</b> {html.escape(oms['orientacao_clinica'])}", texto_style))
        story.append(Spacer(1, 6))

        # Macronutrientes
        story.append(Paragraph("Distribuição Estimada de Macronutrientes", subtitulo_style))
        macro_dados = [
            ["Proteínas (15%)", "Lipídios / Gorduras (30%)", "Carboidratos (55%)"],
            [f"{macros['proteinas_g']} g/dia", f"{macros['lipidios_g']} g/dia", f"{macros['carboidratos_g']} g/dia"]
        ]
        tabela_macro = Table(macro_dados, colWidths=[170, 180, 180])
        tabela_macro.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#059669')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#A7F3D0')),
            ('PADDING', (0,0), (-1,-1), 4),
        ]))
        story.append(tabela_macro)
        story.append(Spacer(1, 6))

        # Anamnese Resumida
        if reg_anamnese and any(reg_anamnese):
            doencas = html.escape(reg_anamnese[0] or 'Não informado')
            comportamentos = html.escape(reg_anamnese[1] or 'Não informado')
            preferencias = html.escape(reg_anamnese[2] or 'Não informado')
            opiniao = html.escape(reg_anamnese[3] or 'Não informado')
            
            story.append(Paragraph("Resumo Clínico & Comportamental (Anamnese)", subtitulo_style))
            anamnese_texto = f"""
            <b>Condições / Doenças:</b> {doencas}<br/>
            <b>Comportamentos Alimentares:</b> {comportamentos}<br/>
            <b>Preferências / Aversões:</b> {preferencias}<br/>
            <b>Expectativa dos Pais:</b> {opiniao}
            """
            story.append(Paragraph(anamnese_texto, texto_style))
            story.append(Spacer(1, 6))

        # Repertório Alimentar
        if reg_repertorio:
            story.append(Paragraph("Repertório Sensorial Mapeado", subtitulo_style))
            rep_dados = [["Alimento", "Status", "Textura", "Sabor"]]
            for item in reg_repertorio:
                rep_dados.append([html.escape(str(item[0])), html.escape(str(item[1])), html.escape(str(item[2])), html.escape(str(item[3]))])
            
            tabela_rep = Table(rep_dados, colWidths=[140, 120, 130, 150])
            tabela_rep.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#D97706')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCD34D')),
                ('PADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(tabela_rep)

        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=Relatorio_{nome}.pdf"})

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro interno na construção do PDF: {str(e)}")
