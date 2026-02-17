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

# Credenciais de Envio
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

# --- CARREGAMENTO COM CACHE ---
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
            col_p = next((c for c in df.columns if 'PRICE' in c or 'VALUE' in c), None)
            if col_p:
                df['MARKET PRICE'] = pd.to_numeric(
                    df[col_p].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'),
                    errors='coerce'
                ).fillna(0.0)
            if 'OVERALL' not in df.columns: df['OVERALL'] = df.iloc[:, 2]
            df_lean = df[['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']].copy()
            df_lean.sort_values('OVERALL', ascending=False, inplace=True)
            data[tab] = df_lean.to_dict('records')
        return data
    except: return None

data_db = load_data()

# --- SESSÃO ---
if 'selecoes' not in st.session_state: st.session_state.selecoes = {}
if 'numeros' not in st.session_state: st.session_state.numeros = {}
if 'titular_kit' not in st.session_state: st.session_state.titular_kit = "Padrão 1"
if 'reserva_kit' not in st.session_state: st.session_state.reserva_kit = "Padrão 2"

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📋 Cadastro")
    j1 = st.text_input("Jogador 1 (Técnico)")
    j2 = st.text_input("Jogador 2 (Técnico)")
    time_nome = st.text_input("Nome do Time", "MEU TIME")
    email_user = st.text_input("E-mail de Contato")
    
    st.divider()
    jogadores_selecionados = [p for p in st.session_state.selecoes.values() if p]
    qtd_total = len(jogadores_selecionados)
    
    st.subheader("📊 Status do Elenco")
    st.write(f"Jogadores: {qtd_total} / 16")
    if qtd_total < 16:
        st.warning(f"Faltam {16 - qtd_total} jogadores para liberar o envio.")
    else:
        st.success("Elenco Completo!")
    
    gasto = sum([p['MARKET PRICE'] for p in jogadores_selecionados])
    saldo = ORCAMENTO_MAX - gasto
    st.metric("Saldo Restante", f"€{saldo:.0f}")
    st.progress(min(gasto / ORCAMENTO_MAX, 1.0))
    
    formacao = st.selectbox("Esquema", ["4-3-3", "4-4-2", "3-5-2", "4-5-1", "3-4-3"])
    filtro = st.number_input("Preço Máximo", 0, 3000, 2000)

# --- CORPO PRINCIPAL ---
st.header(f"⚽ {time_nome.upper()}")

with st.expander("👕 Configurar Uniformes", expanded=False):
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
    with t1: render_kits("titular_kit")
    with t2: render_kits("reserva_kit")

st.divider()

# --- SELEÇÃO ---
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

def seletor(label, lista, key):
    atual = st.session_state.selecoes.get(key)
    usados = [v['NAME'] for k,v in st.session_state.selecoes.items() if v and k != key]
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

st.divider()

# --- BOTÃO FINAL COM LOG DE ERRO ---
if st.button("✅ FINALIZAR INSCRIÇÃO AGORA", type="primary", use_container_width=True):
    # Verificação de campos vazios
    erros = []
    if not j1 or not j2: erros.append("Nomes dos Técnicos (Jogador 1 e 2)")
    if qtd_total < 16: erros.append(f"Faltam {16 - qtd_total} jogadores no elenco")
    
    if erros:
        st.error(f"Não foi possível enviar! Motivo: {', '.join(erros)}")
    else:
        with st.spinner("⏳ Conectando ao servidor de e-mail e enviando..."):
            try:
                # Dados do TXT
                txt_data = f"TIME: {time_nome.upper()}\nTECNICOS: {j1} & {j2}\nCONTATO: {email_user}\n\n"
                txt_data += "--- ELENCO SELECIONADO ---\n"
                for k, p in st.session_state.selecoes.items():
                    if p:
                        n = st.session_state.get(f"n_{k}", "S/N")
                        txt_data += f"ID: {p['INDEX']} | Nº: {n} | {p['NAME']}\n"
                
                # PDF Simples
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"INSCRICAO: {time_nome.upper()}", ln=1, align='C')
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 8, txt_data)
                
                # E-mail
                msg = MIMEMultipart()
                msg['Subject'] = f"SQUAD PES 2013: {time_nome}"
                msg['From'] = EMAIL_REMETENTE
                msg['To'] = EMAIL_DESTINO
                msg.attach(MIMEText(txt_data, 'plain'))
                
                # Anexos
                p1 = MIMEBase('application', 'octet-stream')
                p1.set_payload(txt_data.encode('utf-8'))
                encoders.encode_base64(p1)
                p1.add_header('Content-Disposition', f'attachment; filename="IDs_{time_nome}.txt"')
                msg.attach(p1)
                
                p2 = MIMEBase('application', 'pdf')
                p2.set_payload(pdf.output(dest='S').encode('latin-1'))
                encoders.encode_base64(p2)
                p2.add_header('Content-Disposition', 'attachment; filename="Inscricao.pdf"')
                msg.attach(p2)
                
                # Envio Real
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP)
                    s.send_message(msg)
                
                st.balloons()
                st.success(f"Tudo certo, Gui! Inscrição do {time_nome} enviada para {EMAIL_DESTINO}.")
                
            except Exception as e:
                st.error(f"Ocorreu um erro no servidor de e-mail: {str(e)}")
