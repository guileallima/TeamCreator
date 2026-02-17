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
# ATENÇÃO: Para funcionar, você precisa gerar uma "Senha de App" na sua conta Google
# Não use a senha normal do seu e-mail.
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

# Gera lista de arquivos de uniforme
OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

# Colunas Master Liga
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

st.set_page_config(page_title="Squad Builder PES 2013", layout="wide")

# --- CSS OTIMIZADO ---
st.markdown("""
<style>
    [data-testid="stNumberInput"] button {display: none;}
    [data-testid="stNumberInput"] input {width: 100%;}
    [data-testid="stMetricValue"] {font-size: 1.1rem;}
    .streamlit-expanderHeader {background-color: #f0f2f6; border-radius: 5px;}
    div[data-baseweb="color-picker"] {width: 100%;}
    
    [data-testid="stHorizontalBlock"] {gap: 10px !important;}
    [data-testid="column"] {padding: 0 !important; min-width: 0 !important;}
    
    .streamlit-expanderContent .stButton button {
        width: 200px !important;
        border-radius: 5px;
        padding: 0px 5px;
        margin: 0 auto; 
        display: block;
    }
</style>
""", unsafe_allow_html=True)

# --- FUNÇÕES UTILITÁRIAS ---
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
    try:
        file_ui = "jogadores.xlsx"
        tabs = ['GK', 'DF', 'MF', 'FW']
        data_ui = {}
        for tab in tabs:
            df = pd.read_excel(file_ui, sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            col_id = df.columns[0]
            df.rename(columns={col_id: 'INDEX'}, inplace=True)
            df['INDEX'] = df['INDEX'].astype(str).str.strip()
            
            col_price = None
            for c in ['MARKET PRICE', 'MARKET VALUE (M€)', 'MARKET VALUE', 'VALUE', 'PRICE']:
                if c in df.columns: col_price = c; break
            if col_price: df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else: df['MARKET PRICE'] = 0.0
            data_ui[tab] = df

        file_raw = "jogadoresdata.xlsx"
        df_raw = pd.read_excel(file_raw)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        if 'INDEX' not in df_raw.columns:
            df_raw.rename(columns={df_raw.columns[0]: 'INDEX'}, inplace=True)
        df_raw['INDEX'] = df_raw['INDEX'].astype(str).str.strip()
            
        return data_ui, df_raw
    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}"); st.stop()

data_ui, data_raw = load_data()

# --- SESSÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'numeros' not in st.session_state: st.session_state.numeros = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

if 'uni_titular_sel' not in st.session_state: st.session_state.uni_titular_sel = "Padrão 1"
if 'uni_reserva_sel' not in st.session_state: st.session_state.uni_reserva_sel = "Padrão 2"

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.numeros = {}
    st.session_state.form_id += 1

# --- CÁLCULOS ---
custo_total = sum([p.get('MARKET PRICE', 0.0) for p in st.session_state.escolhas.values() if p])
saldo = ORCAMENTO_MAX - custo_total

# --- TÍTULO ---
st.title("⚽ SQUAD BUILDER")

# --- BLOCO DE CADASTRO ---
with st.expander("📋 Cadastro & Uniformes (Clique para Fechar/Abrir)", expanded=True):
    c_int1, c_int2 = st.columns(2)
    int1 = c_int1.text_input("Jogador 1", key="input_int1")
    int2 = c_int2.text_input("Jogador 2", key="input_int2")
    
    c_team, c_mail = st.columns(2)
    nome_time = c_team.text_input("Nome do Time", "MEU TIME", key="input_team")
    email_user = c_mail.text_input("E-mail", key="input_email")
    
    escudo = st.file_uploader("Upload do Escudo", type=['png','jpg'], key="input_logo")
    
    st.markdown("---")
    st.subheader("👕 Personalização dos Uniformes")
    
    tab_titular, tab_reserva = st.tabs(["🏠 Uniforme Titular", "✈️ Uniforme Reserva"])
    
    def ui_uniforme(tipo_kit):
        key_pfx = f"uni_{tipo_kit.lower()}"
        state_key = f"uni_{tipo_kit.lower()}_sel" 
        
        st.write(f"**Escolha o Padrão ({tipo_kit}):**")
        modelos = list(OPCOES_CAMISAS.keys())
        cols = st.columns(7) 
        
        for i, mod_nome in enumerate(modelos):
            arquivo = OPCOES_CAMISAS[mod_nome]
            with cols[i]:
                if os.path.exists(arquivo):
                    st.image(arquivo, width=200)
                else:
                    st.caption(f"Sem img")
                
                is_selected = (st.session_state[state_key] == mod_nome)
                if is_selected:
                    st.button("✅ Selecionado", key=f"btn_sel_{key_pfx}_{i}", disabled=True)
                else:
                    if st.button("Selecionar", key=f"btn_{key_pfx}_{i}"):
                        st.session_state[state_key] = mod_nome
                        st.rerun()
        
        st.write("---")
        st.write(f"**Cores ({tipo_kit})**")
        qtd_cores = st.radio(f"Nº Cores ({tipo_kit})", [2, 3], horizontal=True, key=f"{key_pfx}_qtd")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**:tshirt: Camisa**")
            cor_camisa_p = st.color_picker("Principal", "#FF0000", key=f"{key_pfx}_cp")
            cor_camisa_s = st.color_picker("Secundária", "#FFFFFF", key=f"{key_pfx}_cs")
            cor_camisa_e = None
            if qtd_cores == 3:
                cor_camisa_e = st.color_picker("Complementar", "#000000", key=f"{key_pfx}_ce")
                
        with c2:
            st.markdown("**:shorts: Calção**")
            cor_calcao = st.color_picker("Cor Base", "#FFFFFF", key=f"{key_pfx}_cc")
            
        with c3:
            st.markdown("**:socks: Meias**")
            cor_meia = st.color_picker("Cor Base", "#FFFFFF", key=f"{key_pfx}_cm")
            
        return {
            "modelo": st.session_state[state_key],
            "img": OPCOES_CAMISAS[st.session_state[state_key]],
            "qtd": qtd_cores,
            "camisa": [cor_camisa_p, cor_camisa_s, cor_camisa_e],
            "calcao": cor_calcao,
            "meia": cor_meia
        }

    with tab_titular:
        kit_titular = ui_uniforme("Titular")
    with tab_reserva:
        kit_reserva = ui_uniforme("Reserva")

st.markdown("---")

# --- PAINEL DE CONTROLE ---
c_fmt, c_filt, c_fin = st.columns([1, 1, 1.5])
with c_fmt:
    formacao = st.selectbox("Esquema Tático", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key="input_fmt")
with c_filt:
    filtro_p = st.number_input("Valor Limite por Jogador (€)", 0.0, 3000.0, 2000.0, 10.0, key="input_filter")
with c_fin:
    percentual_gasto = min(custo_total / ORCAMENTO_MAX, 1.0)
    m1, m2 = st.columns(2)
    m1.metric("Gasto Total", f"€{custo_total:.0f}")
    m2.metric("Saldo", f"€{saldo:.0f}")
    st.progress(percentual_gasto)

st.markdown("---")

# --- SELEÇÃO ---
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

def format_func(row):
    if row is None: return "Selecione..."
    return f"ID: {row.get('INDEX','?')} | {row.get('NAME','?')} - OV: {row.get('OVERALL','?')} - €{row.get('MARKET PRICE',0):.1f}"

def seletor(label, df, key):
    escolha = st.session_state.escolhas.get(key)
    val_atual = escolha.get('MARKET PRICE', 0.0) if escolha else 0.0
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v and k != key]
    mask = (df['MARKET PRICE'] <= (saldo + val_atual)) & (df['MARKET PRICE'] <= filtro_p) & (~df['NAME'].isin(usados))
    df_f = df[mask]
    col_ov = 'OVERALL' if 'OVERALL' in df.columns else df.columns[2]
    ops = [None] + df_f.sort_values(col_ov, ascending=False).to_dict('records')
    if escolha and escolha['NAME'] not in [o['NAME'] for o in ops if o]: ops.insert(1, escolha)
    idx = 0
    if escolha:
        for i, o in enumerate(ops): 
            if o and o['NAME'] == escolha['NAME']: idx = i; break
    
    c_sel, c_num = st.columns([4, 1.2]) 
    with c_sel:
        new_sel = st.selectbox(label, ops, index=idx, format_func=format_func, key=f"s_{key}_{st.session_state.form_id}")
    with c_num:
        val_n = st.session_state.numeros.get(key, "")
        new_n = st.text_input("Nº", value=val_n, max_chars=2, key=f"n_{key}_{st.session_state.form_id}")
        st.session_state.numeros[key] = new_n
    if new_sel != escolha:
        st.session_state.escolhas[key] = new_sel
        st.rerun()
    return new_sel

c1, c2 = st.columns([1, 1])
lista = []

with c1:
    st.subheader("Titulares")
    gk = seletor("🧤 Goleiro", data_ui['GK'], "gk_tit")
    if gk: lista.append({**gk, "T": "TITULAR", "P": "GK", "K": "gk_tit"})
    for i in range(config["Z"]):
        p = seletor(f"🛡️ Zagueiro {i+1}", data_ui['DF'], f"zag_{i}")
        if p: lista.append({**p, "T": "TITULAR", "P": "CB", "K": f"zag_{i}"})
    for i in range(config["L"]):
        p = seletor(f"🏃 Lateral {i+1}", pd.concat([data_ui['DF'],data_ui['MF']]), f"lat_{i}")
        if p: lista.append({**p, "T": "TITULAR", "P": "LB/RB", "K": f"lat_{i}"})
    for i in range(config["M"]):
        p = seletor(f"🎯 Meio Campo {i+1}", data_ui['MF'], f"mei_{i}")
        if p: lista.append({**p, "T": "TITULAR", "P": "MF", "K": f"mei_{i}"})
    for i in range(config["A"]):
        p = seletor(f"🚀 Atacante {i+1}", data_ui['FW'], f"ata_{i}")
        if p: lista.append({**p, "T": "TITULAR", "P": "CF/SS", "K": f"ata_{i}"})

with c2:
    st.subheader("Reservas (5)")
    gkr = seletor("🧤 Goleiro Res.", data_ui['GK'], "gk_res")
    if gkr: lista.append({**gkr, "T": "RESERVA", "P": "GK", "K": "gk_res"})
    df_all = pd.concat([data_ui['DF'], data_ui['MF'], data_ui['FW']])
    for i in range(4):
        p = seletor(f"Reserva {i+2}", df_all, f"res_{i}")
        if p: lista.append({**p, "T": "RESERVA", "P": "RES", "K": f"res_{i}"})

st.markdown("---")
if st.button("🔄 Limpar Escalação", use_container_width=True):
    reset_callback()
    st.rerun()
st.markdown("###")

# --- EXPORT ---
if st.button("✅ ENVIAR INSCRIÇÃO AGORA", type="primary", use_container_width=True):
    # VALIDAÇÃO CRÍTICA
    erros = []
    if not int1: erros.append("Falta o Jogador 1")
    if not int2: erros.append("Falta o Jogador 2")
    if not email_user: erros.append("Falta o E-mail")
    if len(lista) < 16: erros.append(f"Faltam {16 - len(lista)} jogadores")
    
    if erros:
        st.error(f"⚠️ ERRO DE PREENCHIMENTO: {', '.join(erros)}")
        st.stop()
    
    with st.spinner("⏳ Gerando arquivos e enviando e-mail... Aguarde!"):
        try:
            ids = [str(p['INDEX']).strip() for p in lista]
            df_exp = data_raw[data_raw['INDEX'].isin(ids)].reindex(columns=COLUNAS_MASTER_LIGA)
            csv_str = df_exp.to_csv(sep=';', index=False, encoding='utf-8-sig')
            
            pdf = FPDF()
            pdf.add_page()
            
            # Header (Reduzido)
            pdf.set_fill_color(20,20,20); pdf.rect(0,0,210,50,'F')
            if escudo:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                    tf.write(escudo.getvalue()); tname=tf.name
                pdf.image(tname, x=10, y=5, w=25); os.unlink(tname)
            
            pdf.set_font("Arial", 'B', 24); pdf.set_text_color(255,255,255)
            pdf.set_y(10); pdf.cell(0, 10, nome_time.upper(), 0, 1, 'C')
            
            pdf.set_font("Arial", '', 10)
            pdf.set_y(22)
            pdf.cell(0, 5, f"Jogadores: {int1} & {int2}", 0, 1, 'C')
            pdf.cell(0, 5, f"Formação: {formacao} | E-mail: {email_user}", 0, 1, 'C')
            
            def draw_kit_pdf(kit, x_pos, label):
                if kit['img'] and os.path.exists(kit['img']):
                    pdf.image(kit['img'], x=x_pos, y=5, w=25)
                
                pdf.set_xy(x_pos, 32)
                pdf.set_font("Arial", 'B', 7); pdf.set_text_color(255,255,255)
                pdf.cell(25, 3, label, 0, 1, 'C')
                pdf.cell(25, 3, kit['modelo'], 0, 1, 'C')
                
                cores_to_draw = [kit['camisa'][0], kit['camisa'][1]]
                if kit['qtd'] == 3 and kit['camisa'][2]:
                    cores_to_draw.append(kit['camisa'][2])
                cores_to_draw.append(kit['calcao'])
                cores_to_draw.append(kit['meia'])
                
                bx = x_pos + 1
                by = 40
                pdf.set_draw_color(255, 255, 255) 
                
                largura_total = len(cores_to_draw) * 4.5
                bx = x_pos + (25 - largura_total)/2
                
                for hex_c in cores_to_draw:
                    if hex_c:
                        r, g, b = hex_to_rgb(hex_c)
                        pdf.set_fill_color(r, g, b)
                        pdf.rect(bx, by, 4, 4, 'FD')
                        bx += 4.5

            draw_kit_pdf(kit_titular, 150, "TITULAR")
            draw_kit_pdf(kit_reserva, 180, "RESERVA")
                
            pdf.set_y(52) 
            pdf.set_text_color(0,0,0)
            
            def print_tabela(titulo, tipo_filtro):
                pdf.set_fill_color(220, 220, 220)
                pdf.set_font("Arial", 'B', 10) 
                pdf.cell(0, 6, f"  {titulo}", 0, 1, 'L', fill=True) 
                pdf.ln(1)
                pdf.set_font("Arial", '', 8) 
                
                soma = 0; qtd = 0
                for p in lista:
                    if p['T'] == tipo_filtro:
                        n = str(p.get('NAME','')).encode('latin-1','ignore').decode('latin-1')
                        raw_num = st.session_state.numeros.get(p['K'], "")
                        num = int(raw_num) if raw_num.isdigit() else ""
                        ov = p.get('OVERALL', 0)
                        try: soma += float(ov); qtd += 1
                        except: pass
                        
                        pdf.cell(20, 5, p['P'], 0, 0, 'C')
                        pdf.cell(15, 5, str(num), 0, 0, 'C')
                        pdf.cell(125, 5, n, 0, 0, 'L')
                        pdf.set_font("Arial", 'B', 8)
                        pdf.cell(30, 5, str(ov), 0, 1, 'C')
                        pdf.set_font("Arial", '', 8)
                        pdf.set_draw_color(220,220,220); pdf.line(10, pdf.get_y(), 200, pdf.get_y())
                        pdf.ln(5) 
                return soma, qtd

            s_tit, q_tit = print_tabela("ELENCO TITULAR", "TITULAR")
            pdf.ln(2) 
            print_tabela("BANCO DE RESERVAS", "RESERVA")
            
            pdf.ln(3)
            med = s_tit/q_tit if q_tit > 0 else 0
            pdf.set_fill_color(50,50,50); pdf.set_text_color(255,255,255)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, f"FORÇA DO TIME (Média Titular): {med:.1f}", 0, 1, 'C', fill=True)
            
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição: {nome_time}"
            msg.attach(MIMEText(f"Time: {nome_time}\nTitular: {kit_titular['modelo']}\nReserva: {kit_reserva['modelo']}", 'plain'))
            
            files = [('Escalacao.pdf', pdf.output(dest='S').encode('latin-1'), 'application/pdf'),
                    (f'Master_{nome_time}.csv', csv_str.encode('utf-8-sig'), 'text/csv')]
            if escudo: files.append(('Escudo.png', escudo.getvalue(), 'image/png'))
            
            for fname, fcontent, ftype in files:
                att = MIMEBase(*ftype.split('/'))
                att.set_payload(fcontent); encoders.encode_base64(att)
                att.add_header('Content-Disposition', f'attachment; filename="{fname}"')
                msg.attach(att)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP); s.send_message(msg)
                
            st.success("✅ Inscrição Enviada com Sucesso!")

        except smtplib.SMTPAuthenticationError:
            st.error("❌ Erro de Login no E-mail! Verifique se a SENHA DE APP está correta no código.")
        except Exception as e:
            st.error(f"❌ Erro ao enviar: {e}")
