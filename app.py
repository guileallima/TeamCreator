import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from io import StringIO
import tempfile
import os

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"

st.set_page_config(page_title="PES 2013 Squad Builder", layout="wide")

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
        st.error(f"Erro ao carregar 'jogadores.xlsx': {e}")
        st.stop()

# --- FUNÇÃO DE PREÇO (ROBUSTA) ---
def get_p(r):
    if r is None: return 0.0
    # Verifica colunas possíveis de preço
    for col in ['Market Value (M€)', 'MARKET PRICE', 'market value', 'Market Value']:
        if col in r:
            try:
                val = r[col]
                return float(val)
            except:
                continue
    return 0.0

def format_func(row):
    if row is None: return "Selecione..."
    name = row.get('Name', row.get('NAME', 'Desconhecido'))
    ov = row.get('Overall', row.get('overall', '??'))
    return f"{name} - OV: {ov} - €{get_p(row):.1f}"

# --- ESTADO E RESET ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.form_id += 1

data = load_data()
ORCAMENTO_MAX = 2000.0

# --- SIDEBAR ---
with st.sidebar:
    st.header("📋 Cadastro")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    email_user = st.text_input("E-mail do Participante", key=f"eu_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"nt_{st.session_state.form_id}")
    escudo = st.file_uploader("Upload Escudo", type=["png", "jpg"], key=f"es_{st.session_state.form_id}")
    
    st.markdown("---")
    # Filtro de preço que agora interage com a busca
    filtro_p = st.slider("Filtrar por Preço Máximo", 0.0, 1500.0, 1500.0, key=f"sl_{st.session_state.form_id}")
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"fo_{st.session_state.form_id}")

# --- CÁLCULO DINÂMICO ---
custo_total = sum([get_p(v) for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_total

st.sidebar.metric("Orçamento Gasto", f"€{custo_total:.1f}")
st.sidebar.metric("Saldo Restante", f"€{saldo:.1f}", delta=f"{saldo:.1f}")

# --- LÓGICA DE SELEÇÃO ---
config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    # Valor que já estava ocupando este espaço
    val_atual = get_p(st.session_state.escolhas.get(key_id))
    outros = [v.get('Name', v.get('NAME')) for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    # Filtro triplo: Orçamento disponível + Filtro Manual + Não Duplicado
    df_f = df_base[
        (df_base.apply(get_p, axis=1) <= (saldo + val_atual)) & 
        (df_base.apply(get_p, axis=1) <= filtro_p)
    ]
    
    n_col = 'Name' if 'Name' in df_base.columns else 'NAME'
    df_f = df_f[~df_f[n_col].isin(outros)]
    
    o_col = 'Overall' if 'Overall' in df_base.columns else 'overall'
    ops = [None] + df_f.sort_values(o_col, ascending=False).to_dict('records')
    
    sel = st.selectbox(label, ops, format_func=format_func, key=f"{key_id}_{st.session_state.form_id}")
    
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

# --- CONSTRUÇÃO DA PÁGINA ---
st.title(f"⚽ {nome_time.upper()}")
c1, c2 = st.columns([2, 1])
elenco = []

with c1:
    st.subheader(f"Titulares ({formacao})")
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco.append({**g, "T": "TITULAR"})
    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"z_{i}")
        if s: elenco.append({**s, "T": "TITULAR"})
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", pd.concat([data['DF'], data['MF']]), f"l_{i}")
        if s: elenco.append({**s, "T": "TITULAR"})
    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"m_{i}")
        if s: elenco.append({**s, "T": "TITULAR"})
    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"a_{i}")
        if s: elenco.append({**s, "T": "TITULAR"})

with c2:
    st.subheader("📋 Reservas (5)")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco.append({**gr, "T": "RESERVA"})
    tr = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(4): # 4 linha + 1 gk = 5
        r = seletor_smart(f"Reserva {i+2}", tr, f"res_{i}")
        if r: elenco.append({**r, "T": "RESERVA"})

if st.button("🔄 Resetar Tudo", on_click=reset_callback): st.rerun()

# --- FINALIZAÇÃO ---
if st.sidebar.button("✅ FINALIZAR E ENVIAR"):
    if not int1 or not int2 or not email_user:
        st.sidebar.error("Preencha Integrantes e E-mail!")
    elif len(elenco) < 16:
        st.sidebar.warning(f"Selecione os 16 jogadores (Faltam {16 - len(elenco)})")
    else:
        try:
            # PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(30, 30, 30); pdf.rect(0, 0, 210, 45, 'F')
            if escudo:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(escudo.getvalue()); tp = tmp.name
                pdf.image(tp, x=90, y=5, w=30); os.unlink(tp)
            pdf.set_text_color(255, 255, 255); pdf.set_font("Arial", 'B', 22)
            pdf.set_y(33); pdf.cell(190, 10, nome_time.upper(), ln=True, align='C')
            pdf.set_text_color(0, 0, 0); pdf.ln(15); pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 8, f"DUPLA: {int1} & {int2}", ln=True, align='C')
            pdf.cell(0, 8, f"EMAIL: {email_user}", ln=True, align='C')
            pdf.ln(5); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 8, " ESCALAÇÃO", ln=True, fill=True)
            pdf.set_font("Arial", size=10)
            for p in elenco:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(100, 6, f"[{p['T']}] {n}", 0)
                pdf.cell(90, 6, f"OV: {p.get('Overall', p.get('overall'))}", 0, 1, 'R')
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            # CSV
            df_csv = pd.DataFrame(elenco).drop(columns=['T'], errors='ignore')
            csv_str = df_csv.to_csv(sep=';', index=False, encoding='utf-8-sig')

            # EMAIL
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição PES: {nome_time}"
            msg.attach(MIMEText(f"Time: {nome_time}\nDupla: {int1}/{int2}\nContato: {email_user}", 'plain'))

            a1 = MIMEBase('application', 'pdf')
            a1.set_payload(pdf_bytes); encoders.encode_base64(a1)
            a1.add_header('Content-Disposition', f'attachment; filename="Relatorio.pdf"'); msg.attach(a1)

            a2 = MIMEBase('text', 'csv')
            a2.set_payload(csv_str.encode('utf-8-sig')); encoders.encode_base64(a2)
            a2.add_header('Content-Disposition', f'attachment; filename="Dados_Jogo.csv"'); msg.attach(a2)

            if escudo:
                a3 = MIMEBase('image', 'png')
                a3.set_payload(escudo.getvalue()); encoders.encode_base64(a3)
                a3.add_header('Content-Disposition', f'attachment; filename="escudo.png"'); msg.attach(a3)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP)
                s.send_message(msg)
            st.success("✅ Inscrição Enviada!")
        except Exception as e:
            st.error(f"Erro técnico: {e}")
