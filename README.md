# 👶 API de Nutrição Pediátrica & Terapia Sensorial

API clínica desenvolvida em Python para apoio ao diagnóstico nutricional infantil, cálculo de necessidades energéticas e hídricas, distribuição de macronutrientes, triagem de seletividade alimentar e emissão de relatórios profissionais em PDF.

---

## 🚀 Funcionalidades Principais

- **Cálculo de Necessidades Energéticas:** Aplicação da equação de Schofield para Taxa Metabólica Basal (TMB) e estimativa do Gasto Energético Total (GET/TDEE).
- **Distribuição de Macronutrientes:** Cálculo automático das metas diárias em gramas de Proteínas (15%), Lipídios (30%) e Carboidratos (55%).
- **Cálculo Hídrico Automático:** Regra de Holliday-Segar para definição da meta diária de água (ml, litros e conversão em copos).
- **Triagem Sensorial Automatizada:** Análise percentual de recusa alimentar para identificação de risco de seletividade alimentar severa (apoio ao TEA e terapia alimentar).
- **Persistência em Banco de Dados:** Gestão completa de pacientes com banco de dados SQLite (CRUD).
- **Relatório Profissional em PDF:** Geração e download dinâmico de laudos clínicos em PDF formatados para impressão ou envio à família via WhatsApp.

---

## 🛠️ Tecnologias Utilizadas

- **Python 3.10+**
- **FastAPI:** Framework web moderno e de alta performance.
- **Pydantic:** Validação automática e tipagem estrita de dados.
- **SQLite3:** Banco de dados relacional leve para persistência.
- **ReportLab:** Biblioteca para criação e estilização de documentos PDF.
- **Uvicorn:** Servidor ASGI para execução da aplicação.

---

## 📌 Rotas da API (Endpoints)

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/` | Status da API |
| `POST` | `/cadastrar-paciente/` | Cadastra paciente, calcula necessidades nutricionais e analisa perfil sensorial |
| `GET` | `/pacientes/` | Lista todos os pacientes cadastrados no banco de dados |
| `GET` | `/pacientes/{id}` | Busca paciente por ID com divisão diária de macronutrientes |
| `PUT` | `/pacientes/{id}` | Atualiza e recalcula os dados do paciente |
| `DELETE` | `/pacientes/{id}` | Remove um paciente do banco de dados |
| `GET` | `/pacientes/{id}/relatorio` | Gera resumo do relatório em formato JSON/Texto |
| `GET` | `/pacientes/{id}/relatorio-pdf` | Gera e faz o download do relatório oficial formatado em PDF |

---

## ⚙️ Como Executar o Projeto

1. **Clonar o repositório:**
   ```bash
   git clone [https://github.com/nutribarbosajp-code/api-nutricao-pediatrica.git](https://github.com/nutribarbosajp-code/api-nutricao-pediatrica.git)
   cd api-nutricao-pediatrica
