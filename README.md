# 👶 API de Nutrição Pediátrica & Terapia Sensorial

API clínica desenvolvida em Python para apoio ao diagnóstico nutricional infantil, avaliação do crescimento (padrão OMS), cálculo de necessidades energéticas e hídricas, distribuição de macronutrientes, triagem de seletividade alimentar e emissão de laudos em PDF.

---

## 🚀 Funcionalidades Principais

- **Avaliação de Crescimento e Z-Score (OMS):** Cálculo do IMC para Idade, classificação do estado nutricional (Magreza, Eutrofia, Sobrepeso, Obesidade) e estimativa do Escore Z / Percentil baseado nas diretrizes da Organização Mundial da Saúde.
- **Cálculo de Necessidades Energéticas:** Aplicação da equação de Schofield para Taxa Metabólica Basal (TMB) e estimativa do Gasto Energético Total (GET/TDEE).
- **Distribuição de Macronutrientes:** Cálculo automático das metas diárias em gramas de Proteínas (15%), Lipídios (30%) e Carboidratos (55%).
- **Cálculo Hídrico Automático:** Regra de Holliday-Segar para definição da meta diária de água (ml, litros e equivalente em copos).
- **Triagem Sensorial Automatizada:** Análise percentual de recusa alimentar para identificação do risco de seletividade alimentar severa (suporte ao TEA e terapia alimentar).
- **Persistência em Banco de Dados:** Gestão completa de pacientes com banco de dados relacional SQLite (CRUD completo).
- **Relatório Profissional em PDF:** Geração e download dinâmico de laudos clínicos formatados, incluindo bloco exclusivo para a avaliação antropométrica da OMS.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **FastAPI:** Framework web moderno e de alta performance.
- **Pydantic:** Validação automática e tipagem estrita de dados.
- **SQLite3:** Banco de dados relacional leve para persistência.
- **ReportLab:** Biblioteca para criação e estilização visual de relatórios em PDF.
- **Uvicorn:** Servidor ASGI para execução da aplicação.

---

## 📌 Rotas da API (Endpoints)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status e mensagem de boas-vindas da API |
| `POST` | `/cadastrar-paciente/` | Cadastra o paciente, calcula métricas nutricionais, Z-score e analisa perfil sensorial |
| `GET` | `/pacientes/` | Lista todos os pacientes cadastrados no banco de dados |
| `GET` | `/pacientes/{id}` | Busca paciente por ID com divisão de macronutrientes e avaliação antropométrica OMS |
| `PUT` | `/pacientes/{id}` | Atualiza e recalcula os dados completos do paciente |
| `DELETE` | `/pacientes/{id}` | Remove um paciente do banco de dados |
| `GET` | `/pacientes/{id}/relatorio-pdf` | Gera e faz o download do laudo clínico oficial em formato PDF |

---

## ⚙️ Como Executar o Projeto

1. **Clonar o repositório:**
   ```bash
   git clone [https://github.com/nutribarbosajp-code/api-nutricao-pediatrica.git](https://github.com/nutribarbosajp-code/api-nutricao-pediatrica.git)
   cd api-nutricao-pediatrica
