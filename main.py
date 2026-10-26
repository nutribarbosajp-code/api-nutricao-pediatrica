import sqlite3
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="API de Nutrição Pediátrica & Terapia Sensorial",
    description="Ferramenta clínica para cálculo nutricional, hídrico e gestão de pacientes com banco de dados."
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
            tmb_kcal REAL NOT NULL,
            tdee_kcal REAL NOT NULL,
            agua_ml REAL NOT NULL
        )
    """)
    conn.commit()
    conn.close()

# Inicializa a tabela assim que a API liga
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
    nivel_atividade: float = Field(1.3, ge=1.0, le=2.0)
    registro_sensorial: Optional[List[ItemSensorial]] = None

# --- FUNÇÕES DE CÁLCULO ---
def calcular_necessidade_hidrica(peso: float) -> float:
    if peso <= 10:
        return peso * 100
    elif peso <= 20:
        return 1000 + ((peso - 10) * 50)
    else:
        return 1500 + ((peso - 20) * 20)

# --- ROTAS DA API ---
@app.get("/")
def home():
    return {"mensagem": "API de Nutrição Pediátrica & Banco de Dados online!"}

@app.post("/cadastrar-paciente/")
def cadastrar_paciente(paciente: PacientePediatrico):
    tmb = (22.7 * paciente.peso_kg) + 495
    tdee = tmb * paciente.nivel_atividade
    agua_ml = calcular_necessidade_hidrica(paciente.peso_kg)
    
    # Salvar no Banco de Dados SQLite
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO pacientes (nome, idade_anos, peso_kg, tmb_kcal, tdee_kcal, agua_ml)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (paciente.nome, paciente.idade_anos, paciente.peso_kg, round(tmb, 2), round(tdee, 2), round(agua_ml, 2)))
    
    paciente_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id_cadastrado": paciente_id,
        "mensagem": f"Paciente {paciente.nome} guardado com sucesso no banco de dados!",
        "plano": {
            "tmb_kcal": round(tmb, 2),
            "gasto_energetico_total_kcal": round(tdee, 2),
            "necessidade_hidrica_ml": round(agua_ml, 2)
        }
    }

@app.get("/pacientes/")
def listar_pacientes():
    # Buscar todos os pacientes salvos no banco
    conn = sqlite3.connect("pacientes.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, idade_anos, peso_kg, tmb_kcal, tdee_kcal, agua_ml FROM pacientes")
    registros = cursor.fetchall()
    conn.close()

    resultado = []
    for reg in registros:
        resultado.append({
            "id": reg[0],
            "nome": reg[1],
            "idade_anos": reg[2],
            "peso_kg": reg[3],
            "tmb_kcal": reg[4],
            "gasto_energetico_total_kcal": reg[5],
            "necessidade_hidrica_ml": reg[6]
        })

    return {"total_pacientes": len(resultado), "pacientes": resultado}
