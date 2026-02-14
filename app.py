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

def get_p(r):
    if r is None or not isinstance(r, dict): return 0
    return r.get('Market Value (M€)', r.get('MARKET PRICE', r.get('market value', 0)))

def format_func(row):
    if row is None: return "Selecione..."
    name = row.get('Name', row.get('NAME', 'Desconhecido'))
    ov = row.get('Overall', row.get('overall', '??'))
    return f"{name} - OV: {ov} - €{get_p(row)}"

# --- ESTADO DA SESSÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.form_id += 1

data = load_data()
ORCAMENTO_MAX = 2000.0

# --- INTERFACE LATERAL ---
with st.sidebar:
    st.header("📋 Dados do Time")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"nt_{st.session_state.form_id}")
    escudo = st.file_uploader("Escudo", type=["png", "jpg"], key=f"es_{st.session_state.form_id}")
    
    st.markdown("---")
    st.subheader("🔍 Filtros de Busca")
    # Filtro de preço adicional solicitado
    filtro_preco = st.slider("Preço Máximo por Jogador", 0, 1500, 1500)
    
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"fo_{st.session_state.form_id}")

# --- CÁLCULO DE SALDO ---
custo_at = sum([get_p(v) for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_at

config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    v_at = get_p(st.session_state.escolhas.get(key_id))
    outros = [v.get('Name', v.get('NAME')) for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    # Aplica filtros: Orçamento restante + Filtro de preço manual + Duplicidade
    df_f = df_base[
        (df_base.apply(lambda x: get_p(x) <= (saldo + v_at), axis=1)) & 
        (df_base.apply(lambda x: get_p(x) <= filtro_preco, axis=1))
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

# --- CORPO ---
st.title("🏆 PES 2013 - Inscrição")
col1, col2 = st.columns([2, 1])
elenco_final = []

with col1:
    st.subheader(f"Titulares - {formacao}")
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

with col2:
    st.subheader("📋 Reservas (5)")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_final.append({**gr, "TIPO": "RESERVA"})
    
    todos_res = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(4): # 4 reservas de linha + 1 goleiro = 5 no total
        r = seletor_smart(f"Reserva {i+2}", todos_res, f"res_{i}")
        if r: elenco_final.append({**r, "TIPO": "RESERVA"})

st.sidebar.metric("Orçamento Usado", f"€{custo_at:.0f}", f"Saldo: €{saldo:.0f}")
if st.button("🔄 Resetar Time", on_click=reset_callback): st.rerun()

# --- EXPORTAÇÃO ---
if st.sidebar.button("✅ FINALIZAR E ENVIAR"):
    if not int1 or not int2 or len(elenco_final) < 16:
        st.sidebar.error("Selecione os 16 jogadores e preencha a dupla!")
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
            pdf.cell(0, 10, f"DUPLA: {int1} & {int2}", ln=True, align='C')
            pdf.set_fill_color(240, 240, 240); pdf.cell(0, 8, " TITULARES", ln=True, fill=True)
            for p in [x for x in elenco_final if x['TIPO'] == 'TITULAR']:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.set_font("Arial", size=10); pdf.cell(100, 6, f" - {n}", 0)
                pdf.cell(90, 6, f"OV: {p.get('Overall', p.get('overall'))}", 0, align='R', ln=True)
            pdf_out = pdf.output(dest='S').encode('latin-1')

            # 2. CSV
            df_csv = pd.DataFrame(elenco_final).drop(columns=['TIPO'], errors='ignore')
            csv_str = df_csv.to_csv(sep=';', index=False, encoding='utf-8-sig')

            # 3. ENVIO
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição PES: {nome_time}"
            msg.attach(MIMEText(f"Time: {nome_time}\nDupla: {int1} e {int2}", 'plain'))

            att1 = MIMEBase('application', 'pdf')
            att1.set_payload(pdf_out); encoders.encode_base64(att1)
            att1.add_header('Content-Disposition', f'attachment; filename="Escalacao.pdf"'); msg.attach(att1)

            att2 = MIMEBase('text', 'csv')
            att2.set_payload(csv_str.encode('utf-8-sig')); encoders.encode_base64(att2)
            att2.add_header('Content-Disposition', f'attachment; filename="Dados_Jogo.csv"'); msg.attach(att2)

            if escudo:
                att3 = MIMEBase('image', 'png')
                att3.set_payload(escudo.getvalue()); encoders.encode_base64(att3)
                att3.add_header('Content-Disposition', f'attachment; filename="escudo.png"'); msg.attach(att3)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP)
                s.send_message(msg)
            st.success("✅ Inscrição enviada com Sucesso!")
        except Exception as e:
            st.error(f"Erro no envio: {e}")
