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

# --- CONFIGURAÇÕES GERAIS ---
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

st.set_page_config(page_title="Squad Builder PES 2013", layout="wide")

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

# --- FUNÇÕES DE LIMPEZA E CARREGAMENTO ---
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
def get_valid_images():
    validas = {}
    for nome, arquivo in OPCOES_CAMISAS.items():
        if os.path.exists(arquivo): validas[nome] = arquivo
    return validas

@st.cache_data(show_spinner=False)
def load_data_full():
    file_ui = "jogadores.xlsx"
    if not os.path.exists(file_ui): return None
    tabs = ['GK', 'DF', 'MF', 'FW']
    data_ui = {}
    try:
        for tab in tabs:
            df = pd.read_excel(file_ui, sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            col_id = df.columns[0]
            df.rename(columns={col_id: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            
            col_price = next((c for c in df.columns if any(x in c for x in ['PRICE', 'VALUE', 'VALUE (M€)'])), None)
            if col_price:
                df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else:
                df['MARKET PRICE'] = 0.0
                
            if 'OVERALL' not in df.columns and len(df.columns) > 2:
                df['OVERALL'] = df.iloc[:, 2]
            
            df.sort_values('OVERALL', ascending=False, inplace=True)
            data_ui[tab] = df[['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']].copy()
        return data_ui
    except: return None

# Inicialização
data_ui = load_data_full()
valid_images = get_valid_images()

if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'numeros' not in st.session_state: st.session_state.numeros = {}
if 'uni_titular_sel' not in st.session_state: st.session_state.uni_titular_sel = "Padrão 1"
if 'uni_reserva_sel' not in st.session_state: st.session_state.uni_reserva_sel = "Padrão 2"

custo_total = sum([p.get('MARKET PRICE', 0.0) for p in st.session_state.escolhas.values() if p])
saldo = ORCAMENTO_MAX - custo_total

# --- UI PRINCIPAL ---
st.title("⚽ SQUAD BUILDER PES 2013")

with st.expander("📋 Cadastro & Uniformes", expanded=True):
    c_int1, c_int2 = st.columns(2)
    int1 = c_int1.text_input("Jogador 1", key="input_int1")
    int2 = c_int2.text_input("Jogador 2", key="input_int2")
    
    c_team, c_mail = st.columns(2)
    nome_time = c_team.text_input("Nome do Time", "MEU TIME")
    email_user = c_mail.text_input("E-mail de Contato")
    escudo = st.file_uploader("Escudo", type=['png','jpg'])
    
    st.markdown("---")
    tab_titular, tab_reserva = st.tabs(["🏠 Titular", "✈️ Reserva"])
    
    def ui_uniforme(tipo_kit):
        state_key = f"uni_{tipo_kit.lower()}_sel" 
        cols = st.columns(7)
        modelos = list(OPCOES_CAMISAS.keys())
        for i, mod_nome in enumerate(modelos):
            arquivo = valid_images.get(mod_nome)
            with cols[i]:
                if arquivo: st.image(arquivo, width=150)
                if st.button("Usar", key=f"btn_{tipo_kit}_{i}"):
                    st.session_state[state_key] = mod_nome
                    st.rerun()
                if st.session_state[state_key] == mod_nome: st.caption("✅")

        c1, c2, c3 = st.columns(3)
        cp = c1.color_picker("Camisa Principal", "#FF0000", key=f"{tipo_kit}_cp")
        cs = c1.color_picker("Camisa Secundária", "#FFFFFF", key=f"{tipo_kit}_cs")
        cc = c2.color_picker("Calção", "#FFFFFF", key=f"{tipo_kit}_cc")
        cm = c3.color_picker("Meias", "#FFFFFF", key=f"{tipo_kit}_cm")
        return {"modelo": st.session_state[state_key], "img": valid_images.get(st.session_state[state_key]), "cores": [cp, cs, cc, cm]}

    with tab_titular: kit_titular = ui_uniforme("Titular")
    with tab_reserva: kit_reserva = ui_uniforme("Reserva")

# --- PAINEL DE CONTROLE ---
c_fmt, c_filt, c_stats = st.columns([1, 1, 1.5])
formacao = c_fmt.selectbox("Esquema", ["4-3-3", "4-4-2", "3-5-2", "4-5-1", "3-4-3"])
filtro_p = c_filt.number_input("Max €/Jogador", 0.0, 3000.0, 2000.0)
c_stats.metric("Saldo", f"€{saldo:.0f}")
c_stats.progress(min(custo_total / ORCAMENTO_MAX, 1.0))

# --- SELEÇÃO DE JOGADORES ---
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

def seletor(label, df, key):
    escolha = st.session_state.escolhas.get(key)
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v and k != key]
    mask = (df['MARKET PRICE'] <= (saldo + (escolha['MARKET PRICE'] if escolha else 0))) & (df['MARKET PRICE'] <= filtro_p)
    df_f = df[mask]
    if usados: df_f = df_f[~df_f['NAME'].isin(usados)]
    ops = [None] + df_f.to_dict('records')
    if escolha and escolha not in ops: ops.insert(1, escolha)
    
    c_sel, c_num = st.columns([4, 1])
    res = c_sel.selectbox(label, ops, format_func=lambda x: "Selecione..." if x is None else f"{x['NAME']} (OV:{x['OVERALL']} | €{x['MARKET PRICE']:.1f})", key=f"s_{key}")
    num = c_num.text_input("Nº", key=f"n_{key}", max_chars=2)
    if res != escolha:
        st.session_state.escolhas[key] = res
        st.rerun()
    return res

col_elenco_1, col_elenco_2 = st.columns(2)
lista_final = []

with col_elenco_1:
    st.subheader("Titulares")
    g = seletor("🧤 Goleiro", data_ui['GK'], "gk")
    if g: lista_final.append({**g, "Pos": "GK", "Tipo": "TITULAR", "Key": "gk"})
    for i in range(config["Z"]):
        p = seletor(f"🛡️ Zagueiro {i+1}", data_ui['DF'], f"z_{i}")
        if p: lista_final.append({**p, "Pos": "CB", "Tipo": "TITULAR", "Key": f"z_{i}"})
    for i in range(config["L"]):
        p = seletor(f"🏃 Lateral {i+1}", pd.concat([data_ui['DF'], data_ui['MF']]), f"l_{i}")
        if p: lista_final.append({**p, "Pos": "LB/RB", "Tipo": "TITULAR", "Key": f"l_{i}"})
    for i in range(config["M"]):
        p = seletor(f"🎯 Meio {i+1}", data_ui['MF'], f"m_{i}")
        if p: lista_final.append({**p, "Pos": "MF", "Tipo": "TITULAR", "Key": f"m_{i}"})
    for i in range(config["A"]):
        p = seletor(f"🚀 Atacante {i+1}", data_ui['FW'], f"a_{i}")
        if p: lista_final.append({**p, "Pos": "FW", "Tipo": "TITULAR", "Key": f"a_{i}"})

with col_elenco_2:
    st.subheader("Reservas")
    gr = seletor("🧤 Goleiro Res.", data_ui['GK'], "gr")
    if gr: lista_final.append({**gr, "Pos": "GK", "Tipo": "RESERVA", "Key": "gr"})
    todos = pd.concat([data_ui['DF'], data_ui['MF'], data_ui['FW']])
    for i in range(4):
        p = seletor(f"Reserva {i+1}", todos, f"r_{i}")
        if p: lista_final.append({**p, "Pos": "RES", "Tipo": "RESERVA", "Key": f"r_{i}"})

# --- ENVIO ---
if st.button("✅ ENVIAR INSCRIÇÃO", type="primary", use_container_width=True):
    if len(lista_final) < 16 or not int1 or not int2:
        st.error("Complete o time (16 jogadores) e preencha os nomes!")
    else:
        with st.spinner("Enviando..."):
            try:
                # 1. GERAR TXT (ID + NOME + Nº)
                txt_content = f"TIME: {nome_time}\nTECNICOS: {int1} & {int2}\n\n"
                for p in lista_final:
                    num = st.session_state.get(f"n_{p['Key']}", "")
                    txt_content += f"ID: {p['INDEX']} | Nº: {num} | {p['NAME']}\n"

                # 2. GERAR PDF VISUAL
                pdf = FPDF()
                pdf.add_page()
                pdf.set_fill_color(30, 30, 30); pdf.rect(0, 0, 210, 45, 'F')
                pdf.set_font("Arial", 'B', 20); pdf.set_text_color(255, 255, 255)
                pdf.text(60, 20, nome_time.upper())
                pdf.set_font("Arial", '', 10); pdf.text(60, 30, f"Tecnicos: {int1} & {int2}")
                
                # Cores no PDF
                def draw_kit_pdf(kit, x, label):
                    if kit['img'] and os.path.exists(kit['img']): pdf.image(kit['img'], x=x, y=5, w=20)
                    pdf.set_font("Arial", 'B', 7); pdf.text(x+2, 32, label)
                    bx = x
                    for c in kit['cores']:
                        r,g,b = hex_to_rgb(c)
                        pdf.set_fill_color(r,g,b); pdf.rect(bx, 35, 4, 4, 'F')
                        bx += 5
                
                draw_kit_pdf(kit_titular, 150, "TITULAR")
                draw_kit_pdf(kit_reserva, 180, "RESERVA")
                
                pdf.set_y(50); pdf.set_text_color(0,0,0); pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "ELENCO SELECIONADO", 0, 1, 'C')
                pdf.set_font("Arial", '', 9)
                for p in lista_final:
                    num = st.session_state.get(f"n_{p['Key']}", "")
                    pdf.cell(0, 6, f"{p['Tipo']} - {p['Pos']} - ID: {p['INDEX']} - {p['NAME']} (Nº {num})", 0, 1)

                # 3. EMAIL
                msg = MIMEMultipart()
                msg['Subject'] = f"Inscrição: {nome_time}"
                msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
                msg.attach(MIMEText(txt_content, 'plain'))
                
                # Anexos (PDF e TXT apenas)
                att_pdf = MIMEBase('application', 'pdf')
                att_pdf.set_payload(pdf.output(dest='S').encode('latin-1'))
                encoders.encode_base64(att_pdf)
                att_pdf.add_header('Content-Disposition', 'attachment; filename="Elenco.pdf"')
                msg.attach(att_pdf)
                
                att_txt = MIMEBase('text', 'plain')
                att_txt.set_payload(txt_content.encode('utf-8'))
                encoders.encode_base64(att_txt)
                att_txt.add_header('Content-Disposition', 'attachment; filename="IDs_Time.txt"')
                msg.attach(att_txt)
                
                if escudo:
                    att_img = MIMEBase('image', 'png')
                    att_img.set_payload(escudo.getvalue())
                    encoders.encode_base64(att_img)
                    att_img.add_header('Content-Disposition', 'attachment; filename="Escudo.png"')
                    msg.attach(att_img)

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP); s.send_message(msg)
                
                st.success("✅ INSCRIÇÃO ENVIADA!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro: {e}")
