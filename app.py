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
        st.error(f"Erro ao carregar abas. Verifique os nomes GK, DF, MF e FW. Erro: {e}")
        return None

def format_func(row):
    if row is None: return "Selecione ou digite o nome..."
    # Formatação para exibir bilhões de forma legível
    valor = row['Market Value (M€)']
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{valor:,.0f}"

st.title("⚽ Seleção de Elenco - PES 2013")

# Ajuste do limite para 4 bilhões
ORCAMENTO_MAX = 4000000000.0 
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

    # Cálculo do custo e saldo
    custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
    saldo = ORCAMENTO_MAX - custo_atual

    def seletor_inteligente(label, df, key_id):
        # Regra 3: Filtrar para aparecer só os que cabem no orçamento restante
        # Mantemos o já selecionado na lista para evitar que o campo fique em branco ao atingir o limite
        escolha_atual_val = st.session_state.escolhas.get(key_id, {}).get('Market Value (M€)', 0) if st.session_state.escolhas.get(key_id) else 0
        
        disponiveis = df[df['Market Value (M€)'] <= (saldo + escolha_atual_val)]
        
        opcoes = [None] + disponiveis.sort_values('Overall', ascending=False).to_dict('records')
        escolha = st.selectbox(label, opcoes, format_func=format_func, key=key_id)
        st.session_state.escolhas[key_id] = escolha
        return escolha

    elenco_final = []
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        g = seletor_inteligente("🧤 Goleiro Titular", data['GK'], "gk_t")
        if g: elenco_final.append({**g, "Tipo": "Titular"})
        
        for pos, n, aba in [("Defesa", n_def, 'DF'), ("Meio", n_mei, 'MF'), ("Ataque", n_ata, 'FW')]:
            st.write(f"**{pos}**")
            cols = st.columns(2)
            for i in range(n):
                with cols[i%2]:
                    sel = seletor_inteligente(f"{pos} {i+1}", data[aba], f"{aba}_{i}")
                    if sel: elenco_final.append({**sel, "Tipo": "Titular"})

    with col2:
        st.subheader("📋 Reservas")
        gr = seletor_inteligente("Goleiro Reserva", data['GK'], "gk_r")
        if gr: elenco_final.append({**gr, "Tipo": "Reserva"})
        
        todos = pd.concat([data['DF'], data['MF'], data['FW']])
        for i in range(7):
            r = seletor_inteligente(f"Reserva {i+2}", todos, f"res_{i}")
            if r: elenco_final.append({**r, "Tipo": "Reserva"})

    # Barra Lateral
    st.sidebar.markdown("---")
    st.sidebar.metric("Orçamento Usado", f"€{custo_atual:,.0f}", f"Saldo: €{saldo:,.0f}")
    
    if elenco_final:
        df_f = pd.DataFrame(elenco_final)
        media_ov = df_f['Overall'].mean()
        st.sidebar.metric("Média Overall", f"{media_ov:.1f}")

        if st.sidebar.button("💾 Exportar Time"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Regra 1: Cabeçalho com Nome, Custo e Overall
                info = [
                    ["NOME DO TIME:", nome_time],
                    ["CUSTO TOTAL DO TIME:", f"€ {custo_atual:,.0f}"],
                    ["OVERALL MÉDIO DO TIME:", f"{media_ov:.1f}"],
                    ["----------------------------------", ""]
                ]
                pd.DataFrame(info).to_excel(writer, index=False, header=False, sheet_name='Escalação')
                # Lista de jogadores abaixo
                df_f.to_excel(writer, index=False, startrow=5, sheet_name='Escalação')
            
            st.sidebar.download_button("Clique para baixar", output.getvalue(), f"{nome_time}.xlsx")
