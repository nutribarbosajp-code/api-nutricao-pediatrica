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
        "Perfil & Busca de Pacientes",
        "Cadastrar Paciente", 
        "Ficha de Anamnese", 
        "Recordatório 24h", 
        "Repertório & Sugestões IA 🤖", 
        "Insumos da Sessão 🧺",
        "Diário Sensorial & Fotos", 
        "Emitir Laudo PDF"
    ]
)

# --- ABA 0: PERFIL & BUSCA DE PACIENTES ---
if menu == "Perfil & Busca de Pacientes":
    st.header("📁 Perfil Clínico & Pesquisa de Pacientes")
    st.markdown("Consulte rapidamente os pacientes registados, acompanhe o perfil e aceda aos relatórios.")

    try:
        resposta = requests.get(f"{API_URL}/pacientes/")
        if resposta.status_code == 200:
            pacientes = resposta.json()
        else:
            pacientes = []
    except:
        pacientes = []

    if not pacientes:
        st.info("Ainda não existem pacientes registados no sistema. Vá a 'Cadastrar Paciente' para começar.")
    else:
        opcoes_pacientes = {f"{p['nome']} (ID: {p['id']})": p['id'] for p in pacientes}
        
        paciente_selecionado_str = st.selectbox("Selecione o Paciente:", list(opcoes_pacientes.keys()))
        paciente_id = opcoes_pacientes[paciente_selecionado_str]
        
        dados_paciente = next((p for p in pacientes if p['id'] == paciente_id), None)
        
        if dados_paciente:
            st.markdown("---")
            st.subheader(f"👤 Paciente: {dados_paciente['nome']}")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Idade", f"{dados_paciente['idade_anos']} anos")
            with col2:
                st.metric("Peso", f"{dados_paciente['peso_kg']} kg")
            with col3:
                st.metric("Altura", f"{dados_paciente['altura_cm']} cm")
                
            st.markdown("### 📊 Ações e Relatórios")
            
            if st.button("📥 Descarregar Relatório Clínico em PDF (OMS & Macros)"):
                pdf_resposta = requests.get(f"{API_URL}/pacientes/{paciente_id}/relatorio-pdf")
                if pdf_resposta.status_code == 200:
                    st.download_button(
                        label="Clique aqui para guardar o PDF",
                        data=pdf_resposta.content,
                        file_name=f"Relatorio_{dados_paciente['nome']}.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.error("Erro ao gerar o relatório em PDF.")
                    
            st.markdown("### 🥗 Repertório Alimentar Registado")
            rep_resposta = requests.get(f"{API_URL}/repertorio/{paciente_id}")
            if rep_resposta.status_code == 200:
                repertorio = rep_resposta.json()
                if repertorio:
                    for item in repertorio:
                        cor_status = "🟢" if item['status'] == 'seguro' else "🟡"
                        st.write(f"{cor_status} **{item['alimento']}** — Textura: {item['textura']} | Sabor: {item['sabor']} | Cor: {item['cor']}")
                else:
                    st.info("Nenhum alimento registado no repertório deste paciente.")

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
    st.header("📝 Ficha de Anamnese Alimentar Infantil (Completa)")
    
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="ana_id")
    
    if st.button("Carregar Anamnese do Paciente"):
        try:
            res_get = requests.get(f"{API_URL}/anamnese/{paciente_id}")
            if res_get.status_code == 200:
                dados = res_get.json().get("anamnese")
                if dados:
                    st.success("Ficha de Anamnese encontrada!")
                    st.json(dados)
                else:
                    st.warning("Ainda não existe ficha registada para este paciente.")
        except Exception as e:
            st.error(f"Erro ao buscar anamnese: {e}")
            
    st.markdown("---")
    
    with st.form("form_anamnese_completa"):
        st.subheader("1. Identificação e Dados Gerais")
        c1, c2, c3 = st.columns(3)
        with c1: nome_resp = st.text_input("Nome da Mãe / Responsável")
        with c2: tel_resp = st.text_input("Telefone do Responsável")
        with c3: sexo_crianca = st.selectbox("Sexo", ["Feminino", "Masculino"])
        
        c4, c5 = st.columns(2)
        with c4: dt_nasc = st.text_input("Data de Nascimento", placeholder="DD/MM/AAAA")
        with c5: pediatra = st.text_input("Nome do Pediatra / Acompanhamento")

        st.subheader("2. Antecedentes Gestacionais e Parto")
        gestacao_planejada = st.selectbox("A gestação foi planejada?", ["Sim", "Não"])
        intercorrencias_gestacao = st.text_input("Intercorrências na gestação / Medicação / Suplementos / HASG / Diabetes Gestacional")
        c6, c7 = st.columns(2)
        with c6: idade_gest = st.text_input("Idade Gestacional (semanas/dias)")
        with c7: tipo_parto = st.selectbox("Tipo de Parto", ["Cesária", "Natural/Normal"])

        st.subheader("3. Introdução Alimentar e Histórico Pretérito")
        c8, c9, c10 = st.columns(3)
        with c8: amamentado = st.selectbox("Foi amamentado?", ["Sim", "Não"])
        with c9: tempo_amam = st.text_input("Quanto tempo de amamentação?")
        with c10: inicio_ia = st.text_input("Início da Introdução Alimentar (meses)")
        
        c11, c12 = st.columns(2)
        with c11: metodo_ia = st.selectbox("Método de Introdução Alimentar", ["Tradicional", "Misto", "BLW"])
        with c12: uso_mamadeira = st.text_input("Fez uso de mamadeira? Por quanto tempo?")
        
        intercorr_ia = st.text_area("Houve intercorrências na introdução alimentar?")

        st.subheader("4. Hábitos de Vida e Dinâmica Alimentar Diária")
        c_mov, c_conc = st.columns(2)
        with c_mov: habito_mov = st.selectbox("Gosta de se movimentar, brincar?", ["Muito", "Médio", "Pouco"])
        with c_conc: habito_conc = st.selectbox("Demonstra concentrar-se em suas atividades?", ["Muito", "Médio", "Pouco"])
        
        comportamento_diario = st.selectbox(
            "Normalmente, durante o dia, a criança:",
            [
                "Sente fome e pede para comer",
                "Só come distraído",
                "Come sempre nos mesmos horários",
                "Um adulto tem que incentivá-lo",
                "Não segue horários fixos"
            ]
        )
        
        mastigacao = st.selectbox(
            "A criança normalmente mastiga os alimentos?",
            [
                "Sim",
                "Mastiga tudo menos as proteínas que são um pouco mais duras",
                "Só aceita comer os alimentos amassados",
                "Amassados e com bastante caldo"
            ]
        )
        
        utensilios = st.multiselect(
            "A criança faz uso de:",
            ["Copo com bico", "Copo sem bico", "Colher pequena", "Garfo pequeno", "Faca pequena", "Mamadeira"]
        )
        
        cafe_manha = st.selectbox(
            "A criança toma café da manhã?",
            ["Todos os dias", "Quase sempre", "Quase nunca", "Nunca"]
        )

        st.subheader("5. Questionário de Frequência Alimentar (QFA)")
        opcoes_freq = ["Todos os dias", "3x por semana", "2x por semana", "Nunca"]
        
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            f_frutas = st.selectbox("Consumo de Frutas", opcoes_freq)
            f_verduras = st.selectbox("Consumo de Verduras", opcoes_freq)
            f_legumes = st.selectbox("Consumo de Legumes", opcoes_freq)
            f_ind = st.selectbox("Biscoitos Industrializados", opcoes_freq)
            f_ref = st.selectbox("Refrigerante", opcoes_freq)
        with c_f2:
            f_frit = st.selectbox("Frituras", opcoes_freq)
            f_carnes = st.selectbox("Carnes", opcoes_freq)
            f_leite = st.selectbox("Leite e Derivados", opcoes_freq)
            
        ref_dia = st.text_input("Quando em casa, quantas refeições fazem por dia?")
        agua_vol = st.text_input("Consumo de água (frequência e volume aproximado)")

        st.subheader("6. Aspectos Clínicos, Funcionais e Histórico Familiar")
        doencas = st.text_input("Doenças existentes / Condições clínicas")
        medicacoes = st.text_input("Em uso de medicação ou suplementação?")
        alergias = st.text_input("Alergias conhecidas ou alimentares (tipo de expressão alérgica)")
        hist_familiar = st.text_input("Histórico Familiar (Diabetes, Obesidade, Hipertensão, Cardiopatia, etc.)")
        
        st.subheader("7. Comportamentos e Ambiente Alimentar")
        comportamentos_alim = st.multiselect(
            "Comportamentos Alimentares Presentes:",
            ["Seletividade alimentar", "Compulsão alimentar", "PICA", "Comportamento ritualístico", "Comportamento alimentar rígido", "Só come distraído/com telas", "Exige incentivo de adulto"]
        )
        produtos_ind = st.text_input("Consumo de industrializados / corantes (frequência e quais)")
        preferencias = st.text_area("Preferências e Aversões Alimentares (Texturas, cores, marcas específicas)")
        ambiente = st.text_input("Ambiente das refeições (ex: Come à mesa com a família, assistindo à TV)")

        st.subheader("8. Avaliação Gastrointestinal e Clínico-Geral")
        c13, c14 = st.columns(2)
        with c13: intestino = st.selectbox("Funcionamento Intestinal", ["Diário", "2 a 3 vezes por semana", "1 vez por semana", "Constipado", "Diarreia frequente"])
        with c14: bristol = st.selectbox("Escala de Bristol / Aspeto das Fezes", ["Tipo 1-2 (Constipação)", "Tipo 3-4 (Normal/Ideal)", "Tipo 5-7 (Diarreia/Amolescida)", "Presença de muco ou sangue"])
        
        sintomas_gastro = st.text_input("Sintomas (Distensão abdominal, refluxo, muitos gases forte, prurido)")
        sono_habitos = st.text_input("Qualidade do Sono")

        st.subheader("9. Expectativa e Opinião dos Pais")
        opiniao = st.text_area("No que a Terapia Nutricional pode ajudar? Qual a expectativa e quais alimentos gostaria de introduzir?")
        obs_geral = st.text_area("Observações importantes do Terapeuta")

        if st.form_submit_button("Guardar Ficha de Anamnese Completa"):
            payload = {
                "paciente_id": paciente_id,
                "nome_responsavel": nome_resp,
                "telefone_responsavel": tel_resp,
                "sexo": sexo_crianca,
                "data_nascimento": dt_nasc,
                "acompanhamento_pediatra": pediatra,
                "gestacao_planejada": gestacao_planejada,
                "intercorrencias_gestacao": intercorrencias_gestacao,
                "idade_gestacional": idade_gest,
                "tipo_parto": tipo_parto,
                "amamentacao": amamentado,
                "tempo_amamentacao": tempo_amam,
                "inicio_ia": inicio_ia,
                "metodo_ia": metodo_ia,
                "uso_mamadeira": uso_mamadeira,
                "intercorrencias_ia": intercorr_ia,
                "doencas_existentes": doencas,
                "medicacoes": medicacoes,
                "alergias": alergias,
                "historico_familiar": hist_familiar,
                "comportamentos_alimentares": ", ".join(comportamentos_alim),
                "produtos_industrializados": produtos_ind,
                "preferencias_aversoes": preferencias,
                "ambiente_refeicao": ambiente,
                "funcionamento_intestinal": intestino,
                "escala_bristol": bristol,
                "sintomas_gastrointestinais": sintomas_gastro,
                "sono_medicacoes": sono_habitos,
                "opiniao_pais": opiniao,
                "observacoes": obs_geral,
                "habito_movimentar": habito_mov,
                "habito_concentracao": habito_conc,
                "comportamento_diario_comer": comportamento_diario,
                "padrao_mastigacao": mastigacao,
                "utensilios_usados": ", ".join(utensilios),
                "frequencia_cafe_manha": cafe_manha,
                "freq_frutas": f_frutas,
                "freq_verduras": f_verduras,
                "freq_legumes": f_legumes,
                "freq_industrializados": f_ind,
                "freq_refrigerante": f_ref,
                "freq_frituras": f_frit,
                "freq_carnes": f_carnes,
                "freq_leite_derivados": f_leite,
                "refeicoes_por_dia": ref_dia,
                "consumo_agua": agua_vol
            }
            try:
                res = requests.post(f"{API_URL}/anamnese/", json=payload)
                if res.status_code == 200:
                    st.success("Ficha de Anamnese completa guardada com sucesso!")
            except Exception as e:
                st.error(f"Erro ao guardar: {e}")

# --- ABA 3: RECORDATÓRIO 24H ---
elif menu == "Recordatório 24h":
    st.header("🥗 Recordatório Alimentar & Comportamental de 24 Horas")
    st.markdown("Registe o diário alimentar detalhado para mapear padrões de fome, saciedade e comportamento durante as refeições.")
    
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rec_id")
    
    tab_reg_rec, tab_ver_rec = st.tabs(["📝 Registar Consumo", "📊 Consultar Diário"])
    
    with tab_reg_rec:
        st.subheader("Adicionar Refeição ao Diário")
        with st.form("form_recordatorio"):
            c1, c2 = st.columns(2)
            with c1:
                refeicao = st.selectbox("Qual a refeição?", ["Café da manhã", "Lanche da Manhã", "Almoço", "Lanche da Tarde", "Jantar", "Ceia", "Beliscar / Fora de hora"])
                horario = st.time_input("Horário da Refeição")
            with c2:
                aceitacao = st.selectbox("Nível de Aceitação", ["Comeu tudo", "Comeu mais de metade", "Comeu menos de metade", "Apenas provou", "Recusou totalmente", "Cuspiu/Vomitou"])
                contexto = st.selectbox("Contexto / Ambiente", ["À mesa com a família", "À mesa sozinho", "Assistindo TV / Telas", "Brincando / Em movimento", "Na escola / Creche"])
                
            alimento = st.text_area("Alimentos Consumidos e Preparação", placeholder="Ex: Arroz branco, feijão com caldo, nuggets de frango (marca X)")
            quantidade = st.text_input("Quantidade Estimada", placeholder="Ex: 3 colheres de sopa de arroz, 2 nuggets")
            
            if st.form_submit_button("Guardar no Recordatório"):
                payload = {
                    "paciente_id": paciente_id,
                    "refeicao": refeicao, 
                    "alimento": alimento, 
                    "quantidade": quantidade,
                    "horario": horario.strftime("%H:%M"),
                    "aceitacao": aceitacao,
                    "contexto": contexto
                }
                try:
                    res = requests.post(f"{API_URL}/recordatorio/", json=payload)
                    if res.status_code == 200:
                        st.success("Refeição registada com sucesso no diário do paciente!")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
                    
    with tab_ver_rec:
        st.subheader("Histórico do Diário Alimentar")
        if st.button("Atualizar Visualização do Diário"):
            try:
                res = requests.get(f"{API_URL}/recordatorio/{paciente_id}")
                if res.status_code == 200:
                    registros = res.json()
                    if registros:
                        # Exibição visual em blocos tipo "Feed" em vez de tabela crua
                        for reg in registros:
                            with st.container():
                                st.markdown(f"### 📅 {reg['data']} às ⏰ {reg['horario']} — **{reg['refeicao']}**")
                                colA, colB = st.columns(2)
                                with colA:
                                    st.write(f"🍽️ **Alimento / Preparação:** {reg['alimento']}")
                                    st.write(f"⚖️ **Quantidade:** {reg['quantidade']}")
                                with colB:
                                    # Formatação de cor para a aceitação
                                    cor_aceitacao = "🔴" if "Recusou" in reg['aceitacao'] or "Cuspiu" in reg['aceitacao'] else "🟢"
                                    st.write(f"{cor_aceitacao} **Aceitação:** {reg['aceitacao']}")
                                    st.write(f"🏠 **Contexto:** {reg['contexto']}")
                                st.divider()
                    else:
                        st.info("Nenhum registo de recordatório encontrado para este paciente.")
            except Exception as e:
                st.error(f"Erro de conexão: {e}")

# --- ABA 4: REPERTÓRIO ALIMENTAR & SUGESTÕES IA 🤖 ---
elif menu == "Repertório & Sugestões IA 🤖":
    st.header("🧠 Mapeamento Sensorial e Sugestões de Pontes por IA")
    paciente_id = st.number_input("ID do Paciente", min_value=1, step=1, value=1, key="rep_id")
    tab_cad, tab_ia = st.tabs(["📌 Registar Alimentos no Repertório", "🤖 Motor de IA (Pontes Alimentares)"])
    
    with tab_cad:
        st.subheader("Mapear Propriedades Sensoriais dos Alimentos")
        alim_nome = st.text_input("Nome do Alimento", placeholder="Ex: Batata Frita")
        
        status_alim = st.selectbox("Status no Tratamento", ["seguro", "em_trabalho", "recusado"])
        passo_escada = None
        if status_alim == "em_trabalho":
            passo_escada = st.selectbox("Etapa na Escada do Comer", 
                ["1. Tolerar", "2. Interagir", "3. Cheirar", "4. Tocar", "5. Provar", "6. Comer"]
            )
            
        c1, c2, c3, c4 = st.columns(4)
        with c1: text_opt = st.selectbox("Textura", ["Crocante", "Macio", "Pastoso", "Liquido", "Seco"])
        with c2: sab_opt = st.selectbox("Sabor", ["Salgado", "Doce", "Azedo", "Neutro"])
        with c3: cor_opt = st.text_input("Cor Dominante", placeholder="Ex: Vermelho vibrante")
        with c4: temp_opt = st.selectbox("Temperatura", ["Quente", "Morno", "Frio", "Gelado"])
        
        if st.button("Adicionar ao Repertório"):
            status_final = f"em_trabalho ({passo_escada})" if status_alim == "em_trabalho" else status_alim
            payload = {
                "paciente_id": paciente_id,
                "alimento": alim_nome,
                "status": status_final,
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
        
        col_lembrete, col_hora = st.columns(2)
        with col_lembrete:
            lembrete = st.selectbox("Frequência do Lembrete", ["24h antes da sessão", "48h antes da sessão", "Na manhã da sessão"])
        with col_hora:
            hora_lembrete = st.time_input("Horário exato da notificação")
            
        if st.button("Enviar Solicitação com Lembretes"):
            lembrete_final = f"{lembrete} às {hora_lembrete.strftime('%H:%M')}"
            payload = {
                "paciente_id": paciente_id,
                "data_consulta": str(data_sessao),
                "alimentos_solicitados": alimentos_req,
                "orientacoes_preparo": instrucoes,
                "lembrete_config": lembrete_final
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
                            if st.button(f"Marcar como Separado / Comprado (Item #{item['id']})", key=f"btn_sup_{item['id']}"):
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
    st.header("📄 Emitir Laudo Clínico em PDF")
    paciente_id_pdf = st.number_input("ID do Paciente para Laudo", min_value=1, step=1, value=1, key="pdf_id")
    
    st.markdown("Aceda e descarregue o relatório clínico completo contendo a antropometria OMS, distribuição de macronutrientes, TMB/GET, resumo da anamnese e repertório alimentar.")
    
    if st.button("Gerar e Descarregar Laudo PDF"):
        try:
            pdf_res = requests.get(f"{API_URL}/pacientes/{paciente_id_pdf}/relatorio-pdf")
            if pdf_res.status_code == 200:
                st.success("Relatório gerado com sucesso!")
                st.download_button(
                    label="📥 Clique aqui para guardar o Laudo em PDF", 
                    data=pdf_res.content, 
                    file_name=f"Relatorio_Clinico_Paciente_{paciente_id_pdf}.pdf", 
                    mime="application/pdf"
                )
            else:
                st.error("Erro ao gerar o relatório. Verifique se o ID do paciente existe.")
        except Exception as e: 
            st.error(f"Erro de conexão: {e}")
