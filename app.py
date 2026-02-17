import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os

# --- CONFIGURAÇÕES DO PROJETO PES 2013 ---
st.set_page_config(page_title="Inscrição PES 2013", layout="wide")

# Credenciais (Mantenha como estão se a Senha de App estiver correta)
EMAIL_REMETENTE = "leallimagui@gmail.com"
SENHA_APP = "nmrytcivcuidhryn"
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

# --- CARREGAMENTO DE DADOS (CACHE) ---
@st.cache_data
def load_data():
    if not os.path.exists("jogadores.xlsx"):
        return None
    try:
        data = {}
        for tab in ['GK', 'DF', 'MF', 'FW']:
            df = pd.read_excel("jogadores.xlsx", sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            df.rename(columns={df.columns[0]: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            # Limpeza de preço
            col_p = next((c for c in df.columns if 'PRICE' in c or 'VALUE' in c), None)
            if col_p:
                df['MARKET PRICE'] = pd.to_numeric(df[col_p].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.'), errors='coerce').fillna(0.0)
            data[tab] = df[['INDEX', 'NAME', 'MARKET PRICE']].to_dict('records')
        return data
    except:
        return None

db = load_data()

# --- ESTADO DA SESSÃO ---
if 'squad' not in st.session_state: st.session_state.squad = {}
if 'nums' not in st.session_state: st.session_state.nums = {}

# --- INTERFACE ---
with st.sidebar:
    st.header("📝 Dados da Inscrição")
    t1 = st.text_input("Técnico 1")
    t2 = st.text_input("Técnico 2")
    time = st.text_input("Nome do Time", "MEU TIME")
    
    st.divider()
    
    # Contador de Jogadores
    selecionados = [p for p in st.session_state.squad.values() if p]
    qtd = len(selecionados)
    
    if qtd < 16:
        st.error(f"Elenco: {qtd} / 16 (Faltam {16-qtd})")
    else:
        st.success("✅ Elenco Completo!")
    
    gasto = sum([p['MARKET PRICE'] for p in selecionados])
    st.metric("Saldo", f"€{ORCAMENTO_MAX - gasto:.0f}")

st.title(f"⚽ Inscrição: {time}")

if not db:
    st.error("Erro: Arquivo 'jogadores.xlsx' não encontrado.")
    st.stop()

# --- SELEÇÃO SIMPLIFICADA ---
def player_box(label, key, lista):
    atual = st.session_state.squad.get(key)
    c1, c2 = st.columns([0.8, 0.2])
    with c1:
        res = st.selectbox(label, [None] + lista, format_func=lambda x: "---" if x is None else f"{x['NAME']} (€{x['MARKET PRICE']:.0f})", key=f"sel_{key}")
        if res != atual:
            st.session_state.squad[key] = res
            st.rerun()
    with c2:
        st.text_input("Nº", key=f"n_{key}")

cols = st.columns(2)
with cols[0]:
    st.subheader("Titulares")
    player_box("Goleiro", "gk", db['GK'])
    for i in range(2): player_box(f"Zagueiro {i+1}", f"df_{i}", db['DF'])
    for i in range(2): player_box(f"Lateral {i+1}", f"lat_{i}", db['DF']+db['MF'])
    for i in range(3): player_box(f"Meio {i+1}", f"mf_{i}", db['MF'])
    for i in range(3): player_box(f"Atacante {i+1}", f"fw_{i}", db['FW'])

with cols[1]:
    st.subheader("Reservas")
    player_box("Goleiro Res.", "gkr", db['GK'])
    for i in range(4): player_box(f"Reserva {i+1}", f"res_{i}", db['DF']+db['MF']+db['FW'])

st.divider()

# --- BOTÃO DE ENVIO COM DIAGNÓSTICO ---
if st.button("🚀 ENVIAR AGORA", type="primary", use_container_width=True):
    if not (t1 and t2):
        st.warning("Preencha os nomes dos técnicos na barra lateral.")
    elif qtd < 16:
        st.warning(f"Você só selecionou {qtd} jogadores. Precisa de 16.")
    else:
        with st.status("Iniciando envio...", expanded=True) as status:
            try:
                # 1. Preparar Dados
                body = f"TIME: {time}\nTECNICOS: {t1} & {t2}\n\nJOGADORES:\n"
                for k, p in st.session_state.squad.items():
                    if p:
                        n = st.session_state.get(f"n_{k}", "S/N")
                        body += f"ID: {p['INDEX']} | Nº: {n} | {p['NAME']}\n"

                # 2. Gerar PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", size=12)
                pdf.multi_cell(0, 10, txt=body)
                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')

                # 3. Email
                msg = MIMEMultipart()
                msg['Subject'] = f"Inscrição PES: {time}"
                msg['From'] = EMAIL_REMETENTE
                msg['To'] = EMAIL_DESTINO
                msg.attach(MIMEText(body, 'plain'))

                # Anexo TXT
                att_txt = MIMEBase('application', 'octet-stream')
                att_txt.set_payload(body.encode('utf-8'))
                encoders.encode_base64(att_txt)
                att_txt.add_header('Content-Disposition', f'attachment; filename="IDs_{time}.txt"')
                msg.attach(att_txt)

                # Anexo PDF
                att_pdf = MIMEBase('application', 'pdf')
                att_pdf.set_payload(pdf_bytes)
                encoders.encode_base64(att_pdf)
                att_pdf.add_header('Content-Disposition', 'attachment; filename="Resumo.pdf"')
                msg.attach(att_pdf)

                status.update(label="Conectando ao Gmail...", state="running")
                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP)
                    s.send_message(msg)
                
                status.update(label="✅ Enviado com Sucesso!", state="complete")
                st.balloons()
            except Exception as e:
                status.update(label=f"❌ Erro: {str(e)}", state="error")
                st.write("Verifique se a Senha de App do Google ainda é válida.")
