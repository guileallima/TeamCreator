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

st.set_page_config(page_title="PES 2013 Squad Creator", layout="wide")

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

def get_p(r):
    if r is None or not isinstance(r, dict): return 0.0
    for col in ['Market Value (M€)', 'MARKET PRICE', 'market value']:
        if col in r:
            try: return float(r[col])
            except: continue
    return 0.0

def format_func(row):
    if row is None: return "Selecione..."
    name = row.get('Name', row.get('NAME', 'Desconhecido'))
    ov = row.get('Overall', row.get('overall', '??'))
    return f"{name} - OV: {ov} - €{get_p(row)}"

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
    st.header("📋 Inscrição")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    email_participante = st.text_input("E-mail do Participante", key=f"ep_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"nt_{st.session_state.form_id}")
    escudo = st.file_uploader("Upload Escudo", type=["png", "jpg"], key=f"es_{st.session_state.form_id}")
    
    st.markdown("---")
    filtro_preco = st.slider("Filtro: Preço Máximo", 0, 1500, 1500, key=f"sl_{st.session_state.form_id}")
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"fo_{st.session_state.form_id}")

# --- CÁLCULO DE ORÇAMENTO ---
def calc_total():
    return sum([get_p(v) for v in st.session_state.escolhas.values() if v is not None])

custo_atual = calc_total()
saldo_restante = ORCAMENTO_MAX - custo_atual

st.sidebar.metric("Total Gasto", f"€{custo_atual:.1f}")
st.sidebar.metric("Saldo Disponível", f"€{saldo_restante:.1f}", delta=f"{saldo_restante:.1f}")

# --- SELEÇÃO ---
config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    valor_atual = get_p(st.session_state.escolhas.get(key_id))
    outros_nomes = [v.get('Name', v.get('NAME')) for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    # Orçamento disponível para este slot = saldo atual + valor que já estava aqui
    teto_slot = saldo_restante + valor_atual
    
    precos = df_base.apply(get_p, axis=1)
    mask = (precos <= teto_slot) & (precos <= filtro_preco)
    
    n_col = 'Name' if 'Name' in df_base.columns else 'NAME'
    mask = mask & (~df_base[n_col].isin(outros_nomes))
    
    df_f = df_base[mask]
    o_col = 'Overall' if 'Overall' in df_base.columns else 'overall'
    ops = [None] + df_f.sort_values(o_col, ascending=False).to_dict('records')
    
    sel = st.selectbox(label, ops, format_func=format_func, key=f"{key_id}_{st.session_state.form_id}")
    
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

st.title(f"🏆 {nome_time.upper()}")
c1, c2 = st.columns([2, 1])
elenco_final = []

with c1:
    st.subheader(f"Titulares ({formacao})")
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_final.append({**g, "TIPO": "TITULAR"})
    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR"})
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", pd.concat([data['DF'], data['MF']]), f"lat_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR"})
    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR"})
    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if s: elenco_final.append({**s, "TIPO": "TITULAR"})

with c2:
    st.subheader("📋 Reservas (5)")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_final.append({**gr, "TIPO": "RESERVA"})
    tr = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(4):
        r = seletor_smart(f"Reserva {i+2}", tr, f"res_{i}")
        if r: elenco_final.append({**r, "TIPO": "RESERVA"})

if st.button("🔄 Resetar Tudo", on_click=reset_callback): st.rerun()

# --- ENVIO ---
if st.sidebar.button("✅ FINALIZAR E ENVIAR"):
    if not int1 or not int2 or not email_participante:
        st.error("Erro: Preencha os nomes e o e-mail do participante!")
    elif len(elenco_final) < 16:
        st.warning(f"Selecione todos os 16 jogadores (faltam {16 - len(elenco_final)})")
    else:
        try:
            # 1. PDF
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
            pdf.cell(0, 8, f"EMAIL: {email_participante}", ln=True, align='C')
            pdf.ln(5); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 8, " ELENCO", ln=True, fill=True)
            pdf.set_font("Arial", size=10)
            for p in elenco_final:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(100, 6, f"{p['TIPO']}: {n}", 0)
                pdf.cell(90, 6, f"OV: {p.get('Overall', p.get('overall'))}", 0, 1, 'R')
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            # 2. CSV
            df_csv = pd.DataFrame(elenco_final).drop(columns=['TIPO'], errors='ignore')
            csv_str = df_csv.to_csv(sep=';', index=False, encoding='utf-8-sig')

            # 3. MENSAGEM
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição PES: {nome_time}"
            msg.attach(MIMEText(f"Time: {nome_time}\nDupla: {int1} / {int2}\nEmail: {email_participante}", 'plain'))

            # Anexos
            a1 = MIMEBase('application', 'pdf')
            a1.set_payload(pdf_bytes); encoders.encode_base64(a1)
            a1.add_header('Content-Disposition', f'attachment; filename="Escalacao.pdf"'); msg.attach(a1)

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
            st.success("✅ Inscrição enviada com sucesso!")
        except Exception as e:
            st.error(f"Erro no envio: {e}")
