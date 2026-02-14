import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from io import BytesIO

# --- CONFIGURAÇÕES DE E-MAIL (PREENCHA AQUI) ---
EMAIL_REMETENTE = "seu_email@gmail.com" 
SENHA_APP = "nmry tciv cuid hryn" # Aquela senha que você gerou no Google
EMAIL_DESTINO = "leallimagui@gmail.com"

st.set_page_config(page_title="Inscrição PES 2013", layout="wide")

@st.cache_data
def load_data():
    file = "jogadores.xlsx"
    tabs = ['GK', 'DF', 'MF', 'FW']
    data = {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
    for tab in data:
        data[tab].columns = data[tab].columns.str.strip()
    return data

def format_func(row):
    if row is None: return "Selecione..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}"

# --- INICIALIZAÇÃO ---
data = load_data()
ORCAMENTO_MAX = 3000.0

if 'escolhas' not in st.session_state:
    st.session_state.escolhas = {}

# --- LÓGICA DE RESET ---
def reset_team():
    st.session_state.escolhas = {}
    st.rerun()

# --- CÁLCULO DE SALDO ---
custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_atual

# --- INTERFACE ---
st.title("🏆 Inscrição de Elenco - PES 2013")

with st.sidebar:
    st.header("Dados da Dupla")
    nome_dupla = st.text_input("Nome Completo da Dupla")
    email_contato = st.text_input("E-mail de Contato")
    nome_time = st.text_input("Nome do Time", "Meu Time")
    
    escudo = st.file_uploader("Upload do Escudo do Time", type=["png", "jpg", "jpeg"])
    if escudo:
        st.image(escudo, width=100)
    
    st.markdown("---")
    formacao = st.selectbox("Formação", [
        "4-5-1 (2 ZAG, 2 LAT, 5 MEI, 1 ATA)",
        "3-4-3 (3 ZAG, 2 LAT, 2 MEI, 3 ATA)",
        "4-4-2 (2 ZAG, 2 LAT, 4 MEI, 2 ATA)",
        "4-3-3 (2 ZAG, 2 LAT, 3 MEI, 3 ATA)",
        "3-5-2 (3 ZAG, 2 LAT, 3 MEI, 2 ATA)"
    ])

# Definição das regras de posição
config_form = {
    "4-5-1 (2 ZAG, 2 LAT, 5 MEI, 1 ATA)": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3 (3 ZAG, 2 LAT, 2 MEI, 3 ATA)": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2 (2 ZAG, 2 LAT, 4 MEI, 2 ATA)": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3 (2 ZAG, 2 LAT, 3 MEI, 3 ATA)": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2 (3 ZAG, 2 LAT, 3 MEI, 2 ATA)": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    outros_nomes = [v['Name'] for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    valor_atual = st.session_state.escolhas.get(key_id, {}).get('Market Value (M€)', 0) if st.session_state.escolhas.get(key_id) else 0
    
    df_f = df_base[(df_base['Market Value (M€)'] <= (saldo + valor_atual)) & (~df_base['Name'].isin(outros_nomes))]
    opcoes = [None] + df_f.sort_values('Overall', ascending=False).to_dict('records')
    
    index_atual = 0
    if st.session_state.escolhas.get(key_id):
        for i, opt in enumerate(opcoes):
            if opt and opt['Name'] == st.session_state.escolhas[key_id]['Name']:
                index_atual = i
                break
    
    sel = st.selectbox(label, opcoes, index=index_atual, format_func=format_func, key=key_id)
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

# --- MONTAGEM DO TIME ---
col1, col2 = st.columns([2, 1])
elenco_pdf = []

with col1:
    st.subheader("Titulares")
    # Goleiro
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_pdf.append({**g, "Slot": "Goleiro"})

    # Zagueiros (Podem ser DF ou GK por erro, mas pela regra: Zagueiros + Laterais)
    df_zag_lat = pd.concat([data['DF']]) # DF já contém CB, LB, RB no PES
    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_pdf.append({**s, "Slot": "Zagueiro"})
        
    # Laterais (Zagueiros, Laterais ou Meio Campo)
    df_lat_rules = pd.concat([data['DF'], data['MF']])
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", df_lat_rules, f"lat_{i}")
        if s: elenco_pdf.append({**s, "Slot": "Lateral"})

    # Meio Campo (Somente Meio Campo)
    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_pdf.append({**s, "Slot": "Meio Campo"})

    # Atacante (Somente Atacante)
    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if s: elenco_pdf.append({**s, "Slot": "Atacante"})

with col2:
    st.subheader("Reservas")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_pdf.append({**gr, "Slot": "Reserva GK"})
    
    # Reservas gerais (DF, MF, FW)
    todos_res = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(7):
        r = seletor_smart(f"Reserva {i+2}", todos_res, f"res_{i}")
        if r: elenco_pdf.append({**r, "Slot": "Reserva"})

# --- FOOTER E PDF ---
st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")

# Botão de Reset no canto inferior direito
st.markdown("---")
c1, c2, c3 = st.columns([4,1,1])
with c3:
    if st.button("🔄 Resetar Tudo"):
        reset_team()

# Envio de PDF
if st.sidebar.button("✅ FINALIZAR E ENVIAR"):
    if not nome_dupla or not email_contato:
        st.sidebar.error("Preencha o nome da dupla e e-mail!")
    elif len(elenco_pdf) < 18:
        st.sidebar.warning("Selecione todos os 18 jogadores!")
    else:
        try:
            # Gerar PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, f"Inscricao: {nome_time}", ln=True, align='C')
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"Dupla: {nome_dupla}", ln=True)
            pdf.cell(200, 10, f"E-mail: {email_contato}", ln=True)
            pdf.cell(200, 10, f"Custo Total: {custo_atual} | Media Over: {pd.DataFrame(elenco_pdf)['Overall'].mean():.1f}", ln=True)
            pdf.ln(10)
            
            for p in elenco_pdf:
                pdf.cell(0, 8, f"{p['Slot']}: {p['Name']} ({p['Overall']}) - €{p['Market Value (M€)']}", ln=True)
            
            pdf_out = pdf.output(dest='S').encode('latin-1')

            # Enviar E-mail
            msg = MIMEMultipart()
            msg['From'] = EMAIL_REMETENTE
            msg['To'] = EMAIL_DESTINO
            msg['Subject'] = f"Nova Inscrição PES: {nome_time} - {nome_dupla}"
            
            msg.attach(MIMEText(f"Inscrição recebida de {nome_dupla} ({email_contato})", 'plain'))
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_out)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={nome_time}.pdf")
            msg.attach(part)
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(msg)
            server.quit()
            
            st.success("✅ Inscrição enviada com sucesso para a organização!")
        except Exception as e:
            st.error(f"Erro ao enviar: {e}")
