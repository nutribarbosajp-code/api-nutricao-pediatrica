import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Plataforma de Nutrição Pediátrica & IA", page_icon="👶", layout="wide")

try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "http://127.0.0.1:8000"

# --- FUNÇÃO AUXILIAR: Mapear Nomes -> IDs ---
def obter_mapa_pacientes():
    """Busca a lista de pacientes e retorna um dicionário {Nome: ID}."""
    try:
        res = requests.get(f"{API_URL}/pacientes/")
        if res.status_code == 200:
            pacientes = res.json()
            if pacientes:
                return {p['nome']: p['id'] for p in pacientes}
    except Exception:
        pass
    return {}

mapa_pacientes = obter_mapa_pacientes()

# --- CONTROLO DE SESSÃO / LOGIN ---
if "logado" not in st.session_state:
    st.session_state["logado"] = False
if "tipo_usuario" not in st.session_state:
    st.session_state["tipo_usuario"] = None
if "paciente_id_familia" not in st.session_state:
    st.session_state["paciente_id_familia"] = None
if "nome_paciente_familia" not in st.session_state:
    st.session_state["nome_paciente_familia"] = ""

# ECRÃ DE LOGIN
if not st.session_state["logado"]:
    st.title("👶 Sistema de Nutrição Pediátrica & Terapia Sensorial")
    st.subheader("Acesso à Plataforma")
    
    tab_terapeuta, tab_familia = st.tabs(["👨‍⚕️ Área do Terapeuta", "👨‍👩‍👧 Área da Família"])
    
    with tab_terapeuta:
        with st.form("form_login_terapeuta"):
            senha_prof = st.text_input("Palavra-passe de Acesso Clínico", type="password")
            if st.form_submit_button("Entrar como Terapeuta"):
                if senha_prof == "admin123":
                    st.session_state["logado"] = True
                    st.session_state["tipo_usuario"] = "terapeuta"
                    st.success("Login efetuado com sucesso!")
                    st.rerun()
                else:
                    st.error("Palavra-passe incorreta.")
                    
    with tab_familia:
        with st.form("form_login_familia"):
            if mapa_pacientes:
                nome_pac_sel = st.selectbox("Selecione a Criança", list(mapa_pacientes.keys()))
            else:
                nome_pac_sel = st.text_input("Nome da Criança")
                
            codigo_acesso = st.text_input("Código de Acesso da Família", type="password", help="Código padrão: 1234")
            
            if st.form_submit_button("Entrar como Família"):
                if codigo_acesso == "1234":
                    st.session_state["logado"] = True
                    st.session_state["tipo_usuario"] = "familia"
                    st.session_state["nome_paciente_familia"] = nome_pac_sel
                    st.session_state["paciente_id_familia"] = mapa_pacientes.get(nome_pac_sel, 1)
                    st.success(f"Bem-vindo(a), família de {nome_pac_sel}!")
                    st.rerun()
                else:
                    st.error("Código de acesso incorreto.")

    st.stop()

# --- BARRA LATERAL (MENU FILTRADO POR PERFIL) ---
st.sidebar.title("👶 Painel Principal")
st.sidebar.write(f"**Perfil:** {'👨‍⚕️ Terapeuta' if st.session_state['tipo_usuario'] == 'terapeuta' else f'👨‍👩‍👧 Família de {st.session_state[\"nome_paciente_familia\"]}'}")

if st.sidebar.button("🚪 Sair / Terminar Sessão"):
    st.session_state["logado"] = False
    st.session_state["tipo_usuario"] = None
    st.session_state["paciente_id_familia"] = None
    st.session_state["nome_paciente_familia"] = ""
    st.rerun()

st.sidebar.divider()

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
    opcoes_menu = [
        "Diário Sensorial & Fotos", 
        "Insumos da Sessão 🧺", 
        "Recordatório 24h"
    ]

menu = st.sidebar.radio("Navegação", opcoes_menu)

# Componente auxiliar para selecionar o paciente na visão do Terapeuta
def selecionar_paciente_terapeuta(chave_componente):
    if not mapa_pacientes:
        st.warning("Nenhum paciente cadastrado até ao momento.")
        return None
    nome_sel = st.selectbox("Selecione o Paciente:", list(mapa_pacientes.keys()), key=chave_componente)
    return mapa_pacientes[nome_sel]

# --- ABA 0: PERFIL & BUSCA DE PACIENTES ---
if menu == "Perfil & Busca de Pacientes":
    st.header("📁 Perfil Clínico & Pesquisa de Pacientes")
    if not mapa_pacientes:
        st.info("Ainda não existem pacientes registados no sistema. Vá a 'Cadastrar Paciente' para começar.")
    else:
        nome_sel = st.selectbox("Selecione o Paciente:", list(mapa_pacientes.keys()), key="perfil_sel_pac")
        paciente_id = mapa_pacientes[nome_sel]
        
        try:
            resposta = requests.get(f"{API_URL}/pacientes/")
            pacientes = resposta.json() if resposta.status_code == 200 else []
            dados_paciente = next((p for p in pacientes if p['id'] == paciente_id), None)
            
            if dados_paciente:
                st.markdown("---")
                st.subheader(f"👤 Paciente: {dados_paciente['nome']}")
                col1, col2, col3 = st.columns(3)
                col1.metric("Idade", f"{dados_paciente['idade_anos']} anos")
                col2.metric("Peso", f"{dados_paciente['peso_kg']} kg")
                col3.metric("Altura", f"{dados_paciente['altura_cm']} cm")
                
                st.markdown("### 🥗 Repertório Alimentar Registado")
                rep_resposta = requests.get(f"{API_URL}/repertorio/{paciente_id}")
                if rep_resposta.status_code == 200 and rep_resposta.json():
                    for item in rep_resposta.json():
                        cor_status = "🟢" if "seguro" in item['status'] else "🟡"
                        st.write(f"{cor_status} **{item['alimento']}** — Textura: {item['textura']} | Sabor: {item['sabor']}")
                else:
                    st.info("Nenhum alimento registado no repertório deste paciente.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

# --- ABA: DASHBOARD CLÍNICO ---
elif menu == "Dashboard Clínico 📊":
    st.header("📊 Dashboard Clínico & Evolução Sensorial")
    paciente_id = selecionar_paciente_terapeuta("dash_pac_sel")
    
    if paciente_id and st.button("Carregar Gráficos do Paciente"):
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
            nome = st.text_input("Nome do Paciente")
            idade = st.number_input("Idade (anos)", min_value=1, max_value=17, value=3)
            peso = st.number_input("Peso (kg)", min_value=1.0, value=12.0)
        with col2:
            altura = st.number_input("Altura (cm)", min_value=30.0, value=85.0)
            nivel_atividade = st.slider("Fator de Atividade", 1.0, 2.0, 1.3)
            
        if st.form_submit_button("Salvar Paciente"):
            if not nome:
                st.warning("Por favor, digite o nome do paciente.")
            else:
                payload = {"nome": nome, "idade_anos": idade, "peso_kg": peso, "altura_cm": altura, "nivel_atividade": nivel_atividade}
                try:
                    res = requests.post(f"{API_URL}/cadastrar-paciente/", json=payload)
                    if res.status_code == 200:
                        st.success(f"Paciente {nome} cadastrado com sucesso!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

# --- ABA 2: FICHA DE ANAMNESE ---
elif menu == "Ficha de Anamnese":
    st.header("📝 Ficha de Anamnese Alimentar Infantil")
    paciente_id = selecionar_paciente_terapeuta("ana_pac_sel")
    
    if paciente_id:
        if st.button("Carregar Anamnese Existente"):
            try:
                res_get = requests.get(f"{API_URL}/anamnese/{paciente_id}")
                if res_get.status_code == 200 and res_get.json().get("anamnese"):
                    st.success("Ficha encontrada!")
                    st.json(res_get.json()["anamnese"])
                else:
                    st.warning("Sem ficha registada para este paciente.")
            except Exception as e:
                st.error(f"Erro: {e}")

# --- ABA 3: RECORDATÓRIO 24H ---
elif menu == "Recordatório 24h":
    st.header("🥗 Recordatório Alimentar & Comportamental 24h")
    
    if st.session_state["tipo_usuario"] == "familia":
        paciente_id = st.session_state["paciente_id_familia"]
        st.info(f"Registando para o Paciente: **{st.session_state['nome_paciente_familia']}**")
    else:
        paciente_id = selecionar_paciente_terapeuta("rec_pac_sel")
        
    if paciente_id:
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
    paciente_id = selecionar_paciente_terapeuta("rep_pac_sel")
    
    if paciente_id:
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
        st.info(f"Visualizando insumos para: **{st.session_state['nome_paciente_familia']}**")
    else:
        paciente_id = selecionar_paciente_terapeuta("ins_pac_sel")

    if paciente_id:
        if st.session_state["tipo_usuario"] == "familia":
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
                st.success("Solicitação enviada com sucesso!")

# --- ABA 6: DIÁRIO SENSORIAL & FOTOS ---
elif menu == "Diário Sensorial & Fotos":
    st.header("📸 Diário Sensorial e Envio de Fotos")
    if st.session_state["tipo_usuario"] == "familia":
        paciente_id = st.session_state["paciente_id_familia"]
        st.info(f"Acompanhamento de: **{st.session_state['nome_paciente_familia']}**")
    else:
        paciente_id = selecionar_paciente_terapeuta("com_pac_sel")

    if paciente_id:
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
    paciente_id = selecionar_paciente_terapeuta("pdf_pac_sel")
    
    if paciente_id and st.button("Gerar Laudo PDF"):
        res = requests.get(f"{API_URL}/pacientes/{paciente_id}/relatorio-pdf")
        if res.status_code == 200:
            st.download_button("📥 Descarregar PDF", data=res.content, file_name=f"Relatorio_{paciente_id}.pdf", mime="application/pdf")
        else:
            st.error("Não foi possível gerar o PDF para o paciente selecionado.")
