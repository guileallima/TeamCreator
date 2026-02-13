import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Seleção de Elenco PES 2013", layout="wide")

# Função para carregar os dados com os novos nomes de abas
def load_data(file):
    try:
        # Nomes das abas atualizados: GK, DF, MF, FW
        tabs = {'GK': 'Goleiros', 'DF': 'Defensores', 'MF': 'Meio-Campo', 'FW': 'Atacantes'}
        return {key: pd.read_excel(file, sheet_name=key) for key in tabs.keys()}
    except Exception as e:
        st.error(f"Erro ao ler as abas do Excel (GK, DF, MF, FW): {e}")
        return None

def format_func(row):
    if row is None: return "Selecione ou digite o nome..."
    return f"{row['Name']} ({row['reg. pos.']}) - OV: {row['overall']} - €{row['Market Value (M€)']}M"

st.title("⚽ Seleção de Elenco - PES 2013")

# Tenta carregar o arquivo padrão 'jogadores.xlsx'
arquivo_alvo = "jogadores.xlsx"
uploaded_file = st.sidebar.file_uploader("Ou suba uma versão diferente da planilha", type=["xlsx"])

if uploaded_file is not None:
    data = load_data(uploaded_file)
else:
    try:
        data = load_data(arquivo_alvo)
    except:
        st.info(f"Aguardando arquivo '{arquivo_alvo}' no GitHub ou via upload lateral.")
        st.stop()

if data:
    nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
    esquema = st.sidebar.selectbox("Esquema Tático (Laterais/Zagueiros | Meios | Ataque)", ["442", "352", "451", "433", "343"])
    
    taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
    n_def, n_mei, n_ata = taticas[esquema]

    elenco = []
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        # Goleiro Titular (Aba GK)
        g_list = [None] + data['GK'].sort_values('overall', ascending=False).to_dict('records')
        g = st.selectbox("🧤 Goleiro Titular", g_list, format_func=format_func, key="gk_t")
        if g: elenco.append({**g, "Posição_Escalada": "Goleiro", "Status": "Titular"})
        
        # Defensores (Aba DF)
        st.write("🛡️ **Defesa**")
        c_df = st.columns(2)
        for i in range(n_def):
            with c_df[i%2]:
                df_list = [None] + data['DF'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Defensor {i+1}", df_list, format_func=format_func, key=f"df{i}")
                if sel: elenco.append({**sel, "Posição_Escalada": "Defesa", "Status": "Titular"})

        # Meio Campo (Aba MF)
        st.write("🎯 **Meio-Campo**")
        c_mf = st.columns(2)
        for i in range(n_mei):
            with c_mf[i%2]:
                mf_list = [None] + data['MF'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Meio-Campista {i+1}", mf_list, format_func=format_func, key=f"mf{i}")
                if sel: elenco.append({**sel, "Posição_Escalada": "Meio", "Status": "Titular"})

        # Atacantes (Aba FW)
        st.write("🚀 **Ataque**")
        c_fw = st.columns(2)
        for i in range(n_ata):
            with c_fw[i%2]:
                fw_list = [None] + data['FW'].sort_values('overall', ascending=False).to_dict('records')
                sel = st.selectbox(f"Atacante {i+1}", fw_list, format_func=format_func, key=f"fw{i}")
                if sel: elenco.append({**sel, "Posição_Escalada": "Ataque", "Status": "Titular"})

    with col2:
        st.subheader("📋 Reservas (8)")
        # Goleiro Reserva Obrigatório (GK)
        gr = st.selectbox("Goleiro Reserva (Obrigatório)", g_list, format_func=format_func, key="gk_r")
        if gr: elenco.append({**gr, "Posição_Escalada": "Goleiro", "Status": "Reserva"})
        
        # Outros 7 Reservas (Qualquer posição das abas DF, MF, FW)
        todos_res = pd.concat([data['DF'], data['MF'], data['FW']]).sort_values('overall', ascending=False)
        res_list = [None] + todos_res.to_dict('records')
        
        for i in range(7):
            r = st.selectbox(f"Reserva {i+2}", res_list, format_func=format_func, key=f"res{i}")
            if r: elenco.append({**r, "Posição_Escalada": "Mix", "Status": "Reserva"})

    # Cálculos Finais
    if elenco:
        df_final = pd.DataFrame(elenco)
        total_valor = df_final["Market Value (M€)"].sum()
        med_ov = df_final["overall"].mean()

        st.sidebar.markdown("---")
        st.sidebar.subheader("📊 Resumo do Time")
        st.sidebar.metric("Custo Total", f"€{total_valor:.1f}M")
        st.sidebar.metric("Média de Overall", f"{med_ov:.1f}")
        
        # Exportação para Excel
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Escalação')
        
        st.sidebar.download_button(
            label="💾 Baixar Time em Excel",
            data=output.getvalue(),
            file_name=f"{nome_time.replace(' ', '_')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
