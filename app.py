import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="PES 2013 Squad Selector", layout="wide")

# 1. Carregamento fixo e otimizado
@st.cache_data
def load_data():
    file = "jogadores.xlsx"
    try:
        tabs = ['GK', 'DF', 'MF', 'FW']
        data = {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
        for tab in data:
            data[tab].columns = data[tab].columns.str.strip()
        return data
    except Exception as e:
        st.error(f"Erro: Certifique-se de que o arquivo '{file}' está no GitHub com as abas GK, DF, MF e FW.")
        st.stop()

def format_func(row):
    if row is None: return "Selecione..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}"

# --- Inicialização ---
data = load_data()
ORCAMENTO_MAX = 3000.0

if 'escolhas' not in st.session_state:
    st.session_state.escolhas = {}

# Cálculo imediato de saldo
custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_atual

# --- Interface ---
st.title("⚽ Seleção de Elenco - PES 2013")

nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
esquema = st.sidebar.selectbox("Esquema Tático", ["442", "352", "451", "433", "343"])

taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
n_def, n_mei, n_ata = taticas[esquema]

def seletor_veloz(label, df, key_id):
    # Pega o nome de todos os outros jogadores já escolhidos para retirar da lista
    outros_nomes = [v['Name'] for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    # Valor do jogador que já está neste slot (caso queira trocar, esse valor volta para o saldo)
    valor_atual = st.session_state.escolhas.get(key_id, {}).get('Market Value (M€)', 0) if st.session_state.escolhas.get(key_id) else 0
    
    # Filtra: cabe no saldo + não foi escolhido em outro lugar
    df_f = df[(df['Market Value (M€)'] <= (saldo + valor_atual)) & (~df['Name'].isin(outros_nomes))]
    
    opcoes = [None] + df_f.sort_values('Overall', ascending=False).to_dict('records')
    
    # Index para manter a seleção ao recarregar
    index_atual = 0
    if st.session_state.escolhas.get(key_id):
        # Encontra a posição do jogador atual na nova lista filtrada
        for i, opt in enumerate(opcoes):
            if opt and opt['Name'] == st.session_state.escolhas[key_id]['Name']:
                index_atual = i
                break

    escolha = st.selectbox(label, opcoes, index=index_atual, format_func=format_func, key=key_id)
    
    # Se mudar a escolha, atualiza o estado e força o recarregamento para atualizar o saldo na hora
    if st.session_state.escolhas.get(key_id) != escolha:
        st.session_state.escolhas[key_id] = escolha
        st.rerun()
    
    return escolha

col1, col2 = st.columns([2, 1])
elenco_final = []

with col1:
    st.subheader(f"Titulares - {esquema}")
    g = seletor_veloz("🧤 Goleiro Titular", data['GK'], "gk_t")
    if g: elenco_final.append({**g, "Pos": "Titular"})
    
    for pos, n, aba in [("Defensor", n_def, 'DF'), ("Meio", n_mei, 'MF'), ("Atacante", n_ata, 'FW')]:
        st.write(f"**{pos}**")
        c = st.columns(2)
        for i in range(n):
            with c[i%2]:
                sel = seletor_veloz(f"{pos} {i+1}", data[aba], f"{aba}_{i}")
                if sel: elenco_final.append({**sel, "Pos": "Titular"})

with col2:
    st.subheader("📋 Reservas")
    gr = seletor_veloz("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_final.append({**gr, "Pos": "Reserva"})
    
    todos = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(7):
        r = seletor_veloz(f"Reserva {i+2}", todos, f"res_{i}")
        if r: elenco_final.append({**r, "Pos": "Reserva"})

# --- Sidebar Financeira ---
st.sidebar.markdown("---")
st.sidebar.metric("Custo Total", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")

if elenco_final:
    df_f = pd.DataFrame(elenco_final)
    media = df_f['Overall'].mean()
    st.sidebar.metric("Média Overall", f"{media:.1f}")

    if st.sidebar.button("💾 Exportar para Excel"):
        out = BytesIO()
        with pd.ExcelWriter(out, engine='openpyxl') as wr:
            resumo = [["TIME:", nome_time], ["CUSTO:", custo_atual], ["MÉDIA:", f"{media:.1f}"], ["", ""]]
            pd.DataFrame(resumo).to_excel(wr, index=False, header=False, sheet_name='Escalacao')
            df_f.to_excel(wr, index=False, startrow=5, sheet_name='Escalacao')
        st.sidebar.download_button("Baixar Arquivo", out.getvalue(), f"{nome_time}.xlsx")

