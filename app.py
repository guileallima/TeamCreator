import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from io import BytesIO
import tempfile
import os

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
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
    except Exception as e:
        st.error(f"Erro ao carregar 'jogadores.xlsx'.")
        st.stop()

def format_func(row):
    if row is None: return "Selecione..."
    return f"{row['Name']} ({row['Reg. Pos.']}) - OV: {row['Overall']} - €{row['Market Value (M€)']}"

# --- INICIALIZAÇÃO ---
data = load_data()
ORCAMENTO_MAX = 3000.0

if 'escolhas' not in st.session_state:
    st.session_state.escolhas = {}

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
    
    idx = 0
    if st.session_state.escolhas.get(key_id):
        for i, opt in enumerate(opcoes):
            if opt and opt['Name'] == st.session_state.escolhas[key_id]['Name']:
                idx = i
                break
    
    sel = st.selectbox(label, opcoes, index=idx, format_func=format_func, key=key_id)
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

col1, col2 = st.columns([2, 1])
elenco_pdf = []

with col1:
    st.subheader(f"Titulares ({formacao})")
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_pdf.append({**g, "Slot": "Goleiro"})

    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Zagueiro {i+1}"})
        
    df_lat = pd.concat([data['DF'], data['MF']])
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", df_lat, f"lat_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Lateral {i+1}"})

    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_pdf.append({**s, "Slot": f"Meio Campo {i+1}"})

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

st.sidebar.metric("Orçamento Usado", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")

if st.button("🔄 Resetar Time"):
    st.session_state.escolhas = {}
    st.rerun()

# --- FINALIZAÇÃO E ENVIO ---
if st.sidebar.button("✅ FINALIZAR INSCRIÇÃO"):
    if not int1 or not int2 or not email_contato:
        st.sidebar.error("Preencha todos os dados da dupla!")
    elif len(elenco_pdf) < 19:
        st.sidebar.warning("Selecione os 19 jogadores!")
    else:
        try:
            pdf = FPDF()
            pdf.add_page()
            
            # Título
            pdf.set_font("Arial", 'B', 20)
            pdf.cell(200, 15, f"{nome_time.upper()}", ln=True, align='C')
            
            # Imagem no PDF
            if escudo:
                suffix = os.path.splitext(escudo.name)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    tmp.write(escudo.getvalue())
                    tmp_path = tmp.name
                pdf.image(tmp_path, x=85, y=25, w=40)
                pdf.ln(45)
                os.unlink(tmp_path)
            else:
                pdf.ln(10)

            # Dados
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 8, "INFORMAÇÕES GERAIS:", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.cell(200, 7, f"Integrante 1: {int1}", ln=True)
            pdf.cell(200, 7, f"Integrante 2: {int2}", ln=True)
            pdf.cell(200, 7, f"E-mail: {email_contato}", ln=True)
            pdf.cell(200, 7, f"Custo Total: EUR {custo_atual:.0f} | Formação: {formacao}", ln=True)
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(200, 10, "ELENCO ESCOLHIDO:", ln=True)
            pdf.set_font("Arial", size=10)
            for p in elenco_pdf:
                clean_name = str(p['Name']).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(0, 6, f"{p['Slot']}: {clean_name} ({p['Overall']}) - EUR {p['Market Value (M€)']}", ln=True)
            
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            # E-mail com múltiplos anexos
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição: {nome_time} ({int1} / {int2})"
            
            corpo = f"Nova inscrição recebida.\nTime: {nome_time}\nIntegrantes: {int1} e {int2}\n\nO PDF e o Escudo estão em anexo."
            msg.attach(MIMEText(corpo, 'plain'))
            
            # Anexo 1: PDF
            part_pdf = MIMEBase('application', 'octet-stream')
            part_pdf.set_payload(pdf_bytes)
            encoders.encode_base64(part_pdf)
            part_pdf.add_header('Content-Disposition', f"attachment; filename={nome_time}.pdf")
            msg.attach(part_pdf)
            
            # Anexo 2: Escudo separado
            if escudo:
                part_img = MIMEBase('image', os.path.splitext(escudo.name)[1][1:])
                part_img.set_payload(escudo.getvalue())
                encoders.encode_base64(part_img)
                part_img.add_header('Content-Disposition', f"attachment; filename=ESCUDO_{nome_time}{os.path.splitext(escudo.name)[1]}")
                msg.attach(part_img)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_REMETENTE, SENHA_APP)
                server.send_message(msg)
            
            st.success("✅ Inscrição enviada! PDF e Escudo anexados.")
        except Exception as e:
            st.error(f"Erro: {e}")
