from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="API de Nutrição Pediátrica & Terapia Sensorial",
    description="Ferramenta clínica para cálculo nutricional, hídrico e avaliação de seletividade alimentar."
)

class ItemSensorial(BaseModel):
    alimento: str = Field(..., example="Cenoura crua")
    grupo_alimentar: str = Field(..., example="Vegetais")
    textura: str = Field(..., example="Crocante")
    nivel_aceitacao: str = Field(
        ..., 
        example="Recusa", 
        description="Opções: Recusa, Tolera ver/cheirar, Toca, Lambe, Mastiga e Engole"
    )

class PacientePediatrico(BaseModel):
    nome: str = Field(..., example="Joãozinho")
    idade_anos: int = Field(..., ge=1, le=17, description="Idade entre 1 e 17 anos")
    peso_kg: float = Field(..., gt=0, le=120, description="Peso em kg")
    nivel_atividade: float = Field(1.3, ge=1.0, le=2.0, description="Fator de atividade (1.0 a 2.0)")
    registro_sensorial: Optional[List[ItemSensorial]] = None

def calcular_necessidade_hidrica(peso: float) -> float:
    if peso <= 10:
        return peso * 100
    elif peso <= 20:
        return 1000 + ((peso - 10) * 50)
    else:
        return 1500 + ((peso - 20) * 20)

@app.get("/")
def home():
    return {"mensagem": "API de Nutrição Pediátrica & Terapia Sensorial online!"}

@app.post("/calcular-plano-nutricional/")
def calcular_plano(paciente: PacientePediatrico):
    # Cálculo da Taxa Metabólica Basal (Schofield)
    tmb = (22.7 * paciente.peso_kg) + 495
    tdee = tmb * paciente.nivel_atividade
    
    # Distribuição de macronutrientes
    proteinas_kcal = tdee * 0.15
    gorduras_kcal = tdee * 0.30
    carboidratos_kcal = tdee * 0.55
    
    # Cálculo hídrico
    agua_ml = calcular_necessidade_hidrica(paciente.peso_kg)
    
    # Resumo da avaliação sensorial (se houver registos)
    resumo_sensorial = []
    if paciente.registro_sensorial:
        for item in paciente.registro_sensorial:
            resumo_sensorial.append({
                "alimento": item.alimento,
                "textura": item.textura,
                "status": item.nivel_aceitacao
            })

    return {
        "paciente": paciente.nome,
        "diagnostico_energetico": {
            "tmb_kcal": round(tmb, 2),
            "gasto_energetico_total_kcal": round(tdee, 2)
        },
        "distribuicao_macronutrientes_g": {
            "proteinas": round(proteinas_kcal / 4, 2),
            "gorduras": round(gorduras_kcal / 9, 2),
            "carboidratos": round(carboidratos_kcal / 4, 2)
        },
        "necessidade_hidrica_diaria": {
            "volume_ml": round(agua_ml, 2),
            "litros": round(agua_ml / 1000, 2)
        },
        "avaliacao_sensorial": {
            "total_itens_avaliados": len(resumo_sensorial),
            "detalhes": resumo_sensorial
        }
    }
