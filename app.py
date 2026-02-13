import streamlit as st
import pandas as pd
from io import BytesIO
import re

st.set_page_config(page_title="Seleção de Elenco PES 2013", layout="wide")

def clean_column_name(col):
    # Remove tudo que não é letra ou número e deixa minúsculo
    return re.sub(r'[^a-zA-Z0-dict]', '', str(col)).lower()

def load_data(file):
    try:
        tabs_map = ['GK', 'DF', 'MF', 'FW']
        data_dict = {}
        for key in tabs_map:
            df = pd.read_excel(file, sheet_name=key)
            # Mapeia os nomes das colunas originais para os nomes limpos
            df.columns = [clean_column_name(c) for c in df.columns]
            data_dict[key] = df
        return data_dict
    except Exception as e:
        st.error(f"Erro: Verifique se as abas GK, DF, MF e FW existem no seu Excel. Detalhes: {e}")
        return None

def format_func(row):
    if row is None: return "Selecione ou digite o nome..."
    # Nomes das colunas agora estão limpos: name, overall, regpos, marketvaluem
    return f"{row['name']} ({row['regpos']}) - OV: {row['overall']} - €{row['marketvaluem']}M"

st.title("⚽ Seleção de Elenco - PES 2013")

arquivo_alvo = "jogadores.xlsx"
uploaded_file = st.sidebar.file_uploader("Upload da Planilha", type=["xlsx"])

if uploaded_file is not None:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data(arquivo_alvo)
    except:
        st.info(f"Aguardando arquivo '{arquivo_alvo}' no GitHub.")
        st.stop()

if data:
    nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
    esquema = st.sidebar.selectbox("Esquema Tático", ["442", "352", "451", "433", "343"])
    
    taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
    n_def, n_mei, n_ata = taticas[esquema]
    elenco = []

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        # Goleiro
        g_list = [None] + data['GK'].sort_values('overall', ascending=False).to_dict('records')
        g = st.selectbox("🧤 Goleiro Titular", g_list, format_func=format_func, key="gk_t")
        if g: elenco.append({**g, "status": "Titular"})
        
        # Defesa (Aba DF)
        st.write("🛡️ **Defesa**")
        c_df = st.columns(2)
        for i in range(n_def):
            with c_df[i%2]:
                df_list = [None] + data['DF'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Defensor {i+1}", df_list, format_func=format_func, key=f"df{i}")
                if sel: elenco.append({**sel, "status": "Titular"})

        # Meio (Aba MF)
        st.write("🎯 **Meio-Campo**")
        c_mf = st.columns(2)
        for i in range(n_mei):
            with c_mf[i%2]:
                mf_list = [None] + data['MF'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Meio {i+1}", mf_list, format_func=format_func, key=f"mf{i}")
                if sel: elenco.append({**sel, "status": "Titular"})

        # Ataque (Aba FW)
        st.write("🚀 **Ataque**")
        c_fw = st.columns(2)
        for i in range(n_ata):
            with c_fw[i%2]:
                fw_list = [None] + data['FW'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Atacante {i+1}", fw_list, format_func=format_func, key=f"fw{i}")
                if sel: elenco.append({**sel, "status": "Titular"})

    with col2:
        st.subheader("📋 Reservas")
        # Goleiro Reserva (Obrigatório)
        gr = st.selectbox("Goleiro Reserva", g_list, format_func=format_func, key="gk_r")
        if gr: elenco.append({**gr, "status": "Reserva"})
        
        # Outros 7 Reservas
        todos_res = pd.concat([data['DF'], data['MF'], data['FW']]).sort_values('overall', ascending=False)
        res_list = [None] + todos_res.to_dict('records')
        for i in range(7):
            r = st.selectbox(f"Reserva {i+2}", res_list, format_func=format_func, key=f"res{i}")
            if r: elenco.append({**r, "status": "Reserva"})

    if elenco:
        df_final = pd.DataFrame(elenco)
        # O nome da coluna de valor agora é 'marketvaluem' devido à limpeza
        st.sidebar.metric("Custo Total", f"€{df_final['marketvaluem'].sum():.1f}M")
        st.sidebar.metric("Média Overall", f"{df_final['overall'].mean():.1f}")
        
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False)
        st.sidebar.download_button("💾 Baixar Escalação", output.getvalue(), f"{nome_time}.xlsx")
