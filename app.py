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

# --- CONFIGURAÇÕES DO PROJETO PES 2013 ---
st.set_page_config(page_title="Inscrição PES 2013", layout="wide")

# Credenciais
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

# --- CSS PARA LAYOUT COMPACTO E THUMBNAILS ---
st.markdown("""
<style>
    [data-testid="stNumberInput"] button {display: none;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    .streamlit-expanderHeader {background-color: #f0f2f6; border-radius: 5px;}
    [data-testid="stHorizontalBlock"] {gap: 5px !important;}
    [data-testid="column"] {padding: 0 !important; min-width: 0 !important;}
    .stButton button { width: 100% !important; border-radius: 4px; padding: 2px 0px !important; font-size: 0.8rem; }
    [data-testid="stImage"] img { border-radius: 5px; }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES ---
def clean_price(val):
    if pd.isna(val) or val == '': return 0.0
    s_val = str(val)
    s_val = re.sub(r'[^\d.,]', '', s_val)
    if not s_val: return 0.0
    s_val = s_val.replace(',', '.')
    try: return float(s_val)
    except: return 0.0

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

@st.cache_data
def load_data():
    if not os.path.exists("jogadores.xlsx"): return None
    try:
        data = {}
        for tab in ['GK', 'DF', 'MF', 'FW']:
            df = pd.read_excel("jogadores.xlsx", sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            df.rename(columns={df.columns[0]: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            col_p = next((c for c in df.columns if any(x in c for x in ['PRICE', 'VALUE'])), None)
            if col_p:
                df['MARKET PRICE'] = df[col_p].apply(clean_price)
            else:
                df['MARKET PRICE'] = 0.0
            if 'OVERALL' not in df.columns and len(df.columns) > 2:
                df['OVERALL'] = df.iloc[:, 2]
            df.sort_values('OVERALL', ascending=False, inplace=True)
            data[tab] = df[['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']].copy()
        return data
    except: return None

db = load_data()

# --- ESTADO DA SESSÃO ---
if 'squad' not in st.session_state: st.session_state.squad = {}
if 'uni_titular_sel' not in st.session_state: st.session_state.uni_titular_sel = "Padrão 1"
if 'uni_reserva_sel' not in st.session_state: st.session_state.uni_reserva_sel = "Padrão 2"

custo_total = sum([p.get('MARKET PRICE', 0.0) for p in st.session_state.squad.values() if p])
saldo = ORCAMENTO_MAX - custo_total

# --- INTERFACE ---
with st.sidebar:
    st.header("📝 Cadastro")
    t1 = st.text_input("Técnico 1")
    t2 = st.text_input("Técnico 2")
    time_nome = st.text_input("Nome do Time", "MEU TIME")
    st.divider()
    qtd_jog = len([p for p in st.session_state.squad.values() if p])
    st.metric("Saldo", f"€{saldo:.0f}")
    st.write(f"Elenco: {qtd_jog}/16")
    st.progress(min(custo_total / ORCAMENTO_MAX, 1.0))

st.title(f"⚽ Inscrição: {time_nome}")

with st.expander("👕 Uniformes", expanded=True):
    t_home, t_away = st.tabs(["🏠 Titular", "✈️ Reserva"])
    def ui_kit(kit_tipo):
        s_key = f"uni_{kit_tipo.lower()}_sel"
        cols = st.columns(7)
        for i in range(1, 8):
            img_path = f"uniforme{i}.jpg"
            with cols[i-1]:
                if os.path.exists(img_path): st.image(img_path, use_column_width=True)
                if st.button("Usar", key=f"btn_{kit_tipo}_{i}"):
                    st.session_state[s_key] = f"Padrão {i}"
                    st.rerun()
                if st.session_state[s_key] == f"Padrão {i}": st.caption("✅")
        c1, c2, c3 = st.columns(3)
        cp = c1.color_picker("Camisa", "#FF0000", key=f"{kit_tipo}_cp")
        cc = c2.color_picker("Calção", "#FFFFFF", key=f"{kit_tipo}_cc")
        cm = c3.color_picker("Meias", "#FFFFFF", key=f"{kit_tipo}_cm")
        return {"modelo": st.session_state[s_key], "cores": [cp, cc, cm]}
    with t_home: kit_h = ui_kit("Titular")
    with t_away: kit_a = ui_kit("Reserva")

# --- SELEÇÃO ---
def seletor(label, lista, key):
    escolha = st.session_state.squad.get(key)
    usados = [v['NAME'] for k,v in st.session_state.squad.items() if v and k != key]
    df_f = lista[(lista['MARKET PRICE'] <= (saldo + (escolha['MARKET PRICE'] if escolha else 0)))]
    if usados: df_f = df_f[~df_f['NAME'].isin(usados)]
    ops = [None] + df_f.to_dict('records')
    if escolha and escolha not in ops: ops.insert(1, escolha)
    c_sel, c_num = st.columns([4, 1])
    res = c_sel.selectbox(label, ops, format_func=lambda x: "---" if x is None else f"{x['NAME']} (OV:{x['OVERALL']} | €{x['MARKET PRICE']:.0f})", key=f"s_{key}")
    num = c_num.text_input("Nº", key=f"n_{key}", max_chars=2)
    if res != escolha:
        st.session_state.squad[key] = res
        st.rerun()
    return res

col_l, col_r = st.columns(2)
lista_final = []
with col_l:
    st.subheader("Titulares")
    pos_list = ['GK', 'DF', 'DF', 'DF', 'DF', 'MF', 'MF', 'MF']
    for i, p_pos in enumerate(pos_list):
        res = seletor(f"{p_pos} {i+1}", db[p_pos] if p_pos in db else db['DF'], f"t_{i}")
        if res: lista_final.append({**res, "K": f"t_{i}"})
with col_r:
    st.subheader("Reservas")
    res_list = ['GK', 'MF', 'MF', 'FW', 'FW', 'FW', 'FW', 'FW']
    for i, p_pos in enumerate(res_list):
        res = seletor(f"Reserva {i+1}", db[p_pos] if p_pos in db else db['FW'], f"r_{i}")
        if res: lista_final.append({**res, "K": f"r_{i}"})

# --- ENVIO FINAL ---
if st.button("🚀 ENVIAR INSCRIÇÃO", type="primary", use_container_width=True):
    if len(lista_final) < 16 or not t1 or not t2:
        st.error("Preencha os nomes e selecione 16 jogadores!")
    else:
        with st.status("Enviando...") as status:
            try:
                # 1. Montar TXT
                txt = f"TIME: {time_nome}\nTECNICOS: {t1} & {t2}\n\n"
                for p in lista_final:
                    n_camisa = st.session_state.get(f"n_{p['K']}", "")
                    txt += f"ID: {p['INDEX']} | Nº: {n_camisa} | {p['NAME']}\n"

                # 2. PDF
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 14)
                pdf.cell(0, 10, f"INSCRICAO PES 2013 - {time_nome}", ln=1, align='C')
                
                # Cores no PDF
                def draw_kit_pdf(kit, x, label):
                    pdf.set_font("Arial", 'B', 8)
                    pdf.text(x, 25, label)
                    bx = x
                    for c in kit['cores']:
                        r,g,b = hex_to_rgb(c)
                        pdf.set_fill_color(r,g,b)
                        pdf.rect(bx, 28, 5, 5, 'F')
                        bx += 6
                
                draw_kit_pdf(kit_h, 10, "TITULAR")
                draw_kit_pdf(kit_a, 50, "RESERVA")
                
                pdf.set_y(40)
                pdf.set_font("Arial", size=10)
                pdf.multi_cell(0, 8, txt)
                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')

                # 3. E-mail
                msg = MIMEMultipart()
                msg['Subject'] = f"Inscricao PES 2013: {time_nome}"
                msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
                msg.attach(MIMEText(txt, 'plain'))

                # ANEXO TXT
                att_txt = MIMEBase('application', 'octet-stream')
                att_txt.set_payload(txt.encode('utf-8'))
                encoders.encode_base64(att_txt)
                att_txt.add_header('Content-Disposition', f'attachment; filename="IDs_{time_nome}.txt"')
                msg.attach(att_txt)

                # ANEXO PDF
                att_pdf = MIMEBase('application', 'pdf')
                att_pdf.set_payload(pdf_bytes)
                encoders.encode_base64(att_pdf)
                att_pdf.add_header('Content-Disposition', 'attachment; filename="Resumo.pdf"')
                msg.attach(att_pdf)

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP)
                    s.send_message(msg)
                
                status.update(label="✅ Enviado com Sucesso!", state="complete")
                st.balloons()
            except Exception as e:
                status.update(label=f"❌ Erro: {e}", state="error")
