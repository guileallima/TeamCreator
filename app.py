import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import tempfile
import os
import re

# --- CONFIGURAÇÕES ---
st.set_page_config(page_title="Squad Builder PES 2013", layout="wide")

EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

# --- CSS PARA VELOCIDADE E LAYOUT ---
st.markdown("""
<style>
    [data-testid="stNumberInput"] button {display: none;}
    .block-container {padding-top: 1rem;}
    div[data-testid="column"] button { width: 100%; padding: 0.2rem; font-size: 0.8rem; }
</style>
""", unsafe_allow_html=True)

# --- CARREGAMENTO COM CACHE (O segredo da velocidade) ---
@st.cache_data(ttl=3600)
def load_data():
    file_path = "jogadores.xlsx"
    if not os.path.exists(file_path): return None
    
    tabs = ['GK', 'DF', 'MF', 'FW']
    data = {}
    try:
        for tab in tabs:
            df = pd.read_excel(file_path, sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            df.rename(columns={df.columns[0]: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            
            # Limpeza de preço rápida
            col_p = next((c for c in df.columns if 'PRICE' in c or 'VALUE' in c), None)
            if col_p:
                df['MARKET PRICE'] = pd.to_numeric(
                    df[col_p].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'),
                    errors='coerce'
                ).fillna(0.0)
            
            if 'OVERALL' not in df.columns: df['OVERALL'] = df.iloc[:, 2]
            
            # Mantém apenas o necessário para a memória voar
            df_lean = df[['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']].copy()
            df_lean.sort_values('OVERALL', ascending=False, inplace=True)
            data[tab] = df_lean.to_dict('records')
        return data
    except: return None

data_db = load_data()

# --- ESTADO DA SESSÃO ---
if 'selecoes' not in st.session_state: st.session_state.selecoes = {}
if 'numeros' not in st.session_state: st.session_state.numeros = {}
if 'titular_kit' not in st.session_state: st.session_state.titular_kit = "Padrão 1"
if 'reserva_kit' not in st.session_state: st.session_state.reserva_kit = "Padrão 2"

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📋 Cadastro")
    j1 = st.text_input("Jogador 1")
    j2 = st.text_input("Jogador 2")
    time_nome = st.text_input("Nome do Time", "MEU TIME")
    email_user = st.text_input("Seu E-mail")
    
    st.divider()
    gasto = sum([p['MARKET PRICE'] for p in st.session_state.selecoes.values() if p])
    saldo = ORCAMENTO_MAX - gasto
    st.metric("Saldo Restante", f"€{saldo:.0f}")
    st.progress(min(gasto / ORCAMENTO_MAX, 1.0))
    
    formacao = st.selectbox("Esquema", ["4-3-3", "4-4-2", "3-5-2", "4-5-1", "3-4-3"])
    filtro = st.number_input("Preço Máximo", 0, 3000, 2000)

# --- UNIFORMES (7 COLUNAS) ---
with st.expander("👕 Uniformes", expanded=True):
    t1, t2 = st.tabs(["🏠 Titular", "✈️ Reserva"])
    
    def render_kits(key):
        cols = st.columns(7)
        for i, (nome, img) in enumerate(OPCOES_CAMISAS.items()):
            with cols[i]:
                if os.path.exists(img): st.image(img, use_column_width=True)
                if st.session_state[key] == nome:
                    st.button("✅", key=f"b_{key}_{i}", disabled=True)
                else:
                    if st.button("Usar", key=f"b_{key}_{i}"):
                        st.session_state[key] = nome
                        st.rerun()
        return st.session_state[key]

    with t1: kit_h = render_kits("titular_kit")
    with t2: kit_a = render_kits("reserva_kit")

# --- SELEÇÃO DE JOGADORES ---
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

def seletor(label, lista, key):
    atual = st.session_state.selecoes.get(key)
    usados = [v['NAME'] for k,v in st.session_state.selecoes.items() if v and k != key]
    
    # Filtro eficiente
    ops = [None] + [p for p in lista if p['MARKET PRICE'] <= (saldo + (atual['MARKET PRICE'] if atual else 0)) and p['MARKET PRICE'] <= filtro and p['NAME'] not in usados]
    
    if atual and atual not in ops: ops.insert(1, atual)
    
    c_sel, c_num = st.columns([0.8, 0.2])
    with c_sel:
        idx = ops.index(atual) if atual in ops else 0
        res = st.selectbox(label, ops, index=idx, format_func=lambda x: "Selecione..." if x is None else f"{x['NAME']} (OV:{x['OVERALL']} | €{x['MARKET PRICE']:.0f})", key=f"s_{key}")
        if res != atual:
            st.session_state.selecoes[key] = res
            st.rerun()
    with c_num:
        st.text_input("Nº", key=f"n_{key}", label_visibility="collapsed")

col_a, col_b = st.columns(2)
with col_a:
    st.subheader("Titulares")
    seletor("🧤 Goleiro", data_db['GK'], "gk")
    for i in range(config["Z"]): seletor(f"🛡️ Zagueiro {i+1}", data_db['DF'], f"z_{i}")
    for i in range(config["L"]): seletor(f"🏃 Lateral {i+1}", data_db['DF'] + data_db['MF'], f"l_{i}")
    for i in range(config["M"]): seletor(f"🎯 Meio {i+1}", data_db['MF'], f"m_{i}")
    for i in range(config["A"]): seletor(f"🚀 Atacante {i+1}", data_db['FW'], f"a_{i}")

with col_b:
    st.subheader("Reservas")
    seletor("🧤 GK Res", data_db['GK'], "gkr")
    todos = data_db['DF'] + data_db['MF'] + data_db['FW']
    for i in range(4): seletor(f"Reserva {i+1}", todos, f"r_{i}")

# --- ENVIO ---
if st.button("✅ FINALIZAR INSCRIÇÃO", type="primary", use_container_width=True):
    if not j1 or not j2 or len([p for p in st.session_state.selecoes.values() if p]) < 16:
        st.error("Complete o time (16 jogadores) e os nomes dos técnicos!")
    else:
        with st.spinner("Enviando..."):
            try:
                # 1. Gerar TXT (Apenas IDs e Nomes)
                txt_data = f"TIME: {time_nome}\nTECNICOS: {j1} & {j2}\n\n"
                for k, p in st.session_state.selecoes.items():
                    if p:
                        n = st.session_state.get(f"n_{k}", "")
                        txt_data += f"ID: {p['INDEX']} | Nº: {n} | {p['NAME']}\n"
                
                # 2. Gerar PDF Visual
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"INSCRICAO: {time_nome}", ln=1, align='C')
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 8, txt_data)
                
                # 3. Enviar E-mail
                msg = MIMEMultipart()
                msg['Subject'] = f"Inscricao: {time_nome}"
                msg['From'] = EMAIL_REMETENTE
                msg['To'] = EMAIL_DESTINO
                msg.attach(MIMEText(txt_data, 'plain'))
                
                # Anexo TXT
                part1 = MIMEBase('application', 'octet-stream')
                part1.set_payload(txt_data.encode('utf-8'))
                encoders.encode_base64(part1)
                part1.add_header('Content-Disposition', f'attachment; filename="IDs_{time_nome}.txt"')
                msg.attach(part1)
                
                # Anexo PDF
                part2 = MIMEBase('application', 'pdf')
                part2.set_payload(pdf.output(dest='S').encode('latin-1'))
                encoders.encode_base64(part2)
                part2.add_header('Content-Disposition', 'attachment; filename="Resumo.pdf"')
                msg.attach(part2)
                
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP)
                    s.send_message(msg)
                st.success("✅ ENVIADO COM SUCESSO!")
            except Exception as e:
                st.error(f"Erro: {e}")
