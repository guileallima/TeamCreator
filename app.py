import streamlit as st
import pandas as pd
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import os

# --- CONFIGURAÇÃO ---
st.set_page_config(page_title="Inscrição PES 2013", layout="wide")

EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

@st.cache_data
def carregar_dados():
    if not os.path.exists("jogadores.xlsx"): return None
    try:
        abas = pd.read_excel("jogadores.xlsx", sheet_name=None)
        dados = {}
        for nome, df in abas.items():
            df.columns = df.columns.str.strip().str.upper()
            df.rename(columns={df.columns[0]: 'INDEX'}, inplace=True)
            p_col = next((c for c in df.columns if 'PRICE' in c or 'VALUE' in c), None)
            if p_col:
                df['MARKET PRICE'] = pd.to_numeric(df[p_col].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
            dados[nome] = df[['INDEX', 'NAME', 'MARKET PRICE']].to_dict('records')
        return dados
    except: return None

db = carregar_dados()

# --- INTERFACE ---
with st.sidebar:
    st.header("📋 Cadastro")
    t1 = st.text_input("Técnico 1", key="tec1")
    t2 = st.text_input("Técnico 2", key="tec2")
    time_nome = st.text_input("Nome do Time", "MEU TIME", key="tname")
    
    st.divider()
    
    # Coleta de dados em tempo real para o checklist
    jogadores_validados = []
    gasto_atual = 0.0
    for i in range(16):
        p = st.session_state.get(f"sel_{i}")
        if p:
            jogadores_validados.append(p)
            gasto_atual += p.get('MARKET PRICE', 0.0)
    
    st.metric("Saldo", f"€{ORCAMENTO_MAX - gasto_atual:.0f}")
    
    # CHECKLIST DE ENVIO
    st.subheader("✅ Checklist")
    c1 = "✅ Nomes OK" if (t1 and t2) else "❌ Faltam Técnicos"
    c2 = f"✅ Elenco OK ({len(jogadores_validados)}/16)" if len(jogadores_validados) == 16 else f"❌ Elenco ({len(jogadores_validados)}/16)"
    
    st.write(c1)
    st.write(c2)

st.title(f"⚽ Squad Builder: {time_nome}")

if not db:
    st.error("Arquivo 'jogadores.xlsx' não encontrado!")
    st.stop()

# --- SELEÇÃO ---
col1, col2 = st.columns(2)
pos = ['GK', 'DF', 'DF', 'DF', 'DF', 'MF', 'MF', 'MF', 'MF', 'FW', 'FW', 'GK', 'DF', 'MF', 'FW', 'FW']

for i in range(16):
    container = col1 if i < 8 else col2
    with container:
        c_sel, c_num = st.columns([0.8, 0.2])
        c_sel.selectbox(
            f"Jogador {i+1} ({pos[i]})", 
            [None] + db.get(pos[i], []), 
            format_func=lambda x: "---" if x is None else f"{x['NAME']} (€{x['MARKET PRICE']:.0f})",
            key=f"sel_{i}"
        )
        c_num.text_input("Nº", key=f"num_{i}", max_chars=2)

st.divider()

# --- FUNÇÃO DE ENVIO ---
def disparar_email(lista, tec1, tec2, tname):
    try:
        corpo = f"TIME: {tname.upper()}\nTECNICOS: {tec1} & {tec2}\n\n"
        for p in lista:
            corpo += f"ID: {p['id']} | Nome: {p['nome']} | Nº: {p['num']}\n"

        msg = MIMEMultipart()
        msg['Subject'] = f"Inscrição PES 2013: {tname}"
        msg['From'] = EMAIL_REMETENTE
        msg['To'] = EMAIL_DESTINO
        msg.attach(MIMEText(corpo, 'plain'))

        part = MIMEBase('application', 'octet-stream')
        part.set_payload(corpo.encode('utf-8'))
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="IDs_{tname}.txt"')
        msg.attach(part)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, str(e)

# --- BOTÃO DE FINALIZAÇÃO ---
if st.button("🚀 FINALIZAR E ENVIAR AGORA", type="primary", use_container_width=True):
    if not (t1 and t2):
        st.error("ERRO: Preencha os nomes dos técnicos na lateral!")
    elif len(jogadores_validados) < 16:
        st.error(f"ERRO: Selecione os 16 jogadores! (Você selecionou {len(jogadores_validados)})")
    else:
        with st.spinner("Enviando e-mail..."):
            # Monta a lista final para envio
            dados_finais = []
            for i in range(16):
                jog = st.session_state[f"sel_{i}"]
                n = st.session_state.get(f"num_{i}", "")
                dados_finais.append({"id": jog['INDEX'], "nome": jog['NAME'], "num": n})
            
            sucesso, erro = disparar_email(dados_finais, t1, t2, time_nome)
            
            if sucesso:
                st.success("✅ INSCRIÇÃO ENVIADA COM SUCESSO!")
                st.balloons()
            else:
                st.error(f"❌ FALHA NO SERVIDOR: {erro}")
