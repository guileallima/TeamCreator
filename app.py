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

# --- CONFIGURAÇÕES DE E-MAIL ---
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"

# --- COLUNAS PADRÃO PES 2013 ---
COLUNAS_MASTER_LIGA = [
    'INDEX', 'NAME', 'SHIRTNAME', 'JAPANESE PLAYER NAME', 'SPACING', 'COMMENTARY', 'AGE', 'NATIONALITY', 
    'FOOT', 'WEIGHT', 'HEIGHT', 'FORM', 'WEAK FOOT ACCURACY', 'WEAK FOOT FREQUENCY', 'INJURY TOLERANCE', 
    'GROWTH TYPE', 'MARKET PRICE', 'GK 0', 'SW 1', 'CB 2', 'LB 3', 'RB 4', 'DMF 5', 'CMF 6', 'LMF 7', 
    'RMF 8', 'AMF 9', 'LWF 10', 'RWF 11', 'SS 12', 'CF 13', 'POSITION', 'ATTACK', 'DEFENCE', 
    'HEADER ACCURACY', 'DRIBBLE ACCURACY', 'SHORT PASS ACCURACY', 'SHORT PASS SPEED', 'LONG PASS ACCURACY', 
    'LONG PASS SPEED', 'SHOT ACCURACY', 'PLACE KICKING', 'SWERVE', 'BALL CONTROLL', 'GOAL KEEPING SKILLS', 
    'RESPONSE', 'EXPLOSIVE POWER', 'DRIBBLE SPEED', 'TOP SPEED', 'BODY BALANCE', 'STAMINA', 'KICKING POWER', 
    'JUMP', 'TENACITY', 'TEAMWORK', 'S01 1-TOUCH PLAY', 'S02 OUTSIDE CURVE', 'S03 LONG THROW', 'S04 SUPER-SUB', 
    'S05 SPEED MERCHANT', 'S06 LONG RANGE DRIVE', 'S07 SHOULDER FEINT SKILLS', 'S08 TURNING SKILLS', 
    'S09 ROULETTE SKILLS', 'S10 FLIP FLAP SKILLS', 'S11 FLICKING SKILLS', 'S12 SCISSORS SKILLS', 
    'S13 STEP ON SKILLS', 'S14 DEFT TOUCH SKILLS', 'S15 KNUCKLE SHOT', 'S16 JUMPING VOLLEY', 
    'S17 SCISSOR KICK', 'S18 HEEL FLICK', 'S19 WEIGHTED PASS', 'S20 DOUBLE TOUCH', 'S21 RUN AROUND', 
    'S22 SOMBRERO', 'S23 180 DRAG', 'S24 LUNGING TACKLE', 'S25 DIVING HEADER', 'S26 GK LONG THROW', 
    'P01 CLASSIC NO.10', 'P02 ANCHOR MAN', 'P03 TRICKSTER', 'P04 DARTING RUN', 'P05 MAZING RUN', 
    'P06 PINPOINT PASS', 'P07 EARLY CROSS', 'P08 BOX TO BOX', 'P09 INCISIVE RUN', 'P10 LONG RANGER', 
    'P11 ENFORCER', 'P12 GOAL POACHER', 'P13 DUMMY RUNNER', 'P14 FREE ROAMING', 'P15 TALISMAN', 
    'P16 FOX IN THE BOX', 'P17 OFFENSIVE SIDEBACK', 'P18 TRACK BACK', 'ATTACK AWARENESS', 'DEFENCE AWARENESS', 
    'SKIN COLOR', 'SKIN TEXTURE', 'FACE MODE', 'LINKED FACE', 'FACE SLOT', 'LINKED HAIR', 'HAIR SLOT', 
    'BOOTS', 'UNTUCKED SHIRT', 'TIGHT KIT', 'GLOVES', 'DRIBBLE STYLE', 'FREE KICK STYLE', 'PENALTY KICK STYLE', 
    'DROP KICK STYLE', 'GOAL CELEBRATION STYLE #1', 'GOAL CELEBRATION STYLE #2', 'CLUB TEAM', 'NUMBER', 'NATIONAL TEAM'
]

st.set_page_config(page_title="PES 2013 Squad Builder", layout="wide")

@st.cache_data
def load_data():
    file = "jogadores.xlsx"
    try:
        tabs = ['GK', 'DF', 'MF', 'FW']
        data = {}
        for tab in tabs:
            df = pd.read_excel(file, sheet_name=tab)
            
            # --- PADRONIZAÇÃO DE COLUNAS ---
            # Remove espaços extras e converte tudo para MAIÚSCULO para bater com o padrão CSV
            df.columns = df.columns.str.strip().str.upper()
            
            # Garante que a primeira coluna seja o ID/INDEX
            coluna_id_real = df.columns[0]
            df.rename(columns={coluna_id_real: 'INDEX'}, inplace=True)
            
            # Correção de preço se necessário
            # Se não achar MARKET PRICE mas achar MARKET VALUE (M€), renomeia ou cria alias
            if 'MARKET VALUE (M€)' in df.columns:
                df['MARKET PRICE'] = df['MARKET VALUE (M€)']
            
            data[tab] = df
        return data
    except Exception as e:
        st.error(f"Erro ao carregar 'jogadores.xlsx': {e}")
        st.stop()

def get_p(r):
    if r is None: return 0.0
    # Procura em variações comuns de nome de coluna
    for col in ['MARKET PRICE', 'MARKET VALUE (M€)', 'MARKET VALUE']:
        if col in r:
            try: return float(r[col])
            except: continue
    return 0.0

def format_func(row):
    if row is None: return "Selecione..."
    idx = row.get('INDEX', '???')
    name = row.get('NAME', row.get('Name', 'Desconhecido'))
    ov = row.get('OVERALL', row.get('Overall', '??'))
    price = get_p(row)
    return f"ID: {idx} | {name} - OV: {ov} - €{price:.1f}"

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
    val_atual = get_p(st.session_state.escolhas.get(key_id))
    outros = [v.get('NAME', '') for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    # Filtros
    df_f = df_base[
        (df_base.apply(get_p, axis=1) <= (saldo + val_atual)) & 
        (df_base.apply(get_p, axis=1) <= filtro_p)
    ]
    
    df_f = df_f[~df_f['NAME'].isin(outros)]
    
    # Ordenação por Overall (agora em maiúsculo)
    col_ov = 'OVERALL' if 'OVERALL' in df_base.columns else df_base.columns[2] # Fallback
    ops = [None] + df_f.sort_values(col_ov, ascending=False).to_dict('records')
    
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
    for i in range(4): 
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
            pdf.ln(5); pdf.set_fill_color(240, 240, 240); pdf.cell(0, 8, " ELENCO", ln=True, fill=True)
            pdf.set_font("Arial", size=10)
            for p in elenco:
                n = str(p.get('NAME', 'Unknown')).encode('ascii', 'ignore').decode('ascii')
                idx = p.get('INDEX', '---')
                pdf.cell(25, 6, f"ID: {idx}", 0)
                pdf.cell(100, 6, f"{n} ({p['T']})", 0)
                pdf.cell(50, 6, f"OV: {p.get('OVERALL', '??')}", 0, 1, 'R')
            pdf_bytes = pdf.output(dest='S').encode('latin-1')

            # CSV (PADRÃO MASTER LIGA COM DADOS REAIS)
            df_export = pd.DataFrame(elenco)
            
            # Garante que as colunas do padrão PES existam no DataFrame final
            # O reindex vai pegar os dados que já existem (porque convertemos tudo para maiúsculo na carga)
            # e criar colunas vazias apenas para o que faltar
            df_export = df_export.reindex(columns=COLUNAS_MASTER_LIGA)
            
            csv_str = df_export.to_csv(sep=';', index=False, encoding='utf-8-sig')

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
            a2.add_header('Content-Disposition', f'attachment; filename="Master_Liga_{nome_time}.csv"'); msg.attach(a2)

            if escudo:
                a3 = MIMEBase('image', 'png')
                a3.set_payload(escudo.getvalue()); encoders.encode_base64(a3)
                a3.add_header('Content-Disposition', f'attachment; filename="escudo.png"'); msg.attach(a3)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP)
                s.send_message(msg)
            st.success("✅ Inscrição Enviada! Verifique os anexos.")
        except Exception as e:
            st.error(f"Erro técnico: {e}")
