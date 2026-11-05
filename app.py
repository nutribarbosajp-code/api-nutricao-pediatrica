import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Plataforma de Nutrição Pediátrica & IA", page_icon="👶", layout="wide")

# Tenta usar a URL do Render configurada no Streamlit. Se não encontrar, usa a local.
try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "http://127.0.0.1:8000"

# --- CONTROLO DE SESSÃO / LOGIN ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "tipo_usuario" not in st.session_state:
    st.session_state["tipo_usuario"] = None  # "terapeuta" ou "familia"
if "paciente_id_familia" not in st.session_state:
    st.session_state["paciente_id_familia"] = 1

# ECRÃ DE LOGIN (Caso não esteja autenticado)
if not st.session_state["logado"]:
    st.title("👶 Sistema de Nutrição Pediátrica & Terapia Sensorial")
    st.subheader("Acesso à Plataforma")
    
    tab_terapeuta, tab_familia = st.tabs(["👨‍⚕️ Área do Terapeuta", "👨‍👩‍👧 Área da Família"])
    
    with tab_terapeuta:
        with st.form("form_login_terapeuta"):
            senha_prof = st.text_input("Palavra-passe de Acesso Clínico", type="password")
            if st.form_submit_button("Entrar como Terapeuta"):
                # Palavra-passe padrão (pode alterar conforme desejar)
                if senha_prof == "admin123":
                    st.session_state["logado"] = True
                    st.session_state["tipo_usuario"] = "terapeuta"
                    st.success("Login efetuado com sucesso!")
                    st.rerun()
                else:
                    st.error("Palavra-passe incorreta.")
                    
    with tab_familia:
        with st.form("form_login_familia"):
            id_pac = st.number_input("ID do Paciente", min_value=1, step=1, value=1)
            codigo_acesso = st.text_input("Código de Acesso da Família", type="password", help="Ex: 1234")
            if st.form_submit_button("Entrar como Família"):
                if codigo_acesso == "1234":  # Código simples de acesso para os pais
                    st.session_state["logado"] = True
                    st.session_state["tipo_usuario"] = "familia"
                    st.session_state["paciente_id_familia"] = id_pac
                    st.success("Acesso confirmado!")
                    st.rerun()
                else:
                    st.error("Código de acesso incorreto.")

    st.stop()  # Interrompe a execução do restante app se não estiver logado

# --- BARRA LATERAL (MENU FILTRADO POR PERFIL) ---
st.sidebar.title("👶 Painel Principal")
st.sidebar.write(f"**Perfil:** {'👨‍⚕️ Terapeuta' if st.session_state['tipo_usuario'] == 'terapeuta' else '👨‍👩‍👧 Família'}")

if st.sidebar.button("🚪 Sair / Terminar Sessão"):
    st.session_state["logado"] = False
    st.session_state["tipo_usuario"] = None
    st.rerun()

st.sidebar.divider()

# Definir as abas visíveis de acordo com o utilizador
if st.session_state["tipo_usuario"] == "terapeuta":
    opcoes_menu = [
        "Perfil & Busca de Pacientes",
        "Dashboard Clínico 📊",
        "Cadastrar Paciente", 
        "Ficha de Anamnese", 
        "Recordatório 24h", 
        "Repertório & Sugestões IA 🤖", 
        "Insumos da Sessão 🧺",
        "Diário Sensorial & Fotos", 
        "Emitir Laudo PDF"
    ]
else:
    # A família acede apenas a estas 3 abas
    opcoes_menu = [
        "Diário Sensorial & Fotos", 
        "Insumos da Sessão 🧺", 
        "Recordatório 24h"
    ]

menu = st.sidebar.radio("Navegação", opcoes_menu)

# Resto do código da aplicação abaixo...

# --- ABA 0: PERFIL & BUSCA DE PACIENTES ---
if menu == "Perfil & Busca de Pacientes":
    st.header("📁 Perfil Clínico & Pesquisa de Pacientes")
    try:
        resposta = requests.get(f"{API_URL}/pacientes/")
        pacientes = resposta.json() if resposta.status_code == 200 else []
    except:
        pacientes = []

    if not pacientes:
        st.info("Ainda não existem pacientes registados no sistema.")
    else:
        opcoes_pacientes = {f"{p['nome']} (ID: {p['id']})": p['id'] for p in pacientes}
        paciente_selecionado_str = st.selectbox("Selecione o Paciente:", list(opcoes_pacientes.keys()))
        paciente_id = opcoes_pacientes[paciente_selecionado_str]
        dados_paciente = next((p for p in pacientes if p['id'] == paciente_id), None)
        
        if dados_paciente:
            st.markdown("---")
            st.subheader(f"👤 Paciente: {dados_paciente['nome']}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Idade", f"{dados_paciente['idade_anos']} anos")
            col2.metric("Peso", f"{dados_paciente['peso_kg']} kg")
            col3.metric("Altura", f"{dados_paciente['altura_cm']} cm")

# --- ABA: DASHBOARD CLÍNICO ---
elif menu == "Dashboard Clínico 📊":
    st.header("📊 Dashboard Clínico & Evolução Sensorial")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="dash_id")
    if st.button("Carregar Gráficos do Paciente"):
        try:
            res = requests.get(f"{API_URL}/estatisticas/{paciente_id}")
            if res.status_code == 200:
                dados = res.json()
                status = dados.get("status_repertorio", {})
                c1, c2, c3 = st.columns(3)
                c1.metric("🟢 Alimentos Seguros", status.get("seguro", 0))
                c2.metric("🟡 Em Trabalho Terapêutico", status.get("em_trabalho", 0))
                c3.metric("🔴 Alimentos Recusados", status.get("recusado", 0))
                
                st.divider()
                col_graf1, col_graf2 = st.columns(2)
                with col_graf1:
                    st.markdown("### Perfil de Texturas (Aceites)")
                    texturas = dados.get("texturas_seguras", {})
                    if texturas:
                        df_tex = pd.DataFrame(list(texturas.items()), columns=["Textura", "Quantidade"])
                        st.bar_chart(df_tex.set_index("Textura"), color="#10B981")
                    else:
                        st.info("Sem dados de texturas seguras.")
                with col_graf2:
                    st.markdown("### Curva de Comportamento nas Refeições")
                    evolucao = dados.get("evolucao_recordatorio", [])
                    if evolucao:
                        df_evo = pd.DataFrame(evolucao)
                        df_pivot = df_evo.pivot(index='data', columns='aceitacao', values='quantidade').fillna(0)
                        st.line_chart(df_pivot)
                    else:
                        st.info("Sem dados de recordatório para gerar a curva.")
        except Exception as e:
            st.error(f"Erro de conexão: {e}")

# --- ABA 1: CADASTRAR PACIENTE ---
elif menu == "Cadastrar Paciente":
    st.header("📋 Cadastro Inicial do Paciente")
    with st.form("form_paciente"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Paciente", value="Joãozinho")
            idade = st.number_input("Idade (anos)", min_value=1, max_value=17, value=3)
            peso = st.number_input("Peso (kg)", min_value=1.0, value=12.0)
        with col2:
            altura = st.number_input("Altura (cm)", min_value=30.0, value=85.0)
            nivel_atividade = st.slider("Fator de Atividade", 1.0, 2.0, 1.3)
            
        if st.form_submit_button("Salvar Paciente"):
            payload = {"nome": nome, "idade_anos": idade, "peso_kg": peso, "altura_cm": altura, "nivel_atividade": nivel_atividade}
            try:
                res = requests.post(f"{API_URL}/cadastrar-paciente/", json=payload)
                if res.status_code == 200:
                    st.success(f"Paciente cadastrado! ID: {res.json()['id_cadastrado']}")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- ABA 2: FICHA DE ANAMNESE ---
elif menu == "Ficha de Anamnese":
    st.header("📝 Ficha de Anamnese Alimentar Infantil")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="ana_id")
    if st.button("Carregar Anamnese"):
        try:
            res_get = requests.get(f"{API_URL}/anamnese/{paciente_id}")
            if res_get.status_code == 200 and res_get.json().get("anamnese"):
                st.success("Ficha encontrada!")
                st.json(res_get.json()["anamnese"])
            else:
                st.warning("Sem ficha registada para este ID.")
        except Exception as e:
            st.error(f"Erro: {e}")

# --- ABA 3: RECORDATÓRIO 24H ---
elif menu == "Recordatório 24h":
    st.header("🥗 Recordatório Alimentar & Comportamental 24h")
    
    # Se for a família, fixa o ID do paciente automaticamente
    if st.session_state["tipo_usuario"] == "familia":
        paciente_id = st.session_state["paciente_id_familia"]
        st.info(f"Registando para o Paciente ID: {paciente_id}")
    else:
        paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rec_id")
        
    tab_reg_rec, tab_ver_rec = st.tabs(["📝 Registar Consumo", "📊 Consultar Diário"])
    with tab_reg_rec:
        with st.form("form_recordatorio"):
            c1, c2 = st.columns(2)
            with c1:
                refeicao = st.selectbox("Qual a refeição?", ["Pequeno-almoço", "Lanche da Manhã", "Almoço", "Lanche da Tarde", "Jantar", "Ceia", "Beliscar / Fora de hora"])
                horario = st.time_input("Horário da Refeição")
            with c2:
                aceitacao = st.selectbox("Nível de Aceitação", ["Comeu tudo", "Comeu mais de metade", "Comeu menos de metade", "Apenas provou", "Recusou totalmente", "Cuspiu/Vomitou"])
                contexto = st.selectbox("Contexto / Ambiente", ["À mesa com a família", "À mesa sozinho", "Assistindo TV / Telas", "Brincando / Em movimento", "Na escola / Creche"])
            alimento = st.text_area("Alimentos Consumidos e Preparação")
            quantidade = st.text_input("Quantidade Estimada")
            
            if st.form_submit_button("Guardar no Recordatório"):
                payload = {
                    "paciente_id": paciente_id, "refeicao": refeicao, "alimento": alimento, 
                    "quantidade": quantidade, "horario": horario.strftime("%H:%M"), 
                    "aceitacao": aceitacao, "contexto": contexto
                }
                try:
                    res = requests.post(f"{API_URL}/recordatorio/", json=payload)
                    if res.status_code == 200:
                        st.success("Refeição registada com sucesso!")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

    with tab_ver_rec:
        if st.button("Atualizar Diário"):
            try:
                res = requests.get(f"{API_URL}/recordatorio/{paciente_id}")
                if res.status_code == 200 and res.json():
                    for reg in res.json():
                        st.markdown(f"### 📅 {reg['data']} às ⏰ {reg['horario']} — **{reg['refeicao']}**")
                        st.write(f"🍽️ **Alimento:** {reg['alimento']} | ⚖️ **Qtd:** {reg['quantidade']}")
                        st.write(f"🎯 **Aceitação:** {reg['aceitacao']} | 🏠 **Contexto:** {reg['contexto']}")
                        st.divider()
            except Exception as e:
                st.error(f"Erro: {e}")

# --- ABA 4: REPERTÓRIO & IA ---
elif menu == "Repertório & Sugestões IA 🤖":
    st.header("🧠 Mapeamento Sensorial & Pontes Alimentares IA")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rep_id")
    tab_cad, tab_ia = st.tabs(["📌 Registar Alimentos", "🤖 IA (Pontes Alimentares)"])
    with tab_ia:
        if st.button("Gerar Sugestões de Pontes"):
            try:
                res = requests.get(f"{API_URL}/ia/sugerir-pontes/{paciente_id}")
                if res.status_code == 200 and res.json().get("sugestoes"):
                    for sug in res.json()["sugestoes"]:
                        st.write(f"🎯 **Sugestão:** {sug['sugestao_alimento']} (Baseado em: {sug['baseado_em']})")
            except Exception as e:
                st.error(f"Erro: {e}")

# --- ABA 5: INSUMOS DA SESSÃO ---
elif menu == "Insumos da Sessão 🧺":
    st.header("🧺 Solicitação de Alimentos para Consulta")
    if st.session_state["tipo_usuario"] == "familia":
        paciente_id = st.session_state["paciente_id_familia"]
        st.info(f"Visualizando insumos para o Paciente ID: {paciente_id}")
        try:
            res = requests.get(f"{API_URL}/insumos/paciente/{paciente_id}")
            if res.status_code == 200 and res.json():
                for item in res.json():
                    st.info(f"📅 **Sessão:** {item['data_consulta']}")
                    st.write(f"🍏 **Alimentos a levar:** {item['alimentos']}")
                    st.write(f"💡 **Preparo:** {item['orientacoes']}")
                    if item['status'] == 'confirmado_pais':
                        st.success("✅ Confirmado que já separou os insumos!")
                    else:
                        if st.button(f"Marcar como Separado (#{item['id']})", key=f"fam_ins_{item['id']}"):
                            requests.post(f"{API_URL}/insumos/confirmar/{item['id']}")
                            st.rerun()
                    st.divider()
        except Exception as e:
            st.error(f"Erro: {e}")
    else:
        paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="ins_prof_id")
        data_sessao = st.date_input("Data da Próxima Sessão")
        alimentos_req = st.text_area("Alimentos Necessários:")
        instrucoes = st.text_input("Instruções:")
        if st.button("Enviar Solicitação"):
            payload = {
                "paciente_id": paciente_id, "data_consulta": str(data_sessao),
                "alimentos_solicitados": alimentos_req, "orientacoes_preparo": instrucoes,
                "lembrete_config": "24h antes"
            }
            requests.post(f"{API_URL}/insumos/solicitar/", json=payload)
            st.success("Enviado com sucesso!")

# --- ABA 6: DIÁRIO SENSORIAL & FOTOS ---
elif menu == "Diário Sensorial & Fotos":
    st.header("📸 Diário Sensorial e Envio de Fotos")
    if st.session_state["tipo_usuario"] == "familia":
        paciente_id = st.session_state["paciente_id_familia"]
        st.info(f"Acompanhamento do Paciente ID: {paciente_id}")
    else:
        paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="com_prof_id")

    comentario = st.text_input("Comentário sobre a experiência:")
    reacao = st.selectbox("Reação", ["Tolerou", "Tocou", "Cheirou", "Provou", "Comeu", "Recusou"])
    foto_upload = st.file_uploader("Foto da Interação", type=["jpg", "png"])
    
    if st.button("Enviar Registro"):
        files = {"foto": (foto_upload.name, foto_upload.getvalue(), foto_upload.type)} if foto_upload else None
        data = {"paciente_id": paciente_id, "comentario_pais": comentario, "nivel_reacao": reacao}
        res = requests.post(f"{API_URL}/comunicacao/registrar-oferta-familia/", data=data, files=files)
        if res.status_code == 200:
            st.success("Registo enviado!")

# --- ABA 7: EMITIR LAUDO PDF ---
elif menu == "Emitir Laudo PDF":
    st.header("📄 Emitir Laudo PDF")
    paciente_id_pdf = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="pdf_id")
    if st.button("Gerar Laudo"):
        res = requests.get(f"{API_URL}/pacientes/{paciente_id_pdf}/relatorio-pdf")
        if res.status_code == 200:
            st.download_button("📥 Descarregar PDF", data=res.content, file_name=f"Relatorio_{paciente_id_pdf}.pdf", mime="application/pdf")
