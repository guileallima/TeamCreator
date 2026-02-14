import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from io import BytesIO, StringIO
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
    except:
        st.error("Erro ao carregar 'jogadores.xlsx'.")
        st.stop()

def format_func(row):
    if row is None: return "Selecione..."
    name = row.get('Name', row.get('NAME', 'Desconhecido'))
    overall = row.get('Overall', row.get('Overall', '??'))
    price = row.get('Market Value (M€)', row.get('MARKET PRICE', 0))
    return f"{name} - OV: {overall} - €{price}"

if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.form_id += 1

data = load_data()
ORCAMENTO_MAX = 3000.0

# Cálculo de custo dinâmico
def get_p(r): return r.get('Market Value (M€)', r.get('MARKET PRICE', 0))
custo_at = sum([get_p(v) for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_at

st.title("⚽ PES 2013 - Inscrição Oficial")

with st.sidebar:
    st.header("Dados do Time")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    email_contato = st.text_input("E-mail", key=f"em_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"nt_{st.session_state.form_id}")
    escudo = st.file_uploader("Escudo", type=["png", "jpg"], key=f"es_{st.session_state.form_id}")
    if escudo: st.image(escudo, width=80)
    st.markdown("---")
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"fo_{st.session_state.form_id}")

config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    v_at = get_p(st.session_state.escolhas.get(key_id, {}))
    outros = [v.get('Name', v.get('NAME')) for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    df_f = df_base[(df_base.apply(get_p, axis=1) <= (saldo + v_at))]
    n_col = 'Name' if 'Name' in df_base.columns else 'NAME'
    df_f = df_f[~df_f[n_col].isin(outros)]
    o_col = 'Overall' if 'Overall' in df_base.columns else 'overall'
    ops = [None] + df_f.sort_values(o_col, ascending=False).to_dict('records')
    sel = st.selectbox(label, ops, format_func=format_func, key=f"{key_id}_{st.session_state.form_id}")
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

col1, col2 = st.columns([2, 1])
elenco_final = []

with col1:
    st.subheader(f"Titulares - {formacao}")
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_final.append({**g, "TIPO": "TITULAR", "ORDEM": 1})
    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR", "ORDEM": 2})
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", pd.concat([data['DF'], data['MF']]), f"lat_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR", "ORDEM": 3})
    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR", "ORDEM": 4})
    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR", "ORDEM": 5})

with col2:
    st.subheader("📋 Reservas")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_final.append({**gr, "TIPO": "RESERVA", "ORDEM": 6})
    tr = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(7):
        r = seletor_smart(f"Reserva {i+2}", tr, f"res_{i}")
        if r: elenco_final.append({**r, "TIPO": "RESERVA", "ORDEM": 7})

st.sidebar.metric("Custo Total", f"€{custo_at:.0f}", f"Saldo: €{saldo:.0f}")

if st.button("🔄 Resetar", on_click=reset_callback): st.rerun()

if st.sidebar.button("🚀 FINALIZAR E ENVIAR"):
    if not int1 or not int2 or len(elenco_final) < 19:
        st.sidebar.error("Selecione os 19 jogadores e preencha os nomes!")
    else:
        try:
            # 1. PDF TRANSMISSÃO TV
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(20, 20, 20); pdf.rect(0, 0, 210, 45, 'F')
            if escudo:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(escudo.getvalue()); t_p = tmp.name
                pdf.image(t_p, x=90, y=5, w=30); os.unlink(t_p)
            pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 20)
            pdf.set_y(32); pdf.cell(190, 10, nome_time.upper(), ln=True, align='C')
            
            pdf.set_text_color(0, 0, 0); pdf.ln(15); pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"DUPLA: {int1} & {int2} | CUSTO: {custo_at}", ln=True, align='C')
            
            pdf.set_fill_color(230, 230, 230); pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, " ESCALAÇÃO TITULAR", ln=True, fill=True)
            pdf.set_font("Arial", size=10)
            for p in sorted([x for x in elenco_final if x['TIPO'] == 'TITULAR'], key=lambda x: x['ORDEM']):
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(100, 6, f" - {n}", border=0)
                pdf.cell(90, 6, f"OV: {p.get('Overall', p.get('overall'))}", ln=True, align='R')
            
            pdf.ln(5); pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, " BANCO DE RESERVAS", ln=True, fill=True)
            pdf.set_font("Arial", size=10)
            for p in [x for x in elenco_final if x['TIPO'] == 'RESERVA']:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(100, 6, f"   {n}", border=0)
                pdf.cell(90, 6, f"OV: {p.get('Overall', p.get('overall'))}", ln=True, align='R')
            
            pdf_out = pdf.output(dest='S').encode('latin-1')

            # 2. CSV PARA O JOGO (IMPORTANTE)
            df_csv = pd.DataFrame(elenco_final).drop(columns=['TIPO', 'ORDEM'], errors='ignore')
            csv_data = df_csv.to_csv(sep=';', index=False, encoding='utf-8-sig')

            # 3. ENVIO
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição: {nome_time} ({int1}/{int2})"
            msg.attach(MIMEText(f"Inscrição concluída.\nTime: {nome_time}\nDupla: {int1} e {int2}", 'plain'))

            # Anexo PDF
            att_pdf = MIMEBase('application', 'pdf')
            att_pdf.set_payload(pdf_out); encoders.encode_base64(att_pdf)
            att_pdf.add_header('Content-Disposition', f'attachment; filename="{nome_time}_TV.pdf"'); msg.attach(att_pdf)

            # Anexo CSV (Correção aqui para garantir visibilidade)
            att_csv = MIMEBase('text', 'csv')
            att_csv.set_payload(csv_data.encode('utf-8-sig')); encoders.encode_base64(att_csv)
            att_csv.add_header('Content-Disposition', f'attachment; filename="{nome_time}_Importar.csv"'); msg.attach(att_csv)

            if escudo:
                att_img = MIMEBase('image', 'png')
                att_img.set_payload(escudo.getvalue()); encoders.encode_base64(att_img)
                att_img.add_header('Content-Disposition', f'attachment; filename="escudo.png"'); msg.attach(att_img)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_REMETENTE, SENHA_APP)
                server.send_message(msg)
            
            st.success("✅ Enviado! PDF, CSV e Escudo estão no e-mail.")
        except Exception as e:
            st.error(f"Erro: {e}")
