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

# Colunas oficiais para exportação (Master Liga)
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

# --- FUNÇÃO DE LIMPEZA DE PREÇO ---
def clean_price(val):
    """Converte qualquer formato de preço (string com €, virgula, etc) para float."""
    if pd.isna(val) or val == '': return 0.0
    s_val = str(val)
    # Remove tudo que não for numero, ponto ou virgula
    s_val = re.sub(r'[^\d.,]', '', s_val)
    if not s_val: return 0.0
    # Troca virgula por ponto se existir
    s_val = s_val.replace(',', '.')
    try:
        return float(s_val)
    except:
        return 0.0

@st.cache_data
def load_data():
    file = "jogadores.xlsx"
    try:
        tabs = ['GK', 'DF', 'MF', 'FW']
        data = {}
        for tab in tabs:
            df = pd.read_excel(file, sheet_name=tab)
            # Padroniza colunas para Maiúsculas e sem espaços
            df.columns = df.columns.str.strip().str.upper()
            
            # 1. Garante coluna INDEX (Pega a primeira coluna do Excel)
            col_id = df.columns[0]
            df.rename(columns={col_id: 'INDEX'}, inplace=True)
            
            # 2. Identifica e Padroniza a coluna de PREÇO
            col_price = None
            for c in ['MARKET PRICE', 'MARKET VALUE (M€)', 'MARKET VALUE', 'VALUE', 'PRICE']:
                if c in df.columns:
                    col_price = c
                    break
            
            # Se achou a coluna, limpa e padroniza para 'MARKET PRICE'
            if col_price:
                df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else:
                # Se não achou, cria zerada para não quebrar
                df['MARKET PRICE'] = 0.0
                
            data[tab] = df
        return data
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.stop()

data = load_data()

# --- SESSÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.form_id += 1

# --- CÁLCULO DE ORÇAMENTO (Sempre atualizado) ---
# Soma os preços dos jogadores selecionados
custo_total = 0.0
for k, player in st.session_state.escolhas.items():
    if player:
        custo_total += player.get('MARKET PRICE', 0.0)

saldo = ORCAMENTO_MAX - custo_total

# --- INTERFACE ---
with st.sidebar:
    st.header("📋 Cadastro")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    email_user = st.text_input("E-mail", key=f"em_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"tm_{st.session_state.form_id}")
    escudo = st.file_uploader("Escudo", type=['png','jpg'], key=f"logo_{st.session_state.form_id}")
    
    st.markdown("---")
    st.subheader("💰 Finanças")
    # Exibe métricas grandes e claras
    col_met1, col_met2 = st.columns(2)
    col_met1.metric("Gasto", f"€{custo_total:.1f}")
    col_met2.metric("Saldo", f"€{saldo:.1f}", delta=f"{saldo:.1f}")
    
    st.markdown("---")
    filtro_p = st.slider("Filtro de Preço Máx.", 0.0, 1500.0, 1500.0, key=f"flt_{st.session_state.form_id}")
    formacao = st.selectbox("Formação", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"fmt_{st.session_state.form_id}")

# --- SELETOR OTIMIZADO ---
def format_func(row):
    if row is None: return "Selecione..."
    idx = row.get('INDEX', '---')
    name = row.get('NAME', 'Desconhecido')
    ov = row.get('OVERALL', row.get('Overall', '??'))
    price = row.get('MARKET PRICE', 0.0)
    return f"ID: {idx} | {name} - OV: {ov} - €{price:.1f}"

def seletor(label, df, key):
    # Recupera escolha atual
    escolha_atual = st.session_state.escolhas.get(key)
    valor_atual = escolha_atual.get('MARKET PRICE', 0.0) if escolha_atual else 0.0
    
    # Define nomes já usados em OUTROS campos (para evitar duplicata)
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v is not None and k != key]
    
    # Filtra DataFrame
    # 1. Jogador deve caber no (Saldo Restante + Valor que ele mesmo ocupa atualmente)
    # 2. Jogador deve custar menos que o filtro da barra lateral
    mask_orcamento = df['MARKET PRICE'] <= (saldo + valor_atual)
    mask_filtro = df['MARKET PRICE'] <= filtro_p
    mask_duplicata = ~df['NAME'].isin(usados)
    
    df_filtrado = df[mask_orcamento & mask_filtro & mask_duplicata]
    
    # Ordena por Overall
    col_ov = 'OVERALL' if 'OVERALL' in df.columns else df.columns[2]
    opcoes = [None] + df_filtrado.sort_values(col_ov, ascending=False).to_dict('records')
    
    # Garante que, se já houver um jogador selecionado, ele apareça na lista mesmo se fugir do filtro (para não sumir visualmente)
    if escolha_atual and escolha_atual['NAME'] not in [o['NAME'] for o in opcoes if o]:
        opcoes.insert(1, escolha_atual)
    
    # Encontra o índice atual para manter a seleção visual
    idx_sel = 0
    if escolha_atual:
        for i, opt in enumerate(opcoes):
            if opt and opt['NAME'] == escolha_atual['NAME']:
                idx_sel = i
                break
    
    # Widget
    nova_escolha = st.selectbox(label, opcoes, index=idx_sel, format_func=format_func, key=f"sel_{key}_{st.session_state.form_id}")
    
    # Atualiza Session State se mudou
    if nova_escolha != escolha_atual:
        st.session_state.escolhas[key] = nova_escolha
        st.rerun()
        
    return nova_escolha

# --- MONTAGEM DO TIME ---
st.title(f"⚽ {nome_time.upper()}")

config = {
    "4-5-1": {"Z":2, "L":2, "M":5, "A":1},
    "3-4-3": {"Z":3, "L":2, "M":2, "A":3},
    "4-4-2": {"Z":2, "L":2, "M":4, "A":2},
    "4-3-3": {"Z":2, "L":2, "M":3, "A":3},
    "3-5-2": {"Z":3, "L":2, "M":3, "A":2},
}[formacao]

c1, c2 = st.columns([2, 1])
lista_final = []

with c1:
    st.subheader("Titulares")
    gk = seletor("🧤 Goleiro", data['GK'], "gk_tit")
    if gk: lista_final.append({**gk, "TIPO": "TITULAR"})
    
    for i in range(config["Z"]):
        z = seletor(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if z: lista_final.append({**z, "TIPO": "TITULAR"})
        
    for i in range(config["L"]):
        l = seletor(f"🏃 Lateral {i+1}", pd.concat([data['DF'], data['MF']]), f"lat_{i}")
        if l: lista_final.append({**l, "TIPO": "TITULAR"})
        
    for i in range(config["M"]):
        m = seletor(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if m: lista_final.append({**m, "TIPO": "TITULAR"})
        
    for i in range(config["A"]):
        a = seletor(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if a: lista_final.append({**a, "TIPO": "TITULAR"})

with c2:
    st.subheader("Reservas (5)")
    gkr = seletor("🧤 Goleiro Reserva", data['GK'], "gk_res")
    if gkr: lista_final.append({**gkr, "TIPO": "RESERVA"})
    
    # Reservas de linha (4)
    df_all = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(4):
        r = seletor(f"Reserva {i+2}", df_all, f"res_{i}")
        if r: lista_final.append({**r, "TIPO": "RESERVA"})

if st.button("🔄 Resetar Tudo", on_click=reset_callback): pass

# --- FINALIZAR ---
if st.sidebar.button("✅ ENVIAR INSCRIÇÃO"):
    # Validação
    erros = []
    if not int1 or not int2: erros.append("Preencha os nomes da dupla.")
    if not email_user: erros.append("Preencha o e-mail.")
    if len(lista_final) < 16: erros.append(f"Complete o time! Faltam {16 - len(lista_final)} jogadores.")
    
    if erros:
        for e in erros: st.sidebar.error(e)
    else:
        try:
            # 1. PDF
            pdf = FPDF()
            pdf.add_page()
            # Header
            pdf.set_fill_color(20, 20, 20); pdf.rect(0,0,210,40,'F')
            if escudo:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tf:
                    tf.write(escudo.getvalue()); tname=tf.name
                pdf.image(tname, x=90, y=5, w=30); os.unlink(tname)
            
            pdf.set_font("Arial", 'B', 24); pdf.set_text_color(255,255,255)
            pdf.set_y(32); pdf.cell(0, 10, nome_time.upper(), 0, 1, 'C')
            
            # Info
            pdf.set_text_color(0,0,0); pdf.ln(10)
            pdf.set_font("Arial", '', 12)
            pdf.cell(0, 6, f"Dupla: {int1} & {int2}", 0, 1, 'C')
            pdf.cell(0, 6, f"E-mail: {email_user}", 0, 1, 'C')
            pdf.cell(0, 6, f"Custo Total: EUR {custo_total:.1f}", 0, 1, 'C')
            
            # Tabela
            pdf.ln(5)
            pdf.set_fill_color(230,230,230); pdf.set_font("Arial", 'B', 10)
            pdf.cell(20, 8, "ID", 1, 0, 'C', 1)
            pdf.cell(100, 8, "NOME", 1, 0, 'L', 1)
            pdf.cell(30, 8, "POS", 1, 0, 'C', 1)
            pdf.cell(30, 8, "OVERALL", 1, 1, 'C', 1)
            
            pdf.set_font("Arial", '', 10)
            for p in lista_final:
                n = str(p.get('NAME', '')).encode('latin-1', 'ignore').decode('latin-1')
                pdf.cell(20, 8, str(p.get('INDEX', '')), 1, 0, 'C')
                pdf.cell(100, 8, n, 1, 0, 'L')
                pdf.cell(30, 8, p['TIPO'], 1, 0, 'C')
                pdf.cell(30, 8, str(p.get('OVERALL', '')), 1, 1, 'C')
                
            pdf_bytes = pdf.output(dest='S').encode('latin-1')
            
            # 2. CSV
            df_export = pd.DataFrame(lista_final)
            df_export = df_export.reindex(columns=COLUNAS_MASTER_LIGA)
            csv_str = df_export.to_csv(sep=';', index=False, encoding='utf-8-sig')
            
            # 3. E-mail
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Inscrição {nome_time}"
            msg.attach(MIMEText(f"Nova inscrição.\nTime: {nome_time}\nDupla: {int1}/{int2}", 'plain'))
            
            # Anexos
            att1 = MIMEBase('application', 'pdf')
            att1.set_payload(pdf_bytes); encoders.encode_base64(att1)
            att1.add_header('Content-Disposition', 'attachment; filename="Relatorio.pdf"')
            msg.attach(att1)
            
            att2 = MIMEBase('text', 'csv')
            att2.set_payload(csv_str.encode('utf-8-sig')); encoders.encode_base64(att2)
            att2.add_header('Content-Disposition', f'attachment; filename="Master_{nome_time}.csv"')
            msg.attach(att2)
            
            if escudo:
                att3 = MIMEBase('image', 'png')
                att3.set_payload(escudo.getvalue()); encoders.encode_base64(att3)
                att3.add_header('Content-Disposition', 'attachment; filename="Escudo.png"')
                msg.attach(att3)
                
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP)
                s.send_message(msg)
                
            st.success("✅ Sucesso! Inscrição enviada.")
            
        except Exception as e:
            st.error(f"Erro no envio: {e}")
