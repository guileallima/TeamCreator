import streamlit as st
import pandas as pd
from io import BytesIO
import re

st.set_page_config(page_title="Seleção de Elenco PES 2013", layout="wide")

def clean_column_name(col):
    return re.sub(r'[^a-zA-Z0-9]', '', str(col)).lower()

def load_data(file):
    try:
        tabs_map = ['GK', 'DF', 'MF', 'FW']
        data_dict = {}
        for key in tabs_map:
            df = pd.read_excel(file, sheet_name=key)
            df.columns = [clean_column_name(c) for c in df.columns]
            data_dict[key] = df
        return data_dict
    except Exception as e:
        st.error(f"Erro: Verifique as abas GK, DF, MF e FW. Detalhes: {e}")
        return None

def format_func(row):
    if row is None: return "Selecione..."
    return f"{row['name']} ({row['regpos']}) - OV: {row['overall']} - €{row['marketvaluem']}M"

st.title("⚽ Seleção de Elenco - PES 2013")

# Configurações de Orçamento
ORCAMENTO_MAX = 4.0
arquivo_alvo = "jogadores.xlsx"
uploaded_file = st.sidebar.file_uploader("Upload da Planilha", type=["xlsx"])

if uploaded_file is not None:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data(arquivo_alvo)
    except:
        st.info(f"Coloque o arquivo '{arquivo_alvo}' no GitHub.")
        st.stop()

if data:
    nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
    esquema = st.sidebar.selectbox("Esquema Tático", ["442", "352", "451", "433", "343"])
    
    taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
    n_def, n_mei, n_ata = taticas[esquema]
    
    # Inicialização do estado para controle de orçamento
    if 'escolhas' not in st.session_state:
        st.session_state.escolhas = {}

    # Cálculo do custo atual para filtragem dinâmica
    custo_atual = sum([v['marketvaluem'] for k, v in st.session_state.escolhas.items() if v is not None])
    saldo_disponivel = ORCAMENTO_MAX - custo_atual

    def criar_seletor_inteligente(label, df, key_id):
        # Filtra apenas jogadores que cabem no saldo restante
        # Mas permite que o jogador já selecionado continue na lista para não bugar o seletor
        jogadores_viaveis = df[df['marketvaluem'] <= saldo_disponivel]
        
        # Se já houver uma escolha para este botão, garante que ela apareça na lista mesmo se o saldo zerar
        escolha_atual = st.session_state.escolhas.get(key_id)
        if escolha_atual is not None:
            jogadores_viaveis = pd.concat([jogadores_viaveis, pd.DataFrame([escolha_atual])]).drop_duplicates()

        lista = [None] + jogadores_viaveis.sort_values('overall', ascending=False).to_dict('records')
        
        selecionado = st.selectbox(label, lista, format_func=format_func, key=key_id)
        st.session_state.escolhas[key_id] = selecionado
        return selecionado

    elenco_final = []
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        g = criar_seletor_inteligente("🧤 Goleiro Titular", data['GK'], "gk_t")
        if g: elenco_final.append({**g, "status": "Titular"})
        
        for pos, n, aba in [("Defesa", n_def, 'DF'), ("Meio", n_mei, 'MF'), ("Ataque", n_ata, 'FW')]:
            st.write(f"**{pos}**")
            cols = st.columns(2)
            for i in range(n):
                with cols[i%2]:
                    sel = criar_seletor_inteligente(f"{pos} {i+1}", data[aba], f"{aba}_{i}")
                    if sel: elenco_final.append({**sel, "status": "Titular"})

    with col2:
        st.subheader("📋 Reservas")
        gr = criar_seletor_inteligente("Goleiro Reserva", data['GK'], "gk_r")
        if gr: elenco_final.append({**gr, "status": "Reserva"})
        
        todos_outros = pd.concat([data['DF'], data['MF'], data['FW']])
        for i in range(7):
            r = criar_seletor_inteligente(f"Reserva {i+2}", todos_outros, f"res_{i}")
            if r: elenco_final.append({**r, "status": "Reserva"})

    # Barra Lateral com Indicadores
    st.sidebar.markdown("---")
    cor_orcamento = "normal" if custo_atual <= ORCAMENTO_MAX else "inverse"
    st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.2f}M", f"Saldo: €{saldo_disponivel:.2f}M", delta_color=cor_orcamento)
    
    if elenco_final:
        df_f = pd.DataFrame(elenco_final)
        media_ov = df_f['overall'].mean()
        st.sidebar.metric("Média Overall", f"{media_ov:.1f}")

        # Lógica de Exportação Personalizada
        if st.sidebar.button("Gerar Arquivo de Exportação"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Criar DataFrame de cabeçalho
                header_data = [
                    ["NOME DO TIME:", nome_time],
                    ["CUSTO TOTAL:", f"€{custo_atual:.2f}M"],
                    ["OVERALL MÉDIO:", f"{media_ov:.1f}"],
                    ["", ""], # Linha vazia
                    ["ELENCO DETALHADO:", ""]
                ]
                pd.DataFrame(header_data).to_excel(writer, index=False, header=False, sheet_name='Escalação')
                # Adicionar os jogadores abaixo do cabeçalho (linha 6 em diante)
                df_f.to_excel(writer, index=False, startrow=6, sheet_name='Escalação')
            
            st.sidebar.download_button(
                "⬇️ Baixar Excel", 
                output.getvalue(), 
                f"{nome_time}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
