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
ORCAMENTO_MAX = 5000.0

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

# --- DICIONÁRIOS DE HABILIDADES ---
PLAYSTYLES = {
    "Clássico No. 10": ("P01 CLASSIC NO.10", "Jogador armador estático que faz bons passes em vez de manter um bom ritmo ou de movimentar-se muito."),
    "Primeiro Volante": ("P02 ANCHOR MAN", "Volante recuado que protege a defesa."),
    "Malandro": ("P03 TRICKSTER", "Driblador Habilidoso que passa por cima dos adversários."),
    "Pique": ("P04 DARTING RUN", "Jogador de bom ritmo que gosta de ir ao ataque."),
    "Drible Veloz": ("P05 MAZING RUN", "Driblador habilidoso com movimentos rápidos que dão trabalho a qualquer defesa."),
    "Passe Preciso": ("P06 PINPOINT PASS", "Especialista em lançamentos que pode fazer passes de qualidade de longas distâncias."),
    "Cruz. Antecipado": ("P07 EARLY CROSS", "Jogador com ótima visão de jogo que não desperdiça cruzamentos antecipados."),
    "Onipresente": ("P08 BOX TO BOX", "Jogador incansável que percorre o campo todo durante os 90 minutos."),
    "Corrida Com Gás": ("P09 INCISIVE RUN", "Driblador especialista em abrir espaços para buscar oportunidades de gol."),
    "Batedor Pró": ("P10 LONG RANGER", "Jogador que sempre chuta e sempre tenta criar espaços para chutes."),
    "Raçudo": ("P11 ENFORCER", "Jogador robusto que dá combate e tem como único objetivo segurar o ataque adversário."),
    "Artilheiro": ("P12 GOAL POACHER", "Artilheiro voraz que parte pra cima do último zagueiro."),
    "Puxa Marcação": ("P13 DUMMY RUNNER", "Jogador que atrai a defesa para criar espaços a serem explorados por outros jogadores."),
    "Flutuante": ("P14 FREE ROAMING", "Jogador com ótima visão de gol que avança em qualquer oportunidade."),
    "Craque": ("P15 TALISMAN", "Craque que impulsiona todo o time a seguir em frente."),
    "Homem de Área": ("P16 FOX IN THE BOX", "Artilheiro que fica na grande área esperando pela bola."),
    "Defensor que Ataca": ("P17 OFFENSIVE SIDEBACK", "Jogador de defesa que gosta de avançar e surpreender a retaguarda adversária quando tem oportunidade."),
    "Volta para Marcar": ("P18 TRACK BACK", "Jogador de ataque que pressiona ativamente a saída do adversário e tenta roubar a bola.")
}

SKILLS = {
    "Toque de Primeira": ("S01 1-TOUCH PLAY", "Melhora o toque de primeira do jogador em passes e chutes."),
    "Trivela": ("S02 OUTSIDE CURVE", "Melhora os toques com a parte externa do pé."),
    "Arremesso Longo": ("S03 LONG THROW", "Aumenta o alcance dos arremessos laterais longos."),
    "Super Substituto": ("S04 SUPER-SUB", "Aumenta o desempenho do jogador quando ele entra nos minutos finais."),
    "Velocista": ("S05 SPEED MERCHANT", "Permite o giro especial em alta velocidade."),
    "Chute de Longe": ("S06 LONG RANGE DRIVE", "Jogador cujos chutes a gol de longa distância perdem altura abruptamente. Um pesadelo para os goleiros."),
    "Habil. Finta c/ Ombro": ("S07 SHOULDER FEINT SKILLS", "Melhora a técnica e a precisão na execução da finta Matthews e a finta de corpo."),
    "Habil. de Giro": ("S08 TURNING SKILLS", "Melhora a técnica e a precisão na execução do giro de 180°."),
    "Habil. Giro 360": ("S09 ROULETTE SKILLS", "Melhora a técnica e a precisão na execução do Marseille Roulette ou do giro em um pé só."),
    "Habil. Elástico": ("S10 FLIP FLAP SKILLS", "Melhora a técnica e a precisão do elástico ou do elástico invertido."),
    "Habil. Carretilha": ("S11 FLICKING SKILLS", "Melhora a técnica e a precisão para levantar a bola ou executar carretilha."),
    "Habil. Pedalada": ("S12 SCISSORS SKILLS", "Melhora a técnica e a precisão na execução de passadas sobre a bola. Incluindo a passada sobre a bola simples e a passada sobre a bola para trás."),
    "Habil. de Domínio": ("S13 STEP ON SKILLS", "Melhora a técnica e a precisão na execução de finta em L.giro com puxada para trás. Puxada para trás. Finta com o calcanhar e toques com a sola do pé."),
    "Hab. de toque rápido": ("S14 DEFT TOUCH SKILLS", "Melhora a técnica e a precisão ao fazer a pedalada lateral e a pedalada lateral com toque."),
    "Chute com o peito do pé": ("S15 KNUCKLE SHOT", "Melhora a precisão dos chutes com o peito do pé."),
    "Chute com pulo": ("S16 JUMPING VOLLEY", "Às vezes o jogador tenta chutes de primeira com a bola no ar."),
    "Voleio": ("S17 SCISSOR KICK", "Melhora o acerto do chute de voleio."),
    "Toque de calcanhar": ("S18 HEEL FLICK", "Melhora a habilidade do jogador em chutes e passes com a bola no ar."),
    "Passe com peso": ("S19 WEIGHTED PASS", "Aplica backspin na bola em passes longos e lançamentos pelo alto."),
    "Toque duplo": ("S20 DOUBLE TOUCH", "Melhora a técnica e a precisão na execução do toque duplo."),
    "Drible de vaca": ("S21 RUN AROUND", "Melhora a técnica e a precisão na execução do drible da vaca."),
    "Chapéu": ("S22 SOMBRERO", "Melhora a técnica e precisão quando executa o chapéu."),
    "Puxada em 180°": ("S23 180 DRAG", "Permite que o jogador use a parte de dentro do pé para driblar."),
    "Desarme afastado": ("S24 LUNGING TACKLE", "Melhora a eficácia do desarme em velocidade."),
    "Peixinho": ("S25 DIVING HEADER", "Às vezes o jogador pode tentar bloqueios um pouco diferentes."),
    "Arr. longo do gol": ("S26 GK LONG THROW", "Melhora o alcance dos arremessos do goleiro.")
}

st.set_page_config(page_title="Squad Builder PES 2013", layout="wide", initial_sidebar_state="expanded")

# --- CSS PARA FORÇAR LAYOUT COMPACTO ---
st.markdown("""
<style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    .streamlit-expanderHeader {background-color: #f0f2f6; border-radius: 5px;}
    div[data-baseweb="color-picker"] {width: 100%;}
    [data-testid="stHorizontalBlock"] {gap: 5px !important;}
    [data-testid="column"] {padding: 0 !important; min-width: 0 !important;}
    .streamlit-expanderContent .stButton button {
        width: 100% !important; border-radius: 4px; padding: 2px 0px !important; font-size: 0.8rem; margin-top: -5px;
    }
    [data-testid="stImage"] img { border-radius: 5px; }
    
    .mini-card-stats {
        font-size: 0.75rem;
        color: #444;
        background-color: #f9f9f9;
        padding: 6px 10px;
        border-radius: 4px;
        margin-top: -10px;
        margin-bottom: 10px;
        display: block;
        border: 1px solid #ddd;
        line-height: 1.4;
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
def load_data_light():
    file_ui = "jogadoresdata.xlsx"
    if not os.path.exists(file_ui):
        return None
    
    data_ui = {}
    
    try:
        df = pd.read_excel(file_ui)
        df_cols_upper = df.columns.str.strip().str.upper()
        
        col_map = {c_upper: c for c_upper, c in zip(df_cols_upper, df.columns)}
        
        col_id = col_map.get('INDEX', df.columns[0])
        col_name = col_map.get('NAME', 'NAME')
        col_nat = col_map.get('NATIONALITY', 'NATIONALITY')
        col_age = col_map.get('AGE', 'AGE')
        col_pos = col_map.get('POSITION', 'POSITION')
        col_ov = col_map.get('OVERALL', 'overall')
        col_price = col_map.get('MARKET PRICE', 'market price')

        df.rename(columns={col_id: 'INDEX', col_name: 'NAME', col_nat: 'NATIONALITY', 
                           col_age: 'AGE', col_pos: 'REG. POS.', col_ov: 'OVERALL'}, inplace=True)
                           
        df['INDEX'] = df['INDEX'].astype(str).str.strip()
        
        if col_price in df.columns:
            df['MARKET PRICE'] = df[col_price].astype(str).str.replace(r'[^\d.,]', '', regex=True).str.replace(',', '.')
            df['MARKET PRICE'] = pd.to_numeric(df['MARKET PRICE'], errors='coerce').fillna(0.0) / 10.0
        else:
            df['MARKET PRICE'] = 0.0
            
        if 'OVERALL' in df.columns:
            df.sort_values('OVERALL', ascending=False, inplace=True)
        
        all_skill_cols = [t[0] for t in PLAYSTYLES.values()] + [t[0] for t in SKILLS.values()]
        for c in all_skill_cols:
            if c not in df.columns:
                df[c] = 0.0
            else:
                df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0.0)
        
        required_attrs = ['HEIGHT', 'ATTACK', 'DEFENCE', 'TOP SPEED', 'STAMINA', 'GOAL KEEPING SKILLS', 
                          'RESPONSE', 'JUMP', 'BODY BALANCE', 'HEADER ACCURACY', 'LONG PASS ACCURACY', 
                          'DRIBBLE SPEED', 'SHORT PASS ACCURACY', 'TENACITY', 'BALL CONTROLL', 
                          'DRIBBLE ACCURACY', 'EXPLOSIVE POWER', 'SHOT ACCURACY', 'KICKING POWER']
        
        for attr in required_attrs:
            if attr not in df.columns:
                df[attr] = 0 
            else:
                df[attr] = pd.to_numeric(df[attr], errors='coerce').fillna(0)
                
        data_ui["Jogadores"] = df
        return data_ui
    except Exception as e:
        return None

# Load Inicial
data_ui = load_data_light()
valid_images = get_valid_images()

if data_ui is None:
    st.error("Erro: 'jogadoresdata.xlsx' não encontrado ou formato inválido.")
    st.stop()

# Consolidação dos Dados e Preparação de Filtros
df_all = data_ui["Jogadores"].copy()
if 'REG. POS.' in df_all.columns:
    df_all['REG. POS.'] = df_all['REG. POS.'].astype(str).str.strip().str.upper()
else:
    df_all['REG. POS.'] = 'N/A'

df_gk = df_all[df_all['REG. POS.'] == 'GK']

# --- PREPARAÇÃO DAS LISTAS DE OPÇÕES ---
lista_nacionalidades = []
if 'NATIONALITY' in df_all.columns:
    lista_nacionalidades = df_all['NATIONALITY'].dropna().astype(str).str.strip().unique().tolist()
    lista_nacionalidades = sorted([n for n in lista_nacionalidades if n])

br_str = next((n for n in lista_nacionalidades if n.upper() in ['BRASIL', 'BRAZIL']), 'Brasil')
if br_str in lista_nacionalidades:
    lista_nacionalidades.remove(br_str)

opcoes_nacionalidade = [br_str, "Todos"] + lista_nacionalidades
opcoes_pos = list(POS_MAPPING.keys())
opcoes_hab = list(PLAYSTYLES.keys()) + list(SKILLS.keys())

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

# --- SIDEBAR (PAINEL FINANCEIRO & FILTROS) ---
st.sidebar.title("💰 Painel Financeiro")
st.sidebar.metric("Gasto Atual", f"€{custo_total:.0f}")
st.sidebar.metric("Saldo Restante", f"€{saldo:.0f}")
st.sidebar.progress(min(custo_total / ORCAMENTO_MAX, 1.0))

st.sidebar.markdown("---")
st.sidebar.subheader("🔍 Filtros de Jogadores")

filtro_p = st.sidebar.number_input("Preço Máx. (€)", 0.0, 10000.0, ORCAMENTO_MAX, 10.0, key="input_filter")
filtro_pais = st.sidebar.selectbox("Nacionalidade", opcoes_nacionalidade, index=1, key="input_pais")

c_alt, c_vel = st.sidebar.columns(2)
with c_alt:
    filtro_alt = st.number_input("Altura Mín. (cm)", 100, 220, 150, 1, key="input_alt")
with c_vel:
    filtro_vel = st.number_input("Vel. Mínima", 40, 99, 40, 1, key="input_vel", help="Filtra por Top Speed")

pos_selecionadas = st.sidebar.multiselect("Posição (Linha)", opcoes_pos, placeholder="Selecione as posições...", key="ms_pos")
allowed_pos = []
for p in pos_selecionadas:
    allowed_pos.extend(POS_MAPPING[p])

hab_selecionadas = st.sidebar.multiselect("Características (Max 10)", opcoes_hab, max_selections=10, placeholder="Selecione estilos/cartões...", key="ms_hab")

with st.sidebar.expander("📖 O que cada característica faz?"):
    st.markdown("**Estilo de Jogo (Playstyles)**")
    for h_nome, (_, desc) in PLAYSTYLES.items():
        st.markdown(f"<span style='font-size: 0.8rem;'><b>{h_nome}:</b> {desc}</span>", unsafe_allow_html=True)
        
    st.markdown("<br>**Cartões de Habilidade (Skills)**", unsafe_allow_html=True)
    for h_nome, (_, desc) in SKILLS.items():
        st.markdown(f"<span style='font-size: 0.8rem;'><b>{h_nome}:</b> {desc}</span>", unsafe_allow_html=True)

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
    mask = mask & (df['HEIGHT'] >= filtro_alt)
    mask = mask & (df['TOP SPEED'] >= filtro_vel)
    
    if filtro_pais != "Todos":
        mask = mask & (df['NATIONALITY'].astype(str).str.strip() == filtro_pais)
        
    for hab in hab_selecionadas:
        if hab in PLAYSTYLES:
            col_hab = PLAYSTYLES[hab][0]
        else:
            col_hab = SKILLS[hab][0]
        mask = mask & (df[col_hab] == 1)
        
    df_f = df[mask]
    if usados: df_f = df_f[~df_f['NAME'].isin(usados)]
        
    ops = [None] + df_f.to_dict('records')
    if escolha and escolha['NAME'] not in [o['NAME'] for o in ops if o]: ops.insert(1, escolha)
    
    idx = 0
    if escolha:
        for i, o in enumerate(ops): 
            if o and o['NAME'] == escolha['NAME']: idx = i; break
    
    c_sel, c_num = st.columns([3.5, 1.5]) 
    with c_sel:
        new_sel = st.selectbox(label, ops, index=idx, format_func=format_func, key=f"s_{key}_{st.session_state.form_id}")
        
        if new_sel:
            pos = new_sel.get('REG. POS.', '').strip().upper()
            alt = int(new_sel.get('HEIGHT', 0)) if pd.notna(new_sel.get('HEIGHT')) else '-'
            
            def get_stat(col): 
                val = new_sel.get(col, '-')
                return int(val) if pd.notna(val) and isinstance(val, (int, float)) else val
            
            # --- ATRIBUTOS PRINCIPAIS ---
            if pos in ['GK']:
                stats_str = f"📏 ALT: {alt}cm | 🧤 HAB: {get_stat('GOAL KEEPING SKILLS')} | ⚡ RES: {get_stat('RESPONSE')} | 🛡️ DEF: {get_stat('DEFENCE')} | 🦘 SAL: {get_stat('JUMP')} | ⚖️ EQU: {get_stat('BODY BALANCE')}"
            elif pos in ['CB', 'SWP', 'D']:
                stats_str = f"📏 ALT: {alt}cm | 🛡️ DEF: {get_stat('DEFENCE')} | 🗣️ CAB: {get_stat('HEADER ACCURACY')} | ⚖️ EQU: {get_stat('BODY BALANCE')} | 🦘 SAL: {get_stat('JUMP')} | ⚡ RES: {get_stat('RESPONSE')}"
            elif pos in ['LB', 'LWB', 'RB', 'RWB', 'SB']:
                stats_str = f"📏 ALT: {alt}cm | 🚀 V.MAX: {get_stat('TOP SPEED')} | 🫁 VIG: {get_stat('STAMINA')} | 🎯 P.LON: {get_stat('LONG PASS ACCURACY')} | 💨 V.DRI: {get_stat('DRIBBLE SPEED')} | 🛡️ DEF: {get_stat('DEFENCE')}"
            elif pos in ['DMF']:
                stats_str = f"📏 ALT: {alt}cm | 🛡️ DEF: {get_stat('DEFENCE')} | 👟 P.CUR: {get_stat('SHORT PASS ACCURACY')} | 🫁 VIG: {get_stat('STAMINA')} | ⚖️ EQU: {get_stat('BODY BALANCE')} | 😤 TEN: {get_stat('TENACITY')}"
            elif pos in ['CMF', 'SMF', 'RMF', 'LMF', 'AMF', 'M', 'WB']:
                stats_str = f"📏 ALT: {alt}cm | 👟 P.CUR: {get_stat('SHORT PASS ACCURACY')} | ⚽ C.BOL: {get_stat('BALL CONTROLL')} | 🪄 P.DRI: {get_stat('DRIBBLE ACCURACY')} | 🫁 VIG: {get_stat('STAMINA')} | ⚔️ ATQ: {get_stat('ATTACK')}"
            elif pos in ['LWF', 'WF', 'RWF']:
                stats_str = f"📏 ALT: {alt}cm | 🚀 V.MAX: {get_stat('TOP SPEED')} | 💨 V.DRI: {get_stat('DRIBBLE SPEED')} | 💥 EXP: {get_stat('EXPLOSIVE POWER')} | 🪄 P.DRI: {get_stat('DRIBBLE ACCURACY')} | ⚔️ ATQ: {get_stat('ATTACK')}"
            elif pos in ['SS', 'CF', 'A']:
                stats_str = f"📏 ALT: {alt}cm | ⚔️ ATQ: {get_stat('ATTACK')} | 🎯 P.CHU: {get_stat('SHOT ACCURACY')} | 💣 F.CHU: {get_stat('KICKING POWER')} | 🗣️ CAB: {get_stat('HEADER ACCURACY')} | 🚀 V.MAX: {get_stat('TOP SPEED')}"
            else:
                stats_str = f"📏 ALT: {alt}cm | ⚔️ ATQ: {get_stat('ATTACK')} | 🛡️ DEF: {get_stat('DEFENCE')} | 🚀 V.MAX: {get_stat('TOP SPEED')} | 🫁 VIG: {get_stat('STAMINA')}"
            
            # --- CARTÕES DE HABILIDADE (S01-S26 e P01-P18) ---
            habs_ativas = []
            for h_nome, (col_name, _) in list(PLAYSTYLES.items()) + list(SKILLS.items()):
                if new_sel.get(col_name) == 1:
                    habs_ativas.append(h_nome)
            
            habs_str = " | ".join(habs_ativas) if habs_ativas else "Nenhuma"
            
            # Mostrando tudo no Card
            st.markdown(f"""
                <div class='mini-card-stats'>
                    <b>Atributos:</b> {stats_str}<br>
                    <span style='color:#0055aa;'><b>🃏 Cartões/Estilo:</b> {habs_str}</span>
                </div>
            """, unsafe_allow_html=True)
            
    with c_num:
        val_n = st.session_state.numeros.get(key, 0)
        if isinstance(val_n, str):
             val_n = int(val_n) if val_n.isdigit() else 0
        new_n = st.number_input("Nº", min_value=0, max_value=99, value=val_n, step=1, key=f"n_{key}_{st.session_state.form_id}")
        st.session_state.numeros[key] = new_n
        
    if new_sel != escolha:
        st.session_state.escolhas[key] = new_sel
        st.rerun()
    return new_sel

lista = []
df_linha_filtrado = df_all if not allowed_pos else df_all[df_all['REG. POS.'].isin(allowed_pos)]

# --- TÍTULO ---
st.title("⚽ SQUAD BUILDER")

# --- ABAS PRINCIPAIS ---
tab_cad, tab_uni, tab_elenco, tab_resumo = st.tabs(["📋 Cadastro", "👕 Uniformes", "👥 Elenco", "📊 Resumo"])

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

with tab_elenco:
    with st.expander("🏟️ Titular", expanded=True):
        c_tit1, c_tit2 = st.columns(2)
        with c_tit1:
            gk = seletor("Jogador 1 (Goleiro)", df_gk, "gk_tit")
            if gk: lista.append({**gk, "T": "TITULAR", "P": gk.get('REG. POS.', 'GK'), "K": "gk_tit"})
            
            for i in range(2, 7):
                p = seletor(f"Jogador {i}", df_linha_filtrado, f"tit_{i}")
                if p: lista.append({**p, "T": "TITULAR", "P": p.get('REG. POS.', 'N/A'), "K": f"tit_{i}"})
                
        with c_tit2:
            for i in range(7, 12):
                p = seletor(f"Jogador {i}", df_linha_filtrado, f"tit_{i}")
                if p: lista.append({**p, "T": "TITULAR", "P": p.get('REG. POS.', 'N/A'), "K": f"tit_{i}"})

    with st.expander("✈️ Reserva", expanded=False):
        c_res1, c_res2 = st.columns(2)
        with c_res1:
            gkr = seletor("Reserva 1 (Goleiro)", df_gk, "gk_res")
            if gkr: lista.append({**gkr, "T": "RESERVA", "P": gkr.get('REG. POS.', 'GK'), "K": "gk_res"})
            
            for i in range(2, 4):
                p = seletor(f"Reserva {i}", df_linha_filtrado, f"res_{i}")
                if p: lista.append({**p, "T": "RESERVA", "P": p.get('REG. POS.', 'N/A'), "K": f"res_{i}"})
                
        with c_res2:
            for i in range(4, 6):
                p = seletor(f"Reserva {i}", df_linha_filtrado, f"res_{i}")
                if p: lista.append({**p, "T": "RESERVA", "P": p.get('REG. POS.', 'N/A'), "K": f"res_{i}"})

with tab_resumo:
    st.subheader("Resumo da Escalacão")
    if len(lista) > 0:
        df_resumo = pd.DataFrame(lista)
        df_resumo['Nº'] = [st.session_state.numeros.get(p['K'], 0) for p in lista]
        df_resumo['PREÇO (€)'] = [f"€ {p.get('MARKET PRICE', 0.0):.1f}" for p in lista]
        
        colunas_exibicao = ['Nº', 'NAME', 'P', 'OVERALL', 'PREÇO (€)', 'T']
        df_display = df_resumo[colunas_exibicao].copy()
        df_display.rename(columns={'NAME': 'NOME', 'P': 'POSIÇÃO', 'T': 'STATUS'}, inplace=True)
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum jogador selecionado ainda. Vá na aba 'Elenco' para montar seu time.")

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
                    num = st.session_state.numeros.get(p['K'], 0)
                    str_num = str(num) if num != 0 else ""
                    preco = p.get('MARKET PRICE', 0.0)
                    txt_content += f"ID: {p['INDEX']} | Nº: {str_num} | {p['NAME']} | Preço: €{preco:.1f}\n"
            
            txt_content += "\n--- RESERVAS ---\n"
            for p in lista:
                if p['T'] == "RESERVA":
                    num = st.session_state.numeros.get(p['K'], 0)
                    str_num = str(num) if num != 0 else ""
                    preco = p.get('MARKET PRICE', 0.0)
                    txt_content += f"ID: {p['INDEX']} | Nº: {str_num} | {p['NAME']} | Preço: €{preco:.1f}\n"

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
                        raw_num = st.session_state.numeros.get(p['K'], 0)
                        str_num = str(raw_num) if raw_num != 0 else ""
                        ov = p.get('OVERALL', 0)
                        try: soma += float(ov); qtd += 1
                        except: pass
                        pdf.cell(20, 5, str(p['P']), 0, 0, 'C')
                        pdf.cell(15, 5, str_num, 0, 0, 'C')
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
