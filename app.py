import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Seleção de Elenco PES 2013", layout="wide")

def load_data(file):
    try:
        tabs = ['GK', 'DF', 'MF', 'FW']
        data = {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
        for tab in data:
            data[tab].columns = data[tab].columns.str.strip()
        return data
    except Exception as e:
        st.error(f"Erro ao carregar abas: {e}")
        return None

def format_func(row):
    if row is None: return "Selecione ou digite o nome..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}"

st.title("⚽ Seleção de Elenco - PES 2013")

# Ajuste do limite para 5.000 conforme solicitado
ORCAMENTO_MAX = 5000.0 
arquivo_alvo = "jogadores.xlsx"

uploaded_file = st.sidebar.file_uploader("Upload da Planilha", type=["xlsx"])
data = load_data(uploaded_file if uploaded_file else arquivo_alvo)

if data:
    nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
    esquema = st.sidebar.selectbox("Esquema Tático", ["442", "352", "451", "433", "343"])
    
    taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
    n_def, n_mei, n_ata = taticas[esquema]

    if 'escolhas' not in st.session_state:
        st.session_state.escolhas = {}

    # Lista de IDs (nomes) já selecionados para exclusão mútua
    selecionados_nomes = [v['Name'] for k, v in st.session_state.escolhas.items() if v is not None]

    # Cálculo do custo e saldo
    custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
    saldo = ORCAMENTO_MAX - custo_atual

    def seletor_inteligente(label, df, key_id):
        escolha_atual = st.session_state.escolhas.get(key_id)
        nome_atual = escolha_atual['Name'] if escolha_atual else None
        
        # 1. Filtra orçamento
        custo_liberado = escolha_atual['Market Value (M€)'] if escolha_atual else 0
        df_filtrado = df[df['Market Value (M€)'] <= (saldo + custo_liberado)]
        
        # 2. Retira jogadores já escolhidos em outros botões (exceto o próprio deste botão)
        outros_selecionados = [n for n in selecionados_nomes if n != nome_atual]
        df_filtrado = df_filtrado[~df_filtrado['Name'].isin(outros_selecionados)]
        
        opcoes = [None] + df_filtrado.sort_values('Overall', ascending=False).to_dict('records')
        escolha = st.selectbox(label, opcoes, format_func=format_func, key=key_id)
        st.session_state.escolhas[key_id] = escolha
        return escolha

    elenco_final = []
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        g = seletor_inteligente("🧤 Goleiro Titular", data['GK'], "gk_t")
        if g: elenco_final.append({**g, "Escalação": "Titular"})
        
        for pos, n, aba in [("Defesa", n_def, 'DF'), ("Meio", n_mei, 'MF'), ("Ataque", n_ata, 'FW')]:
            st.write(f"**{pos}**")
            cols = st.columns(2)
            for i in range(n):
                with cols[i%2]:
                    sel = seletor_inteligente(f"{pos} {i+1}", data[aba], f"{aba}_{i}")
                    if sel: elenco_final.append({**sel, "Escalação": "Titular"})

    with col2:
        st.subheader("📋 Reservas")
        gr = seletor_inteligente("Goleiro Reserva", data['GK'], "gk_r")
        if gr: elenco_final.append({**gr, "Escalação": "Reserva"})
        
        todos_res = pd.concat([data['DF'], data['MF'], data['FW']])
        for i in range(7):
            r = seletor_inteligente(f"Reserva {i+2}", todos_res, f"res_{i}")
            if r: elenco_final.append({**r, "Escalação": "Reserva"})

    # Barra Lateral
    st.sidebar.markdown("---")
    st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")
    
    if elenco_final:
        df_export = pd.DataFrame(elenco_final)
        media_ov = df_export['Overall'].mean()
        st.sidebar.metric("Média Overall", f"{media_ov:.1f}")

        if st.sidebar.button("💾 Exportar Time"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Cabeçalho com informações consolidadas
                header = [
                    ["NOME DO TIME:", nome_time],
                    ["VALOR TOTAL:", f"€{custo_atual:.0f}"],
                    ["MÉDIA OVERALL:", f"{media_ov:.1f}"],
                    ["LIMITE:", f"€{ORCAMENTO_MAX:.0f}"],
                    ["", ""]
                ]
                pd.DataFrame(header).to_excel(writer, index=False, header=False, sheet_name='Time')
                df_export.to_excel(writer, index=False, startrow=5, sheet_name='Time')
            st.sidebar.download_button("Baixar Arquivo", output.getvalue(), f"{nome_time}.xlsx")
