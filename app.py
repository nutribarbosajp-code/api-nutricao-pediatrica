import streamlit as st
import requests

st.set_page_config(page_title="Plataforma de Nutrição Pediátrica & IA", page_icon="👶", layout="wide")

# Tenta usar a URL do Render configurada no Streamlit. Se não encontrar (testando no PC), usa a local.
try:
    API_URL = st.secrets["API_URL"]
except:
    API_URL = "http://127.0.0.1:8000"


st.title("👶 Sistema de Nutrição Pediátrica, Terapia Sensorial & IA")

menu = st.sidebar.radio(
    "Navegação",
    [
        "Cadastrar Paciente", 
        "Ficha de Anamnese", 
        "Recordatório 24h", 
        "Repertório & Sugestões IA 🤖", 
        "Insumos da Sessão 🧺",
        "Diário Sensorial & Fotos", 
        "Emitir Laudo PDF"
    ]
)

# --- ABA 1: CADASTRAR PACIENTE ---
if menu == "Cadastrar Paciente":
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
    st.header("📝 Ficha de Anamnese Pediátrica & Sensorial")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="ana_id")
    
    with st.form("form_anamnese"):
        historico = st.text_area("Histórico Clínico / Diagnósticos (ex: TEA, TDAH, APLV):")
        comportamento = st.text_area("Comportamento na Mesa / Recusas Principais:")
        marcas = st.text_input("Exige Marcas/Embalagens Específicas? Se sim, quais?")
        ambiente = st.text_input("Ambiente das Refeições (ex: come no sofá, com telas):")
        
        if st.form_submit_button("Guardar Anamnese"):
            payload = {
                "paciente_id": paciente_id,
                "historico_clinico": historico,
                "comportamento_refeicao": comportamento,
                "marcas_especificas": marcas,
                "ambiente_refeicao": ambiente
            }
            try:
                res = requests.post(f"{API_URL}/anamnese/", json=payload)
                if res.status_code == 200:
                    st.success("Ficha de Anamnese guardada com sucesso!")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- ABA 3: RECORDATÓRIO 24H ---
elif menu == "Recordatório 24h":
    st.header("🥗 Recordatório Alimentar de 24 Horas")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rec_id")
    
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        refeicao = st.selectbox("Refeição", ["Pequeno-almoço", "Lanche da Manhã", "Almoço", "Lanche da Tarde", "Jantar", "Ceia"])
        alimento = st.text_input("Alimento / Preparação", placeholder="Ex: Leite com achocolatado")
        quantidade = st.text_input("Quantidade Consumida", placeholder="Ex: 200ml")
        
        if st.button("Adicionar ao Recordatório"):
            payload = {"paciente_id": paciente_id, "refeicao": refeicao, "alimento": alimento, "quantidade": quantidade}
            try:
                res = requests.post(f"{API_URL}/recordatorio/", json=payload)
                if res.status_code == 200:
                    st.success("Item adicionado!")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")
                
    with col_r2:
        st.subheader("Diário Consumido nas últimas 24h")
        if st.button("Ver Recordatório"):
            try:
                res = requests.get(f"{API_URL}/recordatorio/{paciente_id}")
                if res.status_code == 200:
                    st.dataframe(res.json(), use_container_width=True)
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- ABA 4: REPERTÓRIO ALIMENTAR & SUGESTÕES IA 🤖 ---
elif menu == "Repertório & Sugestões IA 🤖":
    st.header("🧠 Mapeamento Sensorial e Sugestões de Pontes por IA")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rep_id")
    
    tab_cad, tab_ia = st.tabs(["📌 Registar Alimentos no Repertório", "🤖 Motor de IA (Pontes Alimentares)"])
    
    with tab_cad:
        st.subheader("Mapear Propriedades Sensoriais dos Alimentos")
        with st.form("form_rep"):
            alim_nome = st.text_input("Nome do Alimento", placeholder="Ex: Batata Frita")
            status_alim = st.selectbox("Status no Tratamento", ["seguro", "em_trabalho", "recusado"])
            
            c1, c2, c3, c4 = st.columns(4)
            with c1: text_opt = st.selectbox("Textura", ["Crocante", "Macio", "Pastoso", "Liquido", "Seco"])
            with c2: sab_opt = st.selectbox("Sabor", ["Salgado", "Doce", "Azedo", "Neutro"])
            with c3: cor_opt = st.selectbox("Cor Dominante", ["Amarelo/Bege", "Verde", "Vermelho", "Laranja", "Escuro"])
            with c4: temp_opt = st.selectbox("Temperatura", ["Quente", "Morno", "Frio", "Gelado"])
            
            if st.form_submit_button("Adicionar ao Repertório"):
                payload = {
                    "paciente_id": paciente_id,
                    "alimento": alim_nome,
                    "status": status_alim,
                    "textura": text_opt,
                    "sabor": sab_opt,
                    "cor": cor_opt,
                    "temperatura": temp_opt
                }
                try:
                    res = requests.post(f"{API_URL}/repertorio/", json=payload)
                    if res.status_code == 200:
                        st.success("Alimento registado no repertório sensorial!")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")

    with tab_ia:
        st.subheader("💡 Algoritmo de Pontes Alimentares (Food Chaining)")
        st.caption("A IA compara os atributos dos alimentos que a criança aceita com segurança para indicar os próximos passos terapêuticos.")
        
        if st.button("Gerar Sugestões de Pontes com IA"):
            try:
                res = requests.get(f"{API_URL}/ia/sugerir-pontes/{paciente_id}")
                if res.status_code == 200:
                    dados_ia = res.json()
                    if dados_ia["sugestoes"]:
                        st.success(f"{dados_ia['total_sugestoes']} sugestão(ões) gerada(s) com sucesso!")
                        for sug in dados_ia["sugestoes"]:
                            with st.expander(f"🎯 Sugestão: {sug['sugestao_alimento']} (Afinidade: {sug['afinidade_score']})"):
                                st.write(f"**Baseado no alimento seguro:** {sug['baseado_em']}")
                                st.write(f"**Propriedades em comum:** {sug['propriedades']}")
                                st.info(f"**Justificativa Clínica:** {sug['justificativa_clinica']}")
                    else:
                        st.warning(dados_ia.get("mensagem", "Nenhuma ponte encontrada."))
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- ABA 5: INSUMOS DA SESSÃO 🧺 ---
elif menu == "Insumos da Sessão 🧺":
    st.header("🧺 Solicitação de Alimentos para Consulta & Lembretes")
    
    # Alertas automáticos para o profissional
    try:
        res_alertas = requests.get(f"{API_URL}/insumos/alertas-pendentes/")
        if res_alertas.status_code == 200:
            dados_alertas = res_alertas.json()
            if dados_alertas["total_alertas"] > 0:
                st.warning("🔔 **Lembrete Clínico:** Pacientes sem alimentos solicitados para a próxima sessão:")
                for alerte in dados_alertas["alertas"]:
                    st.caption(f"⚠️ {alerte['mensagem']}")
    except Exception as e:
        pass

    st.divider()
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="ins_id")
    
    tab_solicitar, tab_pais_insumos = st.tabs(["👨‍⚕️ Solicitar Alimentos (Terapeuta)", "👨‍👩‍👧 Lista da Próxima Sessão (Pais)"])
    
    with tab_solicitar:
        st.subheader("Cadastrar Lista de Insumos para a Próxima Terapia")
        data_sessao = st.date_input("Data da Próxima Sessão")
        alimentos_req = st.text_area("Alimentos Necessários:", placeholder="Ex: 1 Maçã Fuji, 1 pacote de Biscoito de Polvilho")
        instrucoes = st.text_input("Instruções de Higiene / Corte:", placeholder="Ex: Trazer cortado em rodelas num pote fechado")
        lembrete = st.selectbox("Frequência dos Lembretes Automáticos", ["24h antes da sessão", "48h e 24h antes", "No dia anterior e às 07:00 do dia da sessão"])
        
        if st.button("Enviar Solicitação com Lembretes"):
            payload = {
                "paciente_id": paciente_id,
                "data_consulta": str(data_sessao),
                "alimentos_solicitados": alimentos_req,
                "orientacoes_preparo": instrucoes,
                "lembrete_config": lembrete
            }
            try:
                res = requests.post(f"{API_URL}/insumos/solicitar/", json=payload)
                if res.status_code == 200:
                    st.success("Solicitação enviada e lembretes programados com sucesso!")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

    with tab_pais_insumos:
        st.subheader("📌 Alimentos a Levar na Próxima Consulta")
        try:
            res = requests.get(f"{API_URL}/insumos/paciente/{paciente_id}")
            if res.status_code == 200:
                lista = res.json()
                if lista:
                    for item in lista:
                        st.info(f"📅 **Sessão do Dia:** {item['data_consulta']}")
                        st.write(f"🍏 **Alimentos:** {item['alimentos']}")
                        st.write(f"💡 **Como preparar/trazer:** {item['orientacoes']}")
                        st.caption(f"⏰ Lembrete configurado: {item['lembrete']}")
                        
                        if item['status'] == 'confirmado_pais':
                            st.success("✅ A família já confirmou que separou estes alimentos!")
                        else:
                            if st.button(f"Marcar como Separado / Comprado (Item #{item['id']})"):
                                res_conf = requests.post(f"{API_URL}/insumos/confirmar/{item['id']}")
                                if res_conf.status_code == 200:
                                    st.success("Confirmado! O terapeuta já foi notificado.")
                                    st.rerun()
                        st.divider()
                else:
                    st.write("Nenhuma solicitação de alimento pendente para a próxima sessão.")
        except Exception as e:
            st.error(f"Erro de conexão: {e}")

# --- ABA 6: DIÁRIO SENSORIAL & FOTOS ---
elif menu == "Diário Sensorial & Fotos":
    st.header("📸 Acompanhamento Família <-> Terapeuta")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="com_id")
    
    tab_prof, tab_fam = st.tabs(["👨‍⚕️ Prescrever Tarefa", "👨‍👩‍👧 Enviar Foto (Família)"])
    
    with tab_prof:
        orientacao = st.text_area("Orientação de Casa:")
        if st.button("Enviar Tarefa"):
            try:
                res = requests.post(f"{API_URL}/comunicacao/prescrever-tarefa/", json={"paciente_id": paciente_id, "orientacao_tarefa": orientacao})
                if res.status_code == 200: st.success("Tarefa enviada!")
            except Exception as e: st.error(f"Erro: {e}")

    with tab_fam:
        comentario = st.text_input("Comentário sobre a experiência:")
        reacao = st.selectbox("Reação", ["Tolerou (No prato / Perto)", "Tocou", "Cheirou", "Beijou", "Lambeu", "Colocou na boca / Provou", "Comeu / Ingeriu", "Recusou / Cuspiu"])
        foto_upload = st.file_uploader("Foto da Interação", type=["jpg", "jpeg", "png"])
        if st.button("Enviar Registro"):
            files = {"foto": (foto_upload.name, foto_upload.getvalue(), foto_upload.type)} if foto_upload else None
            data = {"paciente_id": paciente_id, "comentario_pais": comentario, "nivel_reacao": reacao}
            try:
                res = requests.post(f"{API_URL}/comunicacao/registrar-oferta-familia/", data=data, files=files)
                if res.status_code == 200: st.success("Registro enviado!")
            except Exception as e: st.error(f"Erro: {e}")

    st.markdown("---")
    if st.button("Carregar Feed"):
        try:
            res = requests.get(f"{API_URL}/comunicacao/historico/{paciente_id}")
            if res.status_code == 200:
                for item in res.json()["feed"]:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**[{item['data']}] {'👨‍⚕️ Profissional' if item['enviado_por'] == 'profissional' else '👨‍👩‍👧 Família'}**")
                        st.write(f"**Mensagem:** {item['mensagem']}")
                        st.caption(f"Status: {item['nivel_reacao']}")
                    with col2:
                        if item["foto_url"]: st.image(f"{API_URL}{item['foto_url']}", width=150)
                    st.divider()
        except Exception as e: st.error(f"Erro: {e}")

# --- ABA 7: EMITIR LAUDO PDF ---
elif menu == "Emitir Laudo PDF":
    st.header("📄 Emitir Laudo")
    paciente_id_pdf = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="pdf_id")
    if st.button("Buscar Laudo"):
        try:
            pdf_res = requests.get(f"{API_URL}/pacientes/{paciente_id_pdf}/relatorio-pdf")
            if pdf_res.status_code == 200:
                st.download_button("📥 Descarregar Laudo em PDF", data=pdf_res.content, file_name=f"Relatorio_{paciente_id_pdf}.pdf", mime="application/pdf")
        except Exception as e: st.error(f"Erro: {e}")
