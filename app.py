import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from io import BytesIO

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "seu_email@gmail.com" 
SENHA_APP = "nmry tciv cuid hryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"

st.set_page_config(page_title="Inscrição PES 2013", layout="wide")

@st.cache_data
def load_data():
    file = "jogadores.xlsx"
    try:
        tabs = ['GK', 'DF', 'MF', 'FW']
        data = {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
        for tab in data:
            data[tab].columns = data[tab].columns.str.strip()
        return data
    except:
        st.error("Erro ao carregar 'jogadores.xlsx'.")
        st.stop()

def format_func(row):
    if row is None: return "Selecione..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}"

# --- INICIALIZAÇÃO ---
data = load_data()
ORCAMENTO_MAX = 3000.0

if 'escolhas' not in st.session_state:
    st.session_state.escolhas = {}

# --- CÁLCULO DE SALDO ---
custo_atual = sum([v['Market Value (M€)'] for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_atual

# --- INTERFACE ---
st.title("🏆 Inscrição de Elenco - PES 2013")

with st.sidebar:
    st.header("Dados da Inscrição")
    int1 = st.text_input("Integrante 1 (Nome Completo)")
    int2 = st.text_input("Integrante 2 (Nome Completo)")
    email_contato = st.text_input("E-mail de Contato")
    nome_time = st.text_input("Nome do Time", "Meu Time")
    
    escudo = st.file_uploader("Upload do Escudo", type=["png", "jpg", "jpeg"])
    if escudo: st.image(escudo, width=80)
    
    st.markdown("---")
    formacao = st.selectbox("Escolha a Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"])

# Configuração técnica das posições baseada na sua descrição
config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    outros_nomes = [v['Name'] for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    v_atual = st.session_state.escolhas.get(key_id, {}).get('Market Value (M€)', 0) if st.session_state.escolhas.get(key_id) else 0
    
    df_f = df_base[(df_base['Market Value (M€)'] <= (saldo + v_atual)) & (~df_base['Name'].isin(outros_nomes))]
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

# --- CORPO DA PÁGINA ---
col1, col2 = st.columns([2, 1])
elenco_pdf = []

with col1:
    st.subheader(f"Titulares ({formacao})")
    # Goleiro
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_pdf.append({**g, "Slot": "Goleiro"})

    # Zagueiros (Regra: Laterais e Zagueiros da aba DF)
    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Zagueiro {i+1}"})
        
    # Laterais (Regra: Zagueiros, Laterais ou Meio-campo - abas DF e MF)
    df_lat = pd.concat([data['DF'], data['MF']])
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", df_lat, f"lat_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Lateral {i+1}"})

    # Meio Campo (Somente MF)
    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Meio Campo {i+1}"})

    # Atacante (Somente FW)
    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Atacante {i+1}"})

with col2:
    st.subheader("📋 Reservas")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_pdf.append({**gr, "Slot": "Reserva GK"})
    
    todos_res = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(7):
        r = seletor_smart(f"Reserva {i+2}", todos_res, f"res_{i}")
        if r: elenco_pdf.append({**r, "Slot": f"Reserva {i+2}"})

# --- FINALIZAÇÃO ---
st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")

c1, c2, c3 = st.columns([4,1,1])
with c3:
    if st.button("🔄 Resetar Time"):
        st.session_state.escolhas = {}
        st.rerun()

if st.sidebar.button("✅ FINALIZAR INSCRIÇÃO"):
    if not int1 or not int2 or not email_contato:
        st.sidebar.error("Preencha todos os dados da dupla!")
    elif len(elenco_pdf) < 19:
        st.sidebar.warning("Selecione os 11 titulares e 8 reservas!")
    else:
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, f"INSCRICAO PES 2013 - {nome_time}", ln=True, align='C')
            pdf.ln(5)
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, f"Integrante 1: {int1}", ln=True)
            pdf.cell(200, 10, f"Integrante 2: {int2}", ln=True)
            pdf.cell(200, 10, f"E-mail: {email_contato}", ln=True)
            pdf.cell(200, 10, f"Custo: {custo_atual} | Formacao: {formacao}", ln=True)
            pdf.ln(5)
            pdf.cell(200, 10, "ELENCO ESCOLHIDO:", ln=True)
            for p in elenco_pdf:
                # Ajuste para evitar caracteres especiais no PDF simples
                clean_name = p['Name'].encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(0, 7, f"{p['Slot']}: {clean_name} ({p['Overall']})", ln=True)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição: {nome_time} ({int1} / {int2})"
            msg.attach(MIMEText(f"Nova inscrição recebida.\nTime: {nome_time}\nDupla: {int1} e {int2}", 'plain'))
            
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename={nome_time}.pdf")
            msg.attach(part)
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(EMAIL_REMETENTE, SENHA_APP)
            server.send_message(msg)
            server.quit()
            
            st.success("✅ Inscrição enviada com sucesso!")
        except Exception as e:
            st.error(f"Erro ao enviar: {e}")
