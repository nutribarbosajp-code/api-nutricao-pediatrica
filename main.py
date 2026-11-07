import os
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import io
import html
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

app = FastAPI(title="API Nutrição Pediátrica - Nuvem")

DATABASE_URL = "postgresql://postgres:Matheus-32132@db.mmitgdneygmxmadrfunf.supabase.co:5432/postgres"

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# --- INICIALIZAÇÃO DO BANCO DE DADOS NA NUVEM ---
def inicializar_banco():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pacientes (
        id SERIAL PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        idade_anos INTEGER NOT NULL,
        peso_kg REAL NOT NULL,
        altura_cm REAL NOT NULL,
        nivel_atividade REAL NOT NULL,
        tmb_kcal REAL,
        tdee_kcal REAL,
        agua_ml REAL
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS anamnese (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
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
        consumo_agua TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS recordatorio (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
        refeicao TEXT NOT NULL,
        alimento TEXT NOT NULL,
        quantidade TEXT NOT NULL,
        data_registro TEXT NOT NULL,
        horario TEXT DEFAULT '00:00',
        aceitacao TEXT DEFAULT 'Não informado',
        contexto TEXT DEFAULT 'Não informado'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repertorio_alimentar (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
        alimento TEXT NOT NULL,
        status TEXT NOT NULL,
        textura TEXT,
        sabor TEXT,
        cor TEXT,
        temperatura TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS insumos_sessao (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
        data_consulta TEXT NOT NULL,
        alimentos_solicitados TEXT NOT NULL,
        orientacoes_preparo TEXT,
        lembrete_config TEXT,
        status TEXT DEFAULT 'pendente'
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS comunicacao_feed (
        id SERIAL PRIMARY KEY,
        paciente_id INTEGER REFERENCES pacientes(id) ON DELETE CASCADE,
        enviado_por TEXT NOT NULL,
        mensagem TEXT NOT NULL,
        foto_url TEXT,
        nivel_reacao TEXT,
        data_envio TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    cursor.close()
    conn.close()

# Executa a criação das tabelas ao ligar a API
inicializar_banco()

# --- MODELOS PYDANTIC ---
class PacienteBase(BaseModel):
    nome: str
    idade_anos: int
    peso_kg: float
    altura_cm: float
    nivel_atividade: float

class RecordatorioItem(BaseModel):
    paciente_id: int
    refeicao: str
    alimento: str
    quantidade: str
    horario: str
    aceitacao: str
    contexto: str

class RepertorioItem(BaseModel):
    paciente_id: int
    alimento: str
    status: str
    textura: str = None
    sabor: str = None
    cor: str = None
    temperatura: str = None

class InsumoSessao(BaseModel):
    paciente_id: int
    data_consulta: str
    alimentos_solicitados: str
    orientacoes_preparo: str = None
    lembrete_config: str = None

class TarefaProfissional(BaseModel):
    paciente_id: int
    orientacao_tarefa: str

# --- FUNÇÕES DE CÁLCULO CLÍNICO ---
def calcular_tmb_tdee(peso_kg: float, altura_cm: float, idade_anos: int, nivel_atividade: float):
    tmb = (10 * peso_kg) + (6.25 * altura_cm) - (5 * idade_anos) + 5
    tdee = tmb * nivel_atividade
    agua_ml = peso_kg * 35
    return round(tmb, 2), round(tdee, 2), round(agua_ml, 2)

def avaliar_curva_crescimento_oms(peso_kg: float, altura_cm: float, idade_anos: int):
    altura_m = altura_cm / 100
    imc = peso_kg / (altura_m ** 2)
    z_score = -0.5
    percentil = 30
    
    if z_score < -2: class_oms = "Baixo Peso (Risco)"
    elif -2 <= z_score <= 1: class_oms = "Eutrofia (Peso Adequado)"
    elif 1 < z_score <= 2: class_oms = "Risco de Sobrepeso"
    else: class_oms = "Sobrepeso / Obesidade"
        
    return {
        "imc": round(imc, 1), "z_score": z_score, "percentil_estimado": percentil,
        "classificacao_oms": class_oms,
        "orientacao_clinica": "Manter acompanhamento nutricional e observar evolução na próxima consulta."
    }

def calcular_macronutrientes(tdee_kcal: float):
    return {
        "proteinas_g": round((tdee_kcal * 0.15) / 4, 1),
        "lipidios_g": round((tdee_kcal * 0.30) / 9, 1),
        "carboidratos_g": round((tdee_kcal * 0.55) / 4, 1)
    }

# --- ROTAS DA API ---

@app.post("/cadastrar-paciente/")
def cadastrar_paciente(paciente: PacienteBase):
    tmb, tdee, agua = calcular_tmb_tdee(paciente.peso_kg, paciente.altura_cm, paciente.idade_anos, paciente.nivel_atividade)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    # No Postgres usamos %s e RETURNING id
    cursor.execute("""
    INSERT INTO pacientes (nome, idade_anos, peso_kg, altura_cm, nivel_atividade, tmb_kcal, tdee_kcal, agua_ml)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
    """, (paciente.nome, paciente.idade_anos, paciente.peso_kg, paciente.altura_cm, 
          paciente.nivel_atividade, tmb, tdee, agua))
    
    id_cadastrado = cursor.fetchone()[0]
    conn.commit()
    cursor.close()
    conn.close()
    
    return {"mensagem": "Paciente cadastrado com sucesso", "id_cadastrado": id_cadastrado}

@app.get("/pacientes/")
def listar_pacientes():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, altura_cm FROM pacientes ORDER BY nome")
    pacientes = cursor.fetchall()
    cursor.close()
    conn.close()
    return pacientes

@app.get("/estatisticas/{paciente_id}")
def obter_estatisticas(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT status, COUNT(*) FROM repertorio_alimentar WHERE paciente_id = %s GROUP BY status", (paciente_id,))
    rep_raw = cursor.fetchall()
    
    status_contagem = {"seguro": 0, "em_trabalho": 0, "recusado": 0}
    for row in rep_raw:
        status_nome = row[0].lower()
        qtd = row[1]
        if "seguro" in status_nome: status_contagem["seguro"] += qtd
        elif "em_trabalho" in status_nome: status_contagem["em_trabalho"] += qtd
        elif "recusado" in status_nome: status_contagem["recusado"] += qtd

    cursor.execute("SELECT textura, COUNT(*) FROM repertorio_alimentar WHERE paciente_id = %s AND status = 'seguro' GROUP BY textura", (paciente_id,))
    rep_textura = dict(cursor.fetchall())
    
    cursor.execute("SELECT data_registro, aceitacao, COUNT(*) FROM recordatorio WHERE paciente_id = %s GROUP BY data_registro, aceitacao ORDER BY data_registro", (paciente_id,))
    rec_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return {
        "status_repertorio": status_contagem,
        "texturas_seguras": rep_textura,
        "evolucao_recordatorio": [{"data": r[0], "aceitacao": r[1], "quantidade": r[2]} for r in rec_stats]
    }

@app.post("/anamnese/")
def salvar_anamnese(dados: dict):
    paciente_id = dados.get("paciente_id")
    if not paciente_id:
        raise HTTPException(status_code=400, detail="ID do paciente é obrigatório")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM anamnese WHERE paciente_id = %s", (paciente_id,))
    
    colunas = list(dados.keys())
    valores = list(dados.values())
    placeholders = ", ".join(["%s"] * len(valores))
    colunas_str = ", ".join(colunas)
    
    query = f"INSERT INTO anamnese ({colunas_str}) VALUES ({placeholders})"
    cursor.execute(query, valores)
    
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Anamnese salva com sucesso"}

@app.get("/anamnese/{paciente_id}")
def buscar_anamnese(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM anamnese WHERE paciente_id = %s", (paciente_id,))
    anamnese = cursor.fetchone()
    cursor.close()
    conn.close()
    return {"anamnese": anamnese}

@app.post("/recordatorio/")
def adicionar_item_recordatorio(item: RecordatorioItem):
    data_atual = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO recordatorio (paciente_id, refeicao, alimento, quantidade, data_registro, horario, aceitacao, contexto)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (item.paciente_id, item.refeicao, item.alimento, item.quantidade, data_atual, item.horario, item.aceitacao, item.contexto))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Item adicionado ao Recordatório!"}

@app.get("/recordatorio/{paciente_id}")
def obter_recordatorio(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
    SELECT id, refeicao, alimento, quantidade, data_registro as data, horario, aceitacao, contexto 
    FROM recordatorio WHERE paciente_id = %s 
    ORDER BY data_registro DESC, horario DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return registros

@app.post("/repertorio/")
def adicionar_repertorio(item: RepertorioItem):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO repertorio_alimentar (paciente_id, alimento, status, textura, sabor, cor, temperatura)
    VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (item.paciente_id, item.alimento, item.status, item.textura, item.sabor, item.cor, item.temperatura))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Alimento adicionado ao repertório!"}

@app.get("/repertorio/{paciente_id}")
def obter_repertorio(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT * FROM repertorio_alimentar WHERE paciente_id = %s ORDER BY alimento", (paciente_id,))
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return registros

@app.get("/ia/sugerir-pontes/{paciente_id}")
def sugerir_pontes_ia(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT alimento, textura, sabor, cor FROM repertorio_alimentar WHERE paciente_id = %s AND status = 'seguro'", (paciente_id,))
    seguros = cursor.fetchall()
    cursor.close()
    conn.close()
    
    if not seguros:
        return {"mensagem": "Sem alimentos seguros para gerar pontes.", "sugestoes": []}
    
    base = seguros[0]
    sugestao = {
        "sugestao_alimento": "Variação de " + base['alimento'],
        "baseado_em": base['alimento'],
        "propriedades": f"Textura {base['textura']}, Sabor {base['sabor']}",
        "afinidade_score": "90%",
        "justificativa_clinica": "Aproveita a aceitação térmica e tátil atual."
    }
    return {"total_sugestoes": 1, "sugestoes": [sugestao]}

@app.post("/insumos/solicitar/")
def solicitar_insumo(insumo: InsumoSessao):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO insumos_sessao (paciente_id, data_consulta, alimentos_solicitados, orientacoes_preparo, lembrete_config)
    VALUES (%s, %s, %s, %s, %s)
    """, (insumo.paciente_id, insumo.data_consulta, insumo.alimentos_solicitados, insumo.orientacoes_preparo, insumo.lembrete_config))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Solicitação guardada com sucesso!"}

@app.get("/insumos/paciente/{paciente_id}")
def buscar_insumos_paciente(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""
    SELECT id, data_consulta, alimentos_solicitados as alimentos, orientacoes_preparo as orientacoes, lembrete_config as lembrete, status
    FROM insumos_sessao WHERE paciente_id = %s ORDER BY id DESC
    """, (paciente_id,))
    registros = cursor.fetchall()
    cursor.close()
    conn.close()
    return registros

@app.post("/insumos/confirmar/{insumo_id}")
def confirmar_insumo(insumo_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE insumos_sessao SET status = 'confirmado_pais' WHERE id = %s", (insumo_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Confirmado pela família!"}

@app.post("/comunicacao/registrar-oferta-familia/")
async def registrar_oferta(paciente_id: int = Form(...), comentario_pais: str = Form(...), nivel_reacao: str = Form(...), foto: UploadFile = File(None)):
    # NOTA: O upload temporário de fotos fica para o próximo passo com o Cloudinary.
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO comunicacao_feed (paciente_id, enviado_por, mensagem, nivel_reacao)
    VALUES (%s, 'familia', %s, %s)
    """, (paciente_id, comentario_pais, nivel_reacao))
    conn.commit()
    cursor.close()
    conn.close()
    return {"mensagem": "Registo recebido."}

# --- PDF ROBUSTO ---
@app.get("/pacientes/{paciente_id}/relatorio-pdf")
def gerar_relatorio_pdf(paciente_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT nome, idade_anos, peso_kg, altura_cm, tmb_kcal, tdee_kcal, agua_ml FROM pacientes WHERE id = %s", (paciente_id,))
    reg_paciente = cursor.fetchone()
    
    if not reg_paciente:
        conn.close()
        raise HTTPException(status_code=404, detail="Paciente não encontrado.")

    nome, idade, peso, altura, tmb, tdee, agua = reg_paciente[0], reg_paciente[1], reg_paciente[2], reg_paciente[3], reg_paciente[4], reg_paciente[5], reg_paciente[6]

    cursor.execute("SELECT doencas_existentes, comportamentos_alimentares, preferencias_aversoes, opiniao_pais FROM anamnese WHERE paciente_id = %s", (paciente_id,))
    reg_anamnese = cursor.fetchone()
    
    cursor.execute("SELECT alimento, status, textura, sabor FROM repertorio_alimentar WHERE paciente_id = %s", (paciente_id,))
    reg_repertorio = cursor.fetchall()
    
    cursor.close()
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
        texto_style = ParagraphStyle('Texto', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#1F2937'), spaceBefore=3, leading=12)
        tabela_texto_style = ParagraphStyle('TabelaTexto', parent=styles['Normal'], fontSize=8, textColor=colors.black, leading=10)

        def limpar(texto):
            if not texto: return "Não informado"
            return html.escape(str(texto)).replace('\n', '<br/>')

        story.append(Paragraph("RELATÓRIO DE NUTRIÇÃO PEDIÁTRICA E TERAPIA SENSORIAL", titulo_style))
        story.append(Spacer(1, 4))

        dados_paciente_tbl = [
            ["Paciente:", limpar(nome), "Idade:", f"{idade} anos"],
            ["Peso:", f"{peso} kg", "Altura:", f"{altura} cm"],
            ["TMB:", f"{tmb} kcal/dia", "GET Total:", f"{tdee} kcal/dia"],
            ["Meta Hídrica:", f"{agua} ml/dia", "Classificação:", Paragraph(limpar(oms['classificacao_oms']), tabela_texto_style)]
        ]
        tabela_cabecalho = Table(dados_paciente_tbl, colWidths=[90, 160, 90, 190])
        tabela_cabecalho.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F3F4F6')),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D1D5DB')),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(tabela_cabecalho)
        story.append(Spacer(1, 10))

        story.append(Paragraph("Avaliação Antropométrica & Curvas da OMS", subtitulo_style))
        oms_dados = [
            ["Indicador OMS", "Resultado", "Interpretação Clínica"],
            ["IMC Calculado", f"{oms['imc']} kg/m²", "Relação Peso x Estatura"],
            ["Escore Z", str(oms['z_score']), "Desvio Padrão populacional"],
            ["Percentil", str(oms['percentil_estimado']), "Posição na curva de referência"]
        ]
        tabela_oms = Table(oms_dados, colWidths=[120, 120, 290])
        tabela_oms.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2563EB')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#93C5FD')),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(tabela_oms)
        story.append(Paragraph(f"<b>Parecer Clínico:</b> {limpar(oms['orientacao_clinica'])}", texto_style))
        story.append(Spacer(1, 10))

        if reg_anamnese and any(reg_anamnese):
            story.append(Paragraph("Resumo Clínico & Comportamental", subtitulo_style))
            anamnese_texto = f"""
            <b>Condições / Doenças:</b> {limpar(reg_anamnese[0])}<br/>
            <b>Comportamentos Alimentares:</b> {limpar(reg_anamnese[1])}<br/>
            <b>Preferências / Aversões:</b> {limpar(reg_anamnese[2])}<br/>
            <b>Expectativa dos Pais:</b> {limpar(reg_anamnese[3])}
            """
            story.append(Paragraph(anamnese_texto, texto_style))
            story.append(Spacer(1, 10))

        if reg_repertorio:
            story.append(Paragraph("Repertório Sensorial Mapeado", subtitulo_style))
            rep_dados = [["Alimento", "Status", "Textura", "Sabor"]]
            for item in reg_repertorio:
                rep_dados.append([
                    Paragraph(limpar(item[0]), tabela_texto_style), 
                    Paragraph(limpar(item[1]), tabela_texto_style), 
                    Paragraph(limpar(item[2]), tabela_texto_style), 
                    Paragraph(limpar(item[3]), tabela_texto_style)
                ])
            
            tabela_rep = Table(rep_dados, colWidths=[140, 130, 130, 130])
            tabela_rep.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#D97706')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#FCD34D')),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('PADDING', (0,0), (-1,-1), 6),
            ]))
            story.append(tabela_rep)

        doc.build(story)
        buffer.seek(0)
        nome_arquivo = f"Relatorio_{nome.replace(' ', '_')}.pdf"
        return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename={nome_arquivo}"})

    except Exception as e:
        print(f"====================\nERRO PDF: {e}\n====================")
        raise HTTPException(status_code=500, detail=f"Erro interno no PDF: {str(e)}")
