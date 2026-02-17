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

# --- CSS PARA LAYOUT COMPACTO E THUMBNAILS (NÃO MEXER) ---
st.markdown("""
<style>
    /* Esconde botões de input numérico */
    [data-testid="stNumberInput"] button {display: none;}
    
    /* Layout mais denso */
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    
    /* Expander visualmente limpo */
    .streamlit-expanderHeader {background-color: #f0f2f6; border-radius: 5px;}
    
    /* FORÇA AS 7 COLUNAS A FICAREM JUNTAS */
    [data-testid="stHorizontalBlock"] {gap: 5px !important;}
    [data-testid="column"] {padding: 0 !important; min-width: 0 !important;}
    
    /* Botões de seleção de uniforme (Compactos) */
    .stButton button {
        width: 100% !important;
        border-radius: 4px;
        padding: 2px 0px !important;
        font-size: 0.8rem;
    }
    
    /* Imagens (Thumbnails) */
    [data-testid="stImage"] img {
        border-radius: 5px;
    }
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
def get_valid_images():
    validas = {}
    for nome, arquivo in OPCOES_CAMISAS.items():
        if os.path.exists(arquivo):
            validas[nome] = arquivo
    return validas

@st.cache_data(show_spinner=False)
def load_data_full():
    file_ui = "jogadores.xlsx"
    if not os.path.exists(file_ui):
        return None
    
    tabs = ['GK', 'DF', 'MF', 'FW']
    data_ui = {}
    cols_ui = ['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL'] 
    
    try:
        for tab in tabs:
            df = pd.read_excel(file_ui, sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            
            # Ajusta ID
            col_id = df.columns[0]
            df.rename(columns={col_id: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            
            # Limpeza Preço
            col_price = next((c for c in df.columns if any(x in c for x in ['PRICE', 'VALUE', 'VALUE (M€)'])), None)
            if col_price:
                df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else:
                df['MARKET PRICE'] = 0.0
                
            # Overall
            if 'OVERALL' not in df.columns and len(df.columns) > 2:
                df['OVERALL'] = df.iloc[:, 2]
            
            df.sort_values('OVERALL', ascending=False, inplace=True)
            data_ui[tab] = df[['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']].copy()
            
        return data_ui
    except:
        return None

# Load Inicial
data_ui = load_data_full()
valid_images = get_valid_images()

if data_ui is None:
    st.error("Erro: 'jogadores.xlsx' não encontrado.")
    st.stop()

# --- SESSÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'numeros' not in st.session_state: st.session_state.numeros = {}
if 'uni_titular_sel' not in st.session_state: st.session_state.uni_titular_sel = "Padrão 1"
if 'uni_reserva_sel' not in st.session_state: st.session_state.uni_reserva_sel = "Padrão 2"

custo_total = sum([p.get('MARKET PRICE', 0.0) for p in st.session_state.escolhas.values() if p])
saldo = ORCAMENTO_MAX - custo_total

# --- TÍTULO ---
st.title("⚽ SQUAD BUILDER PES 2013")

# --- CADASTRO E UNIFORMES ---
with st.expander("📋 Cadastro & Uniformes", expanded=True):
    c_int1, c_int2 = st.columns(2)
    int1 = c_int1.text_input("Jogador 1", key="input_int1")
    int2 = c_int2.text_input("Jogador 2", key="input_int2")
    
    c_team, c_mail = st.columns(2)
    nome_time = c_team.text_input("Nome do Time", "MEU TIME", key="input_team")
    email_user = c_mail.text_input("E-mail de Contato", key="input_email")
    
    escudo = st.file_uploader("Escudo (Logo)", type=['png','jpg'], key="input_logo")
    
    st.markdown("---")
    st.write("**:shirt: Personalizar Uniformes**")
    
    tab_titular, tab_reserva = st.tabs(["🏠 Titular", "✈️ Reserva"])
    
    def ui_uniforme(tipo_kit):
        state_key = f"uni_{tipo_kit.lower()}_sel" 
        
        st.caption(f"Selecione o Padrão ({tipo_kit}):")
        modelos = list(OPCOES_CAMISAS.keys())
        cols = st.columns(7) 
        
        for i, mod_nome in enumerate(modelos):
            arquivo = valid_images.get(mod_nome)
            with cols[i]:
                if arquivo:
                    st.image(arquivo, width=150)
                
                is_selected = (st.session_state[state_key] == mod_nome)
                if st.button("Usar", key=f"btn_{tipo_kit}_{i}"):
                    st.session_state[state_key] = mod_nome
                    st.rerun()
                if is_selected:
                    st.caption("✅ Selecionado")
        
        c1, c2, c3 = st.columns(3)
        cp = c1.color_picker("Camisa Base", "#FF0000", key=f"{tipo_kit}_cp")
        cs = c1.color_picker("Camisa Detalhe", "#FFFFFF", key=f"{tipo_kit}_cs")
        cc = c2.color_picker("Calção", "#FFFFFF", key=f"{tipo_kit}_cc")
        cm = c3.color_picker("Meias", "#FFFFFF", key=f"{tipo_kit}_cm")
            
        return {"modelo": st.session_state[state_key], "img": valid_images.get(st.session_state[state_key]), 
                "cores": [cp, cs, cc, cm]}

    with tab_titular: kit_titular = ui_uniforme("Titular")
    with tab_reserva: kit_reserva = ui_uniforme("Reserva")

st.markdown("---")

# --- PAINEL DE CONTROLE ---
c_fmt, c_filt, c_fin = st.columns([1, 1, 1.5])
with c_fmt:
    formacao = st.selectbox("Esquema Tático", ["4-3-3", "4-4-2", "3-5-2", "4-5-1", "3-4-3"], key="input_fmt")
with c_filt:
    filtro_p = st.number_input("Max € por Jogador", 0.0, 3000.0, 2000.0, key="input_filter")
with c_fin:
    c_fin.metric("Saldo Restante", f"€{saldo:.0f}")
    st.progress(min(custo_total / ORCAMENTO_MAX, 1.0))

st.markdown("---")

# --- SELEÇÃO DE JOGADORES ---
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

def seletor(label, df, key):
    escolha = st.session_state.escolhas.get(key)
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v and k != key]
    
    # Filtro
    mask = (df['MARKET PRICE'] <= (saldo + (escolha['MARKET PRICE'] if escolha else 0))) & (df['MARKET PRICE'] <= filtro_p)
    df_f = df[mask]
    if usados: df_f = df_f[~df_f['NAME'].isin(usados)]
        
    ops = [None] + df_f.to_dict('records')
    if escolha and escolha not in ops: ops.insert(1, escolha)
    
    c_sel, c_num = st.columns([4, 1]) 
    with c_sel:
        idx = ops.index(escolha) if escolha in ops else 0
        res = st.selectbox(label, ops, index=idx, format_func=lambda x: "Selecionar..." if x is None else f"{x['NAME']} (OV:{x['OVERALL']} | €{x['MARKET PRICE']:.1f})", key=f"s_{key}")
    with c_num:
        num = st.text_input("Nº", key=f"n_{key}", max_chars=2)
        
    if res != escolha:
        st.session_state.escolhas[key] = res
        st.rerun()
    return res

c1, c2 = st.columns(2)
lista_para_exportar = []

with c1:
    st.subheader("Titulares")
    g = seletor("🧤 Goleiro", data_ui['GK'], "gk_t")
    if g: lista_para_exportar.append({**g, "Tipo": "TITULAR", "Pos": "GK", "K": "gk_t"})
    for i in range(config["Z"]):
        p = seletor(f"🛡️ Zagueiro {i+1}", data_ui['DF'], f"z_{i}")
        if p: lista_para_exportar.append({**p, "Tipo": "TITULAR", "Pos": "CB", "K": f"z_{i}"})
    for i in range(config["L"]):
        p = seletor(f"🏃 Lateral {i+1}", pd.concat([data_ui['DF'], data_ui['MF']]), f"l_{i}")
        if p: lista_para_exportar.append({**p, "Tipo": "TITULAR", "Pos": "LAT", "K": f"l_{i}"})
    for i in range(config["M"]):
        p = seletor(f"🎯 Meio {i+1}", data_ui['MF'], f"m_{i}")
        if p: lista_para_exportar.append({**p, "Tipo": "TITULAR", "Pos": "MF", "K": f"m_{i}"})
    for i in range(config["A"]):
        p = seletor(f"🚀 Atacante {i+1}", data_ui['FW'], f"a_{i}")
        if p: lista_para_exportar.append({**p, "Tipo": "TITULAR", "Pos": "FW", "K": f"a_{i}"})

with c2:
    st.subheader("Reservas")
    gr = seletor("🧤 Goleiro Res.", data_ui['GK'], "gk_r")
    if gr: lista_para_exportar.append({**gr, "Tipo": "RESERVA", "Pos": "GK", "K": "gk_r"})
    todos_df = pd.concat([data_ui['DF'], data_ui['MF'], data_ui['FW']])
    for i in range(4):
        p = seletor(f"Reserva {i+1}", todos_df, f"res_{i}")
        if p: lista_para_exportar.append({**p, "Tipo": "RESERVA", "Pos": "RES", "K": f"res_{i}"})

st.divider()

# --- ENVIO FINAL (SEM CSV) ---
if st.button("✅ FINALIZAR E ENVIAR INSCRIÇÃO", type="primary", use_container_width=True):
    if len(lista_para_exportar) < 16 or not int1 or not int2:
        st.error("ERRO: O elenco deve ter 16 jogadores e os nomes dos técnicos devem estar preenchidos!")
    else:
        with st.spinner("Enviando inscrição para o servidor..."):
            try:
                # 1. GERAR TXT (ID + NOME + Nº)
                txt_content = f"TIME: {nome_time.upper()}\n"
                txt_content += f"TECNICOS: {int1} & {int2}\n"
                txt_content += f"FORMACAO: {formacao}\n"
                txt_content += "="*30 + "\n\n"
                
                for p in lista_para_exportar:
                    num_camisa = st.session_state.get(f"n_{p['K']}", "")
                    txt_content += f"ID: {p['INDEX']} | Nº: {num_camisa} | {p['NAME']}\n"

                # 2. GERAR PDF VISUAL
                pdf = FPDF()
                pdf.add_page()
                pdf.set_fill_color(30, 30, 30); pdf.rect(0, 0, 210, 45, 'F')
                
                if escudo:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                        tf.write(escudo.getvalue()); tname=tf.name
                    pdf.image(tname, x=10, y=5, w=30); os.unlink(tname)
                
                pdf.set_font("Arial", 'B', 22); pdf.set_text_color(255, 255, 255)
                pdf.set_xy(45, 10); pdf.cell(0, 10, nome_time.upper(), 0, 1)
                pdf.set_font("Arial", '', 10); pdf.set_xy(45, 20); pdf.cell(0, 10, f"Tecnicos: {int1} & {int2}")
                
                def draw_kit_pdf(kit, x_pos, label):
                    if kit['img'] and os.path.exists(kit['img']):
                        pdf.image(kit['img'], x=x_pos, y=5, w=20)
                    pdf.set_font("Arial", 'B', 7); pdf.set_xy(x_pos, 28); pdf.cell(20, 5, label, 0, 1, 'C')
                    bx = x_pos
                    for hex_c in kit['cores']:
                        r, g, b = hex_to_rgb(hex_c)
                        pdf.set_fill_color(r, g, b)
                        pdf.rect(bx, 35, 4, 4, 'F')
                        bx += 5

                draw_kit_pdf(kit_titular, 150, "TITULAR")
                draw_kit_pdf(kit_reserva, 180, "RESERVA")
                
                pdf.set_y(50); pdf.set_text_color(0,0,0); pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 10, "ELENCO SELECIONADO (PES 2013)", 0, 1, 'C')
                pdf.set_font("Arial", '', 9)
                
                for p in lista_para_exportar:
                    num = st.session_state.get(f"n_{p['K']}", "")
                    pdf.cell(0, 6, f"[{p['Tipo']}] {p['Pos']} - ID: {p['INDEX']} - {p['NAME']} (Camisa: {num})", 0, 1)

                # 3. ENVIAR E-MAIL
                msg = MIMEMultipart()
                msg['Subject'] = f"Inscrição PES 2013: {nome_time}"
                msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
                msg.attach(MIMEText(txt_content, 'plain'))
                
                # Anexo PDF
                att_pdf = MIMEBase('application', 'pdf')
                att_pdf.set_payload(pdf.output(dest='S').encode('latin-1'))
                encoders.encode_base64(att_pdf)
                att_pdf.add_header('Content-Disposition', 'attachment; filename="Elenco_Visual.pdf"')
                msg.attach(att_pdf)
                
                # Anexo TXT (Somente IDs e Nomes)
                att_txt = MIMEBase('text', 'plain')
                att_txt.set_payload(txt_content.encode('utf-8'))
                encoders.encode_base64(att_txt)
                att_txt.add_header('Content-Disposition', 'attachment; filename="IDs_Jogadores.txt"')
                msg.attach(att_txt)

                with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                    s.login(EMAIL_REMETENTE, SENHA_APP)
                    s.send_message(msg)
                
                st.success("✅ INSCRIÇÃO ENVIADA COM SUCESSO!")
                st.balloons()
            except Exception as e:
                st.error(f"Erro no envio: {e}")
