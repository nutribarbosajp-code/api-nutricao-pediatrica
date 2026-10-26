# 👶 API de Nutrição Pediátrica & Terapia Sensorial

API clínica desenvolvida em Python para apoio ao diagnóstico nutricional infantil, cálculo de necessidades energéticas e hídricas, mapeamento de seletividade alimentar e emissão de relatórios formatados.

---

## 🚀 Funcionalidades Principais

- **Cálculo de Necessidades Energéticas:** Aplicação da equação de Schofield para Taxa Metabólica Basal (TMB) e estimativa de Gasto Energético Total (GET/TDEE).
- **Cálculo Hídrico Automático:** Aplicação da regra de Holliday-Segar para definição do volume diário de água (ml/dia e litros).
- **Mapeamento Sensorial:** Registros de aceitação alimentar para acompanhamento em terapia alimentar (seletividade alimentar/TEA).
- **Persistência em Banco de Dados:** Gestão completa de pacientes com banco de dados SQLite (CRUD).
- **Relatório Clínico Formatado:** Geração automática de resumo nutricional e hídrico em formato legível para envio à família.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **FastAPI:** Framework web moderno e de alta performance.
- **Pydantic:** Validação automática e tipagem estrita de dados.
- **SQLite3:** Banco de dados relacional leve para persistência.
- **Uvicorn:** Servidor ASGI para execução da aplicação.

---

## 📌 Rotas da API (Endpoints)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status da API |
| `POST` | `/cadastrar-paciente/` | Cadastra um novo paciente e calcula metas nutricionais/hídricas |
| `GET` | `/pacientes/` | Lista todos os pacientes cadastrados no banco de dados |
| `GET` | `/pacientes/{id}` | Busca um paciente específico pelo ID |
| `PUT` | `/pacientes/{id}` | Atualiza e recalcula os dados de um paciente |
| `DELETE` | `/pacientes/{id}` | Remove um paciente do banco de dados |
| `GET` | `/pacientes/{id}/relatorio` | Gera o relatório clínico formatado do paciente |

---

## ⚙️ Como Executar o Projeto

1. **Clonar o repositório:**
   ```bash
   git clone https://github.com/nutribarbosajp-code/api-nutricao-pediatrica.git
cd api-nutricao-pediatrica

