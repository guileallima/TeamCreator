import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Seleção de Elenco PES 2013", layout="wide")

# Função de carga simplificada para evitar erros de mapeamento
def load_data(file):
    try:
        # Lendo exatamente as abas que você informou
        tabs = ['GK', 'DF', 'MF', 'FW']
        return {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
    except Exception as e:
        st.error(f"Erro ao carregar abas. Verifique se os nomes GK, DF, MF e FW estão corretos. Erro: {e}")
        return None

# Formatação usando os nomes exatos das colunas que você passou
def format_func(row):
    if row is None: return "Selecione ou digite o nome..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}M"

st.title("⚽ Seleção de Elenco - PES 2013")

# Limite de orçamento: 4.0 (Ajuste para 4000000 se sua planilha usar números inteiros)
ORCAMENTO_MAX = 4.0 
arquivo_alvo = "jogadores.xlsx"

uploaded_file = st.sidebar.file_uploader("Upload da Planilha", type=["xlsx"])
data = load_data(uploaded_file if uploaded_file else arquivo_alvo)

if data:
    nome_time = st.sidebar.text_input("Nome do Time", "Meu Time PES")
    esquema = st.sidebar.selectbox("Esquema Tático", ["442", "352", "451", "433", "343"])
    
    # Mapeamento do esquema
    taticas = {"442":(4,4,2), "352":(3,5,2), "451":(4,5,1), "433":(4,3,3), "343":(3,4,3)}
    n_def, n_mei, n_ata = taticas[esquema]

    if 'escolhas' not in st.session_state:
        st.session_state.escolhas = {}

    # Cálculo do custo (usando o nome exato da coluna)
    custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
    saldo = ORCAMENTO_MAX - custo_atual

    def seletor_jogador(label, df, key_id):
        # Filtro: mostra quem cabe no orçamento OU quem já estava selecionado
        # Adicionei uma margem de segurança para evitar que a lista suma
        disponiveis = df[df['Market Value (M€)'] <= (saldo + (st.session_state.escolhas.get(key_id, {}).get('Market Value (M€)', 0) if st.session_state.escolhas.get(key_id) else 0))]
        
        opcoes = [None] + disponiveis.sort_values('Overall', ascending=False).to_dict('records')
        escolha = st.selectbox(label, opcoes, format_func=format_func, key=key_id)
        st.session_state.escolhas[key_id] = escolha
        return escolha

    elenco_final = []
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"Titulares - {esquema}")
        g = seletor_jogador("🧤 Goleiro Titular", data['GK'], "gk_t")
        if g: elenco_final.append({**g, "Tipo": "Titular"})
        
        for pos, n, aba in [("Defesa", n_def, 'DF'), ("Meio", n_mei, 'MF'), ("Ataque", n_ata, 'FW')]:
            st.write(f"**{pos}**")
            cols = st.columns(2)
            for i in range(n):
                with cols[i%2]:
                    sel = seletor_jogador(f"{pos} {i+1}", data[aba], f"{aba}_{i}")
                    if sel: elenco_final.append({**sel, "Tipo": "Titular"})

    with col2:
        st.subheader("📋 Reservas")
        gr = seletor_jogador("Goleiro Reserva", data['GK'], "gk_r")
        if gr: elenco_final.append({**gr, "Tipo": "Reserva"})
        
        todos = pd.concat([data['DF'], data['MF'], data['FW']])
        for i in range(7):
            r = seletor_jogador(f"Reserva {i+2}", todos, f"res_{i}")
            if r: elenco_final.append({**r, "Tipo": "Reserva"})

    # Barra Lateral
    st.sidebar.markdown("---")
    st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.2f}M", f"Saldo: €{saldo:.2f}M")
    
    if elenco_final:
        df_f = pd.DataFrame(elenco_final)
        media_ov = df_f['Overall'].mean()
        st.sidebar.metric("Média Overall", f"{media_ov:.1f}")

        if st.sidebar.button("💾 Exportar Time"):
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Cabeçalho customizado
                info = [["TIME:", nome_time], ["CUSTO:", f"{custo_atual:.2f}"], ["OVERALL:", f"{media_ov:.1f}"], ["", ""]]
                pd.DataFrame(info).to_excel(writer, index=False, header=False, sheet_name='Time')
                df_f.to_excel(writer, index=False, startrow=5, sheet_name='Time')
            st.sidebar.download_button("Clique aqui para baixar", output.getvalue(), f"{nome_time}.xlsx")
