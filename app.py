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
ORCAMENTO_MAX = 50000.0

OPCOES_CAMISAS = {f"Padrão {i}": f"uniforme{i}.jpg" for i in range(1, 8)}

# Mapeamento de Posições
POS_MAPPING = {
    "Goleiro": ["GK"],
    "Zagueiro": ["CB", "SWP", "D"],
    "Lateral Esquerdo": ["LB", "LWB"],
    "Lateral Direito": ["RB", "RWB", "SB"],
    "Volante": ["DMF"],
    "Meio Campo": ["CMF", "SMF", "RMF", "LMF", "AMF", "M", "WB"],
    "Atacante": ["SS", "CF", "A"],
    "Ponta Esquerda": ["LWF", "WF"],
    "Ponta Direita": ["RWF"]
}

st.set_page_config(page_title="Squad Builder PES 2013", layout="wide")

# --- CSS PARA FORÇAR LAYOUT COMPACTO ---
st.markdown("""
<style>
    [data-testid="stNumberInput"] button {display: none;}
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    .streamlit-expanderHeader {background-color: #f0f2f6; border-radius: 5px;}
    div[data-baseweb="color-picker"] {width: 100%;}
    [data-testid="stHorizontalBlock"] {gap: 5px !important;}
    [data-testid="column"] {padding: 0 !important; min-width: 0 !important;}
    .streamlit-expanderContent .stButton button {
        width: 100% !important; border-radius: 4px; padding: 2px 0px !important; font-size: 0.8rem; margin-top: -5px;
    }
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
def get_valid_images():
    validas = {}
    for nome, arquivo in OPCOES_CAMISAS.items():
        if os.path.exists(arquivo):
            validas[nome] = arquivo
    return validas

@st.cache_data(show_spinner=False)
def load_data_light():
    file_ui = "jogadores.xlsx"
    if not os.path.exists(file_ui):
        return None
    
    tabs = ['GK', 'DF', 'MF', 'FW']
    data_ui = {}
    # Adicionado 'NATIONALITY' na extração de dados
    cols_ui = ['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL', 'REG. POS.', 'AGE', 'NATIONALITY'] 
    
    try:
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
                df['MARKET PRICE'] = df[col_price].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.')
                df['MARKET PRICE'] = pd.to_numeric(df['MARKET PRICE'], errors='coerce').fillna(0.0)
            else:
                df['MARKET PRICE'] = 0.0
                
            if 'OVERALL' not in df.columns and len(df.columns) > 2:
                 df['OVERALL'] = df.iloc[:, 2]
            
            cols_final = [c for c in cols_ui if c in df.columns]
            df_lean = df[cols_final].copy()
            
            if 'OVERALL' in df_lean.columns:
                df_lean.sort_values('OVERALL', ascending=False, inplace=True)
            
            data_ui[tab] = df_lean
            
        return data_ui
    except Exception as e:
        return None

# Load Inicial
data_ui = load_data_light()
valid_images = get_valid_images()

if data_ui is None:
    st.error("Erro: 'jogadores.xlsx' não encontrado.")
    st.stop()

# Consolidação dos Dados e Preparação de Filtros
df_all = pd.concat(list(data_ui.values()), ignore_index=True)
if 'REG. POS.' in df_all.columns:
    df_all['REG. POS.'] = df_all['REG. POS.'].astype(str).str.strip().str.upper()
else:
    df_all['REG. POS.'] = 'N/A'

df_gk = df_all[df_all['REG. POS.'] == 'GK']
if df_gk.empty and 'GK' in data_ui:
    df_gk = data_ui['GK']

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

custo_total = sum([p.get('MARKET PRICE', 0.0) for p in st.session_state.escolhas.values() if p])
saldo = ORCAMENTO_MAX - custo_total

# --- TÍTULO E PAINEL FINANCEIRO ---
st.title("⚽ SQUAD BUILDER")
st.markdown("### 💰 Painel Financeiro")

c_filt, c_gasto, c_saldo = st.columns([1, 1, 1])
with c_filt:
    filtro_p = st.number_input("Preço Máx. por Jogador (€)", 0.0, 100000.0, ORCAMENTO_MAX, 100.0, key="input_filter")
with c_gasto:
    st.metric("Gasto Atual", f"€{custo_total:.0f}")
with c_saldo:
    st.metric("Saldo Restante", f"€{saldo:.0f}")

st.progress(min(custo_total / ORCAMENTO_MAX, 1.0))
st.markdown("---")

# --- COMPONENTES AUXILIARES ---
def format_func(row):
    if row is None: return "Selecionar..."
    
    idade = row.get('AGE', '?')
    if pd.notna(idade) and isinstance(idade, (int, float)):
        idade = int(idade)
        
    nacionalidade = row.get('NATIONALITY', '?')
    if pd.isna(nacionalidade):
        nacionalidade = '?'
        
    return f"{row.get('NAME','?')} | {nacionalidade} | {row.get('REG. POS.','?')} | Idade: {idade} | OV: {row.get('OVERALL','?')} | €{row.get('MARKET PRICE',0):.1f}"

def seletor(label, df, key):
    escolha = st.session_state.escolhas.get(key)
    val_atual = escolha.get('MARKET PRICE', 0.0) if escolha else 0.0
    usados = [v['NAME'] for k,v in st.session_state.escolhas.items() if v and k != key]
    
    mask = (df['MARKET PRICE'] <= (saldo + val_atual)) & (df['MARKET PRICE'] <= filtro_p)
    df_f = df[mask]
    if usados: df_f = df_f[~df_f['NAME'].isin(usados)]
        
    ops = [None] + df_f.to_dict('records')
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

def render_position_filters(prefix):
    with st.expander("🔍 Filtro de Posições (Jogadores de Linha)", expanded=False):
        c1, c2, c3 = st.columns(3)
        chk = {}
        chk["Goleiro"] = c1.checkbox("Goleiro (GK)", key=f"c_gk_{prefix}")
        chk["Zagueiro"] = c1.checkbox("Zagueiro (CB, SWP, D)", key=f"c_cb_{prefix}")
        chk["Lateral Esquerdo"] = c1.checkbox("Lateral Esq. (LB, LWB)", key=f"c_le_{prefix}")
        
        chk["Lateral Direito"] = c2.checkbox("Lateral Dir. (RB, RWB, SB)", key=f"c_ld_{prefix}")
        chk["Volante"] = c2.checkbox("Volante (DMF)", key=f"c_vol_{prefix}")
        chk["Meio Campo"] = c2.checkbox("Meio Campo (CMF, SMF...)", key=f"c_mc_{prefix}")
        
        chk["Atacante"] = c3.checkbox("Atacante (CF, SS, A)", key=f"c_ata_{prefix}")
        chk["Ponta Esquerda"] = c3.checkbox("Ponta Esq. (LWF, WF)", key=f"c_pe_{prefix}")
        chk["Ponta Direita"] = c3.checkbox("Ponta Dir. (RWF)", key=f"c_pd_{prefix}")

        allowed = []
        for k, is_chk in chk.items():
            if is_chk: allowed.extend(POS_MAPPING[k])
        return allowed

lista = []

# --- ABAS PRINCIPAIS ---
tab_cad, tab_uni, tab_tit, tab_res = st.tabs(["📋 Cadastro", "👕 Uniformes", "🏟️ Equipe Titular", "✈️ Equipe Reserva"])

with tab_cad:
    st.subheader("Dados da Inscrição")
    c_int1, c_int2 = st.columns(2)
    int1 = c_int1.text_input("Jogador 1", key="input_int1")
    int2 = c_int2.text_input("Jogador 2", key="input_int2")
    
    c_team, c_mail = st.columns(2)
    nome_time = c_team.text_input("Nome do Time", "MEU TIME", key="input_team")
    email_user = c_mail.text_input("E-mail", key="input_email")
    
    c_escudo, c_form = st.columns(2)
    escudo = c_escudo.file_uploader("Escudo", type=['png','jpg'], key="input_logo")
    formacao = c_form.selectbox("Formação Base", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key="input_fmt", help="Informativo. O sistema permite escalar como desejar.")

with tab_uni:
    st.subheader("Seleção de Uniformes")
    tab_titular_uni, tab_reserva_uni = st.tabs(["🏠 Titular", "✈️ Reserva"])
    
    def ui_uniforme(tipo_kit):
        key_pfx = f"uni_{tipo_kit.lower()}"
        state_key = f"uni_{tipo_kit.lower()}_sel" 
        
        st.caption(f"Selecione o Padrão ({tipo_kit}):")
        modelos = list(OPCOES_CAMISAS.keys())
        cols = st.columns(7) 
        
        for i, mod_nome in enumerate(modelos):
            arquivo = valid_images.get(mod_nome)
            with cols[i]:
                if arquivo:
                    st.image(arquivo, width=200) 
                
                is_selected = (st.session_state[state_key] == mod_nome)
                if is_selected:
                    st.button("✅", key=f"btn_sel_{key_pfx}_{i}", disabled=True)
                else:
                    if st.button("Usar", key=f"btn_{key_pfx}_{i}"):
                        st.session_state[state_key] = mod_nome
                        st.rerun()
        
        st.caption(f"Cores ({tipo_kit}):")
        qtd_cores = st.radio(f"Cores", [2, 3], horizontal=True, key=f"{key_pfx}_qtd", label_visibility="collapsed")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("**Camisa**")
            cp = st.color_picker("Principal", "#FF0000", key=f"{key_pfx}_cp")
            cs = st.color_picker("Secundária", "#FFFFFF", key=f"{key_pfx}_cs")
            ce = None
            if qtd_cores == 3:
                ce = st.color_picker("Extra", "#000000", key=f"{key_pfx}_ce")
        with c2:
            st.markdown("**Calção**")
            cc = st.color_picker("Base", "#FFFFFF", key=f"{key_pfx}_cc")
        with c3:
            st.markdown("**Meias**")
            cm = st.color_picker("Base", "#FFFFFF", key=f"{key_pfx}_cm")
            
        return {"modelo": st.session_state[state_key], "img": valid_images.get(st.session_state[state_key]),
                "qtd": qtd_cores, "camisa": [cp, cs, ce], "calcao": cc, "meia": cm}

    with tab_titular_uni: kit_titular = ui_uniforme("Titular")
    with tab_reserva_uni: kit_reserva = ui_uniforme("Reserva")

with tab_tit:
    allowed_tit = render_position_filters("tit")
    df_linha_tit = df_all if not allowed_tit else df_all[df_all['REG. POS.'].isin(allowed_tit)]
    
    c_tit1, c_tit2 = st.columns(2)
    with c_tit1:
        gk = seletor("Jogador 1 (Goleiro)", df_gk, "gk_tit")
        if gk: lista.append({**gk, "T": "TITULAR", "P": gk.get('REG. POS.', 'GK'), "K": "gk_tit"})
        
        for i in range(2, 7):
            p = seletor(f"Jogador {i}", df_linha_tit, f"tit_{i}")
            if p: lista.append({**p, "T": "TITULAR", "P": p.get('REG. POS.', 'N/A'), "K": f"tit_{i}"})
            
    with c_tit2:
        for i in range(7, 12):
            p = seletor(f"Jogador {i}", df_linha_tit, f"tit_{i}")
            if p: lista.append({**p, "T": "TITULAR", "P": p.get('REG. POS.', 'N/A'), "K": f"tit_{i}"})

with tab_res:
    allowed_res = render_position_filters("res")
    df_linha_res = df_all if not allowed_res else df_all[df_all['REG. POS.'].isin(allowed_res)]
    
    c_res1, c_res2 = st.columns(2)
    with c_res1:
        gkr = seletor("Reserva 1 (Goleiro)", df_gk, "gk_res")
        if gkr: lista.append({**gkr, "T": "RESERVA", "P": gkr.get('REG. POS.', 'GK'), "K": "gk_res"})
        
        for i in range(2, 4):
            p = seletor(f"Reserva {i}", df_linha_res, f"res_{i}")
            if p: lista.append({**p, "T": "RESERVA", "P": p.get('REG. POS.', 'N/A'), "K": f"res_{i}"})
            
    with c_res2:
        for i in range(4, 6):
            p = seletor(f"Reserva {i}", df_linha_res, f"res_{i}")
            if p: lista.append({**p, "T": "RESERVA", "P": p.get('REG. POS.', 'N/A'), "K": f"res_{i}"})

st.markdown("---")
if st.button("🔄 Limpar Tudo", use_container_width=True):
    reset_callback()
    st.rerun()
st.markdown("###")

# --- EXPORTAÇÃO ---
if st.button("✅ ENVIAR INSCRIÇÃO", type="primary", use_container_width=True):
    erros = []
    if not int1: erros.append("Jogador 1")
    if not int2: erros.append("Jogador 2")
    if not email_user: erros.append("E-mail")
    if len(lista) < 16: erros.append(f"Faltam {16 - len(lista)} jogadores")
    
    if erros:
        st.error(f"Faltam dados: {', '.join(erros)}")
        st.stop()
    
    with st.spinner("Enviando..."):
        try:
            # 1. GERAÇÃO DO TXT
            txt_content = f"TIME: {nome_time.upper()}\n"
            txt_content += f"JOGADORES: {int1} & {int2}\n"
            txt_content += f"FORMAÇÃO: {formacao}\n"
            txt_content += "="*30 + "\n\n"
            
            txt_content += "--- TITULARES ---\n"
            for p in lista:
                if p['T'] == "TITULAR":
                    num = st.session_state.numeros.get(p['K'], "")
                    preco = p.get('MARKET PRICE', 0.0)
                    txt_content += f"ID: {p['INDEX']} | Nº: {num} | {p['NAME']} | Preço: €{preco:.1f}\n"
            
            txt_content += "\n--- RESERVAS ---\n"
            for p in lista:
                if p['T'] == "RESERVA":
                    num = st.session_state.numeros.get(p['K'], "")
                    preco = p.get('MARKET PRICE', 0.0)
                    txt_content += f"ID: {p['INDEX']} | Nº: {num} | {p['NAME']} | Preço: €{preco:.1f}\n"

            # 2. GERAÇÃO DO PDF VISUAL
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(20,20,20); pdf.rect(0,0,210,50,'F')
            
            if escudo:
                ext = os.path.splitext(escudo.name)[1].lower() if escudo.name else ".png"
                if ext not in ['.png', '.jpg', '.jpeg']: ext = ".png"
                with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tf:
                    tf.write(escudo.getvalue()); tname=tf.name
                try:
                    pdf.image(tname, x=10, y=5, w=25)
                except Exception:
                    pass
                finally:
                    os.unlink(tname)
            
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
                
                cores = [kit['camisa'][0], kit['camisa'][1]]
                if kit['qtd'] == 3 and kit['camisa'][2]: cores.append(kit['camisa'][2])
                cores.append(kit['calcao'])
                cores.append(kit['meia'])
                
                bx = x_pos + (25 - (len(cores)*4.5))/2
                by = 40
                pdf.set_draw_color(255, 255, 255) 
                for hex_c in cores:
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
                        pdf.cell(20, 5, str(p['P']), 0, 0, 'C')
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
            pdf.cell(0, 8, f"FORÇA: {med:.1f}", 0, 1, 'C', fill=True)
            
            # EMAIL
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, msg['To'] = EMAIL_DESTINO
            msg['Subject'] = f"Inscrição: {nome_time}"
            msg.attach(MIMEText(f"Nova inscrição recebida.\nTime: {nome_time}", 'plain'))
            
            att1 = MIMEBase('application', 'pdf')
            att1.set_payload(pdf.output(dest='S').encode('latin-1'))
            encoders.encode_base64(att1)
            att1.add_header('Content-Disposition', 'attachment; filename="Elenco.pdf"')
            msg.attach(att1)
            
            att2 = MIMEBase('text', 'plain')
            att2.set_payload(txt_content.encode('utf-8'))
            encoders.encode_base64(att2)
            att2.add_header('Content-Disposition', f'attachment; filename="IDs_{nome_time}.txt"')
            msg.attach(att2)

            if escudo:
                att3 = MIMEBase('image', 'png')
                att3.set_payload(escudo.getvalue())
                encoders.encode_base64(att3)
                att3.add_header('Content-Disposition', 'attachment; filename="Escudo.png"')
                msg.attach(att3)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP); s.send_message(msg)
                
            st.success("✅ ENVIADO COM SUCESSO!")

        except smtplib.SMTPAuthenticationError:
            st.error("Erro de Senha do E-mail.")
        except Exception as e:
            st.error(f"Erro: {e}")
