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

# --- CONFIGURAÇÕES ---
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

# Colunas Obrigatórias do PES 2013 (Master Liga)
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

def clean_price(val):
    if pd.isna(val) or val == '': return 0.0
    s_val = str(val)
    s_val = re.sub(r'[^\d.,]', '', s_val)
    if not s_val: return 0.0
    s_val = s_val.replace(',', '.')
    try: return float(s_val)
    except: return 0.0

@st.cache_data
def load_data():
    try:
        # 1. VISUAL (Site)
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
                if c in df.columns:
                    col_price = c
                    break
            if col_price:
                df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else:
                df['MARKET PRICE'] = 0.0
            
            data_ui[tab] = df

        # 2. DADOS (Jogo)
        file_raw = "jogadoresdata.xlsx"
        df_raw = pd.read_excel(file_raw)
        df_raw.columns = df_raw.columns.str.strip().str.upper()
        if 'INDEX' not in df_raw.columns:
            df_raw.rename(columns={df_raw.columns[0]: 'INDEX'}, inplace=True)
        df_raw['INDEX'] = df_raw['INDEX'].astype(str).str.strip()
            
        return data_ui, df_raw

    except Exception as e:
        st.error(f"Erro ao carregar arquivos: {e}")
        st.stop()

data_ui, data_raw = load_data()

# --- SESSÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
# 'form_id' será usado APENAS para os seletores de jogadores
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    # Limpa apenas as escolhas dos jogadores
    st.session_state.escolhas = {}
    # Incrementa o ID para forçar APENAS os selectbox a recarregarem
    st.session_state.form_id += 1

# --- CÁLCULO ---
custo_total = 0.0
for k, player in st.session_state.escolhas.items():
    if player: custo_total += player.get('MARKET PRICE', 0.0)
saldo = ORCAMENTO_MAX - custo_total

# --- UI ---
with st.sidebar:
    st.header("📋 Cadastro")
    # AQUI MUDOU: Usamos chaves FIXAS (strings estáticas) para que não resetem
    int1 = st.text_input("Integrante 1", key="input_int1")
    int2 = st.text_input("Integrante 2", key="input_int2")
    email_user = st.text_input("E-mail", key="input_email")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key="input_team")
    escudo = st.file_uploader("Escudo", type=['png','jpg'], key="input_logo")
    
    st.markdown("---")
    st.metric("Gasto", f"€{custo_total:.1f}")
    st.metric("Saldo", f"€{saldo:.1f}", delta=f"{saldo:.1f}")
    
    st.markdown("---")
    # Filtro e Formação também com chaves fixas
    filtro_p = st.number_input("Preço Máximo (€)", min_value=0.0, max_value=3000.0, value=2000.0, step=10.0, key="input_filter")
    
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key="input_formation")

# --- SELETOR ---
def format_func(row):
    if row is None: return "Selecione..."
    idx = row.get('INDEX', '---')
    name = row.get('NAME', 'Desconhecido')
    ov = row.get('OVERALL', row.get('Overall', '??'))
    price = row.get('MARKET PRICE', 0.0)
    return f"ID: {idx} | {name} - OV: {ov} - €{price:.1f}"

def seletor(label, df, key):
    escolha_atual = st.session_state.escolhas.get(key)
    valor_atual = escolha_atual.get('MARKET PRICE', 0.0) if escolha_atual else 0.0
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v is not None and k != key]
    
    mask = (df['MARKET PRICE'] <= (saldo + valor_atual)) & (df['MARKET PRICE'] <= filtro_p) & (~df['NAME'].isin(usados))
    df_filtrado = df[mask]
    
    col_ov = 'OVERALL' if 'OVERALL' in df.columns else df.columns[2]
    opcoes = [None] + df_filtrado.sort_values(col_ov, ascending=False).to_dict('records')
    
    if escolha_atual and escolha_atual['NAME'] not in [o['NAME'] for o in opcoes if o]:
        opcoes.insert(1, escolha_atual)
    
    idx_sel = 0
    if escolha_atual:
        for i, opt in enumerate(opcoes):
            if opt and opt['NAME'] == escolha_atual['NAME']: idx_sel = i; break
            
    # AQUI MUDOU: A chave usa 'form_id', então só esse componente reseta
    nova_escolha = st.selectbox(label, opcoes, index=idx_sel, format_func=format_func, key=f"sel_{key}_{st.session_state.form_id}")
    
    if nova_escolha != escolha_atual:
        st.session_state.escolhas[key] = nova_escolha
        st.rerun()
    return nova_escolha

# --- MONTAGEM ---
st.title(f"⚽ {nome_time.upper()}")
config = {"4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3}, "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3}, "3-5-2": {"Z":3,"L":2,"M":3,"A":2}}[formacao]

c1, c2 = st.columns([2, 1])
lista_visual = [] 

with c1:
    st.subheader("Titulares")
    gk = seletor("🧤 Goleiro", data_ui['GK'], "gk_tit")
    if gk: lista_visual.append({**gk, "TIPO": "TITULAR", "POS_DISPLAY": "GK"})
    for i in range(config["Z"]):
        z = seletor(f"🛡️ Zagueiro {i+1}", data_ui['DF'], f"zag_{i}")
        if z: lista_visual.append({**z, "TIPO": "TITULAR", "POS_DISPLAY": "CB"})
    for i in range(config["L"]):
        l = seletor(f"🏃 Lateral {i+1}", pd.concat([data_ui['DF'], data_ui['MF']]), f"lat_{i}")
        if l: lista_visual.append({**l, "TIPO": "TITULAR", "POS_DISPLAY": "LB/RB"})
    for i in range(config["M"]):
        m = seletor(f"🎯 Meio Campo {i+1}", data_ui['MF'], f"mei_{i}")
        if m: lista_visual.append({**m, "TIPO": "TITULAR", "POS_DISPLAY": "MF"})
    for i in range(config["A"]):
        a = seletor(f"🚀 Atacante {i+1}", data_ui['FW'], f"ata_{i}")
        if a: lista_visual.append({**a, "TIPO": "TITULAR", "POS_DISPLAY": "CF/SS"})

with c2:
    st.subheader("Reservas (5)")
    gkr = seletor("🧤 Goleiro Reserva", data_ui['GK'], "gk_res")
    if gkr: lista_visual.append({**gkr, "TIPO": "RESERVA", "POS_DISPLAY": "GK"})
    df_all = pd.concat([data_ui['DF'], data_ui['MF'], data_ui['FW']])
    for i in range(4):
        r = seletor(f"Reserva {i+2}", df_all, f"res_{i}")
        if r: lista_visual.append({**r, "TIPO": "RESERVA", "POS_DISPLAY": "RES"})

# Botão de Reset
if st.button("🔄 Resetar Apenas o Time", on_click=reset_callback): pass

# --- EXPORTAÇÃO ---
if st.sidebar.button("✅ ENVIAR INSCRIÇÃO"):
    if not int1 or not int2 or not email_user: st.sidebar.error("Dados incompletos."); st.stop()
    if len(lista_visual) < 16: st.sidebar.warning("Selecione os 16 jogadores."); st.stop()
    
    try:
        # 1. Recupera IDs
        ids_selecionados = [str(p['INDEX']).strip() for p in lista_visual]
        
        # 2. Gera CSV (Match com arquivo Raw)
        df_export_raw = data_raw[data_raw['INDEX'].isin(ids_selecionados)].copy()
        df_export_final = df_export_raw.reindex(columns=COLUNAS_MASTER_LIGA)
        csv_str = df_export_final.to_csv(sep=';', index=False, encoding='utf-8-sig')
        
        # 3. Gera PDF VISUAL LIMPO
        pdf = FPDF()
        pdf.add_page()
        
        # Cabeçalho Escuro
        pdf.set_fill_color(20,20,20); pdf.rect(0,0,210,40,'F')
        
        # Escudo
        if escudo:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                tf.write(escudo.getvalue()); tname=tf.name
            pdf.image(tname, x=10, y=5, w=25); os.unlink(tname)
        
        # Nome do Time
        pdf.set_font("Arial", 'B', 24); pdf.set_text_color(255,255,255)
        pdf.set_y(15); pdf.cell(0, 10, nome_time.upper(), 0, 1, 'C')
        
        # Dados da Dupla
        pdf.set_text_color(0,0,0); pdf.ln(20)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 6, f"Treinadores: {int1} & {int2}", 0, 1, 'C')
        pdf.cell(0, 6, f"Formação: {formacao}", 0, 1, 'C')
        pdf.ln(5)
        
        # --- TABELA DE TITULARES ---
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "  ELENCO TITULAR", 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", '', 11)
        
        soma_ov_titular = 0
        qtd_titular = 0
        
        # Lista Titulares
        for p in lista_visual:
            if p['TIPO'] == 'TITULAR':
                nome = str(p.get('NAME','')).encode('latin-1','ignore').decode('latin-1')
                pos = p.get('POS_DISPLAY', '-')
                ov = p.get('OVERALL', 0)
                
                try: 
                    ov_val = float(ov)
                    soma_ov_titular += ov_val
                    qtd_titular += 1
                except: pass

                pdf.cell(30, 8, pos, 0, 0, 'C')
                pdf.cell(130, 8, nome, 0, 0, 'L')
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(30, 8, str(ov), 0, 1, 'C')
                pdf.set_font("Arial", '', 11)
                
                pdf.set_draw_color(200,200,200)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())

        # --- TABELA DE RESERVAS ---
        pdf.ln(5)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 10, "  BANCO DE RESERVAS", 0, 1, 'L', fill=True)
        pdf.ln(2)
        
        pdf.set_font("Arial", '', 11)
        for p in lista_visual:
            if p['TIPO'] == 'RESERVA':
                nome = str(p.get('NAME','')).encode('latin-1','ignore').decode('latin-1')
                pos = p.get('POS_DISPLAY', '-')
                ov = p.get('OVERALL', 0)
                
                pdf.cell(30, 8, pos, 0, 0, 'C')
                pdf.cell(130, 8, nome, 0, 0, 'L')
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(30, 8, str(ov), 0, 1, 'C')
                pdf.set_font("Arial", '', 11)
                pdf.set_draw_color(200,200,200)
                pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        
        # --- RODAPÉ COM MÉDIA ---
        pdf.ln(10)
        media = soma_ov_titular / qtd_titular if qtd_titular > 0 else 0
        
        pdf.set_fill_color(50, 50, 50)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 12, f"FORÇA DO TIME (Média Titular): {media:.1f}", 0, 1, 'C', fill=True)
        
        pdf_bytes = pdf.output(dest='S').encode('latin-1')

        # EMAIL
        msg = MIMEMultipart()
        msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
        msg['Subject'] = f"Escalação Oficial: {nome_time}"
        msg.attach(MIMEText(f"Time: {nome_time}\nDupla: {int1}/{int2}\n\nConfira a escalação oficial no PDF anexo.", 'plain'))
        
        att1 = MIMEBase('application', 'pdf')
        att1.set_payload(pdf_bytes); encoders.encode_base64(att1)
        att1.add_header('Content-Disposition', 'attachment; filename="Escalacao.pdf"'); msg.attach(att1)
        
        att2 = MIMEBase('text', 'csv')
        att2.set_payload(csv_str.encode('utf-8-sig')); encoders.encode_base64(att2)
        att2.add_header('Content-Disposition', f'attachment; filename="Master_{nome_time}.csv"'); msg.attach(att2)
        
        if escudo:
            att3 = MIMEBase('image', 'png')
            att3.set_payload(escudo.getvalue()); encoders.encode_base64(att3)
            att3.add_header('Content-Disposition', 'attachment; filename="Escudo.png"'); msg.attach(att3)
            
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(EMAIL_REMETENTE, SENHA_APP)
            s.send_message(msg)
            
        st.success("✅ Inscrição Enviada com Sucesso! (PDF Limpo + CSV Master Liga)")
        
    except Exception as e:
        st.error(f"Erro no processamento: {e}")
