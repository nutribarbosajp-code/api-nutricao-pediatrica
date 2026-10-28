import streamlit as st
import requests

st.set_page_config(page_title="Painel Nutrição Pediátrica", page_icon="👶", layout="wide")

API_URL = "http://127.0.0.1:8000"

st.title("👶 Sistema de Nutrição Pediátrica & Terapia Sensorial")

menu = st.sidebar.radio(
    "Navegação",
    ["Cadastrar Paciente", "Listar Pacientes", "Diário Sensorial & Fotos", "Emitir Laudo PDF"]
)

# --- ABA 1: CADASTRAR PACIENTE ---
if menu == "Cadastrar Paciente":
    st.header("📋 Cadastro do Paciente")
    with st.form("form_paciente"):
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome do Paciente", value="Joãozinho")
            idade = st.number_input("Idade (anos)", min_value=1, max_value=17, value=3)
            peso = st.number_input("Peso (kg)", min_value=1.0, value=12.0)
        with col2:
            altura = st.number_input("Altura (cm)", min_value=30.0, value=85.0)
            nivel_atividade = st.slider("Atividade Física", 1.0, 2.0, 1.3)

        if st.form_submit_button("Salvar Paciente"):
            payload = {
                "nome": nome,
                "idade_anos": idade,
                "peso_kg": peso,
                "altura_cm": altura,
                "nivel_atividade": nivel_atividade
            }
            try:
                res = requests.post(f"{API_URL}/cadastrar-paciente/", json=payload)
                if res.status_code == 200:
                    st.success("Paciente cadastrado com sucesso!")
                else:
                    st.error("Erro ao cadastrar paciente na API.")
            except Exception as e:
                st.error(f"Erro de conexão com a API: {e}")

# --- ABA 2: LISTAR PACIENTES ---
elif menu == "Listar Pacientes":
    st.header("👥 Pacientes Cadastrados")
    if st.button("Atualizar Lista"):
        try:
            res = requests.get(f"{API_URL}/pacientes/")
            if res.status_code == 200:
                st.dataframe(res.json(), use_container_width=True)
            else:
                st.error("Erro ao buscar a lista de pacientes.")
        except Exception as e:
            st.error(f"Erro de conexão com a API: {e}")

# --- ABA 3: DIÁRIO SENSORIAL & FOTOS ---
elif menu == "Diário Sensorial & Fotos":
    st.header("📸 Acompanhamento e Comunicação Família <-> Terapeuta")
    
    # Variável definida no topo do menu para estar disponível em toda a aba
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1)
    
    tab_profissional, tab_familia = st.tabs(["👨‍⚕️ Visão do Profissional (Prescrever)", "👨‍👩‍👧 Visão da Família (Enviar Foto)"])
    
    # Visão do Profissional
    with tab_profissional:
        st.subheader("Prescrever Atividade / Desafio Sensorial para Casa")
        orientacao = st.text_area(
            "Descreva a orientação para a próxima semana:",
            placeholder="Ex: Oferecer brócolis cozido no vapor ao lado do prato. Incentivar apenas a interação visual e o toque."
        )
        if st.button("Enviar Tarefa para os Pais"):
            payload = {"paciente_id": paciente_id, "orientacao_tarefa": orientacao}
            try:
                res = requests.post(f"{API_URL}/comunicacao/prescrever-tarefa/", json=payload)
                if res.status_code == 200:
                    st.success("Orientação enviada para o aplicativo da família!")
                else:
                    st.error("Erro ao prescrever tarefa. Verifique o ID do paciente.")
            except Exception as e:
                st.error(f"Erro de conexão com a API: {e}")

    # Visão da Família
    with tab_familia:
        st.subheader("Registrar Momento da Refeição / Desafio")
        comentario = st.text_input(
            "Como foi a experiência hoje?",
            placeholder="Ex: Aceitou segurar a rodela de cenoura por 10 segundos."
        )
        reacao = st.selectbox(
            "Reação da Criança", 
            [
                "Tolerou (No prato / Perto)", 
                "Tocou", 
                "Cheirou", 
                "Beijou", 
                "Lambeu", 
                "Colocou na boca / Provou", 
                "Comeu / Ingeriu", 
                "Recusou / Cuspiu"
            ]
        )
        foto_upload = st.file_uploader("Enviar Foto do Prato ou da Interação", type=["jpg", "jpeg", "png"])
        
        if st.button("Enviar Registro"):
            files = {"foto": (foto_upload.name, foto_upload.getvalue(), foto_upload.type)} if foto_upload else None
            data = {"paciente_id": paciente_id, "comentario_pais": comentario, "nivel_reacao": reacao}
            try:
                res = requests.post(f"{API_URL}/comunicacao/registrar-oferta-familia/", data=data, files=files)
                if res.status_code == 200:
                    st.success("Foto e registro enviados para o nutricionista!")
                else:
                    st.error("Erro ao enviar registro para a API.")
            except Exception as e:
                st.error(f"Erro de conexão com a API: {e}")

    st.markdown("---")
    st.subheader("📜 Feed de Acompanhamento Terapêutico")
    if st.button("Carregar Feed do Paciente"):
        try:
            res = requests.get(f"{API_URL}/comunicacao/historico/{paciente_id}")
            if res.status_code == 200:
                feed = res.json()["feed"]
                if feed:
                    for item in feed:
                        col_i1, col_i2 = st.columns([3, 1])
                        with col_i1:
                            remetente_label = "👨‍⚕️ Profissional" if item["enviado_por"] == "profissional" else "👨‍👩‍👧 Família"
                            st.markdown(f"**[{item['data']}] {remetente_label}**")
                            st.write(f"**Mensagem:** {item['mensagem']}")
                            st.caption(f"Status/Reação: {item['nivel_reacao']}")
                        with col_i2:
                            if item["foto_url"]:
                                st.image(f"{API_URL}{item['foto_url']}", width=150)
                        st.divider()
                else:
                    st.info("Nenhum registo encontrado para este paciente.")
            else:
                st.error("Erro ao carregar o feed do paciente.")
        except Exception as e:
            st.error(f"Erro de conexão com a API: {e}")

# --- ABA 4: EMITIR LAUDO PDF ---
elif menu == "Emitir Laudo PDF":
    st.header("📄 Download de Laudos")
    paciente_id_pdf = st.number_input("Digite o ID do Paciente", min_value=1, step=1, value=1, key="pdf_id")
    if st.button("Buscar Laudo"):
        try:
            pdf_res = requests.get(f"{API_URL}/pacientes/{paciente_id_pdf}/relatorio-pdf")
            if pdf_res.status_code == 200:
                st.download_button(
                    label="📥 Descarregar Laudo em PDF",
                    data=pdf_res.content,
                    file_name=f"Relatorio_{paciente_id_pdf}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Paciente não encontrado.")
        except Exception as e:
            st.error(f"Erro de conexão com a API: {e}")
