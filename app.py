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
        # Carrega mantendo todas as colunas para o CSV do jogo
        data = {tab: pd.read_excel(file, sheet_name=tab) for tab in tabs}
        for tab in data:
            data[tab].columns = data[tab].columns.str.strip()
        return data
    except:
        st.error(f"Erro ao carregar '{file}'. Verifique se ele contém as abas GK, DF, MF e FW.")
        st.stop()

# Formatação para o seletor (exibição amigável)
def format_func(row):
    if row is None: return "Selecione..."
    # Tenta usar 'Name' ou 'NAME' conforme a planilha
    name_col = 'Name' if 'Name' in row else 'NAME'
    ov_col = 'Overall' if 'Overall' in row else 'overall'
    val_col = 'Market Value (M€)' if 'Market Value (M€)' in row else 'MARKET PRICE'
    return f"{row[name_col]} - OV: {row.get(ov_col, '??')} - €{row.get(val_col, 0)}"

# --- INICIALIZAÇÃO ---
if 'escolhas' not in st.session_state: st.session_state.escolhas = {}
if 'form_id' not in st.session_state: st.session_state.form_id = 0

def reset_callback():
    st.session_state.escolhas = {}
    st.session_state.form_id += 1

data = load_data()
ORCAMENTO_MAX = 3000.0

# Cálculo de saldo (procurando a coluna de valor correta)
def get_val(row):
    for c in ['Market Value (M€)', 'MARKET PRICE', 'market value']:
        if c in row: return row[c]
    return 0

custo_atual = sum([get_val(v) for v in st.session_state.escolhas.values() if v is not None])
saldo = ORCAMENTO_MAX - custo_atual

st.title("⚽ PES 2013 - Gestão de Elenco")

with st.sidebar:
    st.header("📋 Cadastro do Time")
    int1 = st.text_input("Integrante 1", key=f"i1_{st.session_state.form_id}")
    int2 = st.text_input("Integrante 2", key=f"i2_{st.session_state.form_id}")
    email_contato = st.text_input("E-mail para contato", key=f"em_{st.session_state.form_id}")
    nome_time = st.text_input("Nome do Time", "MEU TIME", key=f"nt_{st.session_state.form_id}")
    
    escudo = st.file_uploader("Escudo do Time", type=["png", "jpg"], key=f"esc_{st.session_state.form_id}")
    if escudo: st.image(escudo, width=80)
    
    st.markdown("---")
    formacao = st.selectbox("Formação Tática", ["4-5-1", "3-4-3", "4-4-2", "4-3-3", "3-5-2"], key=f"f_{st.session_state.form_id}")

config_form = {
    "4-5-1": {"ZAG": 2, "LAT": 2, "MEI": 5, "ATA": 1},
    "3-4-3": {"ZAG": 3, "LAT": 2, "MEI": 2, "ATA": 3},
    "4-4-2": {"ZAG": 2, "LAT": 2, "MEI": 4, "ATA": 2},
    "4-3-3": {"ZAG": 2, "LAT": 2, "MEI": 3, "ATA": 3},
    "3-5-2": {"ZAG": 3, "LAT": 2, "MEI": 3, "ATA": 2}
}
conf = config_form[formacao]

def seletor_smart(label, df_base, key_id):
    u_key = f"{key_id}_{st.session_state.form_id}"
    v_atual = get_val(st.session_state.escolhas.get(key_id, {}))
    # Filtro de duplicidade (pelo Nome)
    outros = [v['Name'] if 'Name' in v else v['NAME'] for k, v in st.session_state.escolhas.items() if v is not None and k != key_id]
    
    df_f = df_base[(df_base.apply(get_val, axis=1) <= (saldo + v_atual))]
    name_col = 'Name' if 'Name' in df_base.columns else 'NAME'
    df_f = df_f[~df_f[name_col].isin(outros)]
    
    ov_col = 'Overall' if 'Overall' in df_base.columns else 'overall'
    opcoes = [None] + df_f.sort_values(ov_col, ascending=False).to_dict('records')
    
    sel = st.selectbox(label, opcoes, format_func=format_func, key=u_key)
    if st.session_state.escolhas.get(key_id) != sel:
        st.session_state.escolhas[key_id] = sel
        st.rerun()
    return sel

col1, col2 = st.columns([2, 1])
elenco_completo = []

with col1:
    st.subheader(f"Campo de Jogo ({formacao})")
    g = seletor_smart("🧤 Goleiro", data['GK'], "gk_t")
    if g: elenco_completo.append({**g, "CAT": "TITULAR", "POS_ESC": "GK"})

    for i in range(conf["ZAG"]):
        s = seletor_smart(f"🛡️ Zagueiro {i+1}", data['DF'], f"zag_{i}")
        if s: elenco_completo.append({**s, "CAT": "TITULAR", "POS_ESC": "ZAG"})
        
    for i in range(conf["LAT"]):
        s = seletor_smart(f"🏃 Lateral {i+1}", pd.concat([data['DF'], data['MF']]), f"lat_{i}")
        if s: elenco_completo.append({**s, "CAT": "TITULAR", "POS_ESC": "LAT"})

    for i in range(conf["MEI"]):
        s = seletor_smart(f"🎯 Meio Campo {i+1}", data['MF'], f"mei_{i}")
        if s: elenco_completo.append({**s, "CAT": "TITULAR", "POS_ESC": "MEI"})

    for i in range(conf["ATA"]):
        s = seletor_smart(f"🚀 Atacante {i+1}", data['FW'], f"ata_{i}")
        if s: elenco_completo.append({**s, "CAT": "TITULAR", "POS_ESC": "ATA"})

with col2:
    st.subheader("📋 Banco de Reservas")
    gr = seletor_smart("Goleiro Reserva", data['GK'], "gk_r")
    if gr: elenco_completo.append({**gr, "CAT": "RESERVA", "POS_ESC": "GK"})
    
    todos_res = pd.concat([data['DF'], data['MF'], data['FW']])
    for i in range(7):
        r = seletor_smart(f"Reserva {i+2}", todos_res, f"res_{i}")
        if r: elenco_completo.append({**r, "CAT": "RESERVA", "POS_ESC": "SUB"})

st.sidebar.metric("Orçamento", f"€{custo_atual:.0f}", f"Saldo: €{saldo:.0f}")

if st.button("🔄 Reiniciar Seleção", on_click=reset_callback): st.rerun()

# --- EXPORTAÇÃO ---
if st.sidebar.button("🚀 FINALIZAR E ENVIAR"):
    if not int1 or not int2 or len(elenco_completo) < 19:
        st.sidebar.error("Complete os dados e selecione os 19 jogadores!")
    else:
        try:
            # 1. GERAR PDF (ESTILO TV)
            pdf = FPDF()
            pdf.add_page()
            pdf.set_fill_color(30, 30, 30)
            pdf.rect(0, 0, 210, 40, 'F') # Header escuro
            
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Arial", 'B', 24)
            pdf.cell(190, 20, nome_time.upper(), ln=True, align='C')
            
            if escudo:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
                    tmp.write(escudo.getvalue()); tmp_path = tmp.name
                pdf.image(tmp_path, x=10, y=5, w=25)
                os.unlink(tmp_path)

            pdf.set_text_color(0, 0, 0)
            pdf.ln(25)
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, f"DUPLA: {int1} & {int2}", ln=True, align='C')
            pdf.ln(5)

            # Titulares
            pdf.set_fill_color(200, 200, 200)
            pdf.cell(0, 8, " ESCALAÇÃO TITULAR", ln=True, fill=True)
            pdf.set_font("Arial", size=11)
            for p in [x for x in elenco_completo if x['CAT'] == 'TITULAR']:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(95, 7, f"({p['POS_ESC']}) {n}", border=0)
                pdf.cell(95, 7, f"OV: {p.get('Overall', p.get('overall'))}", ln=True, align='R')

            pdf.ln(5)
            # Reservas
            pdf.cell(0, 8, " BANCO DE RESERVAS", ln=True, fill=True)
            for p in [x for x in elenco_completo if x['CAT'] == 'RESERVA']:
                n = str(p.get('Name', p.get('NAME'))).encode('ascii', 'ignore').decode('ascii')
                pdf.cell(95, 7, f"   {n}", border=0)
                pdf.cell(95, 7, f"OV: {p.get('Overall', p.get('overall'))}", ln=True, align='R')
            
            pdf_out = pdf.output(dest='S').encode('latin-1')

            # 2. GERAR CSV DO JOGO (PADRÃO MASTER LIGA)
            df_csv = pd.DataFrame(elenco_completo).drop(columns=['CAT', 'POS_ESC'], errors='ignore')
            csv_buffer = StringIO()
            df_csv.to_csv(csv_buffer, sep=';', index=False)
            csv_out = csv_buffer.getvalue()

            # 3. ENVIAR E-MAIL COM 2 ANEXOS
            msg = MIMEMultipart()
            msg['From'], msg['To'] = EMAIL_REMETENTE, EMAIL_DESTINO
            msg['Subject'] = f"Elenco Confirmado: {nome_time}"
            msg.attach(MIMEText(f"Inscrição de {int1} e {int2}.\nSeguem anexos o PDF para divulgação e o CSV para o jogo.", 'plain'))

            # Anexo PDF
            p1 = MIMEBase('application', 'octet-stream')
            p1.set_payload(pdf_out); encoders.encode_base64(p1)
            p1.add_header('Content-Disposition', f'attachment; filename="{nome_time}_TV.pdf"'); msg.attach(p1)

            # Anexo CSV
            p2 = MIMEBase('application', 'octet-stream')
            p2.set_payload(csv_out.encode('utf-8')); encoders.encode_base64(p2)
            p2.add_header('Content-Disposition', f'attachment; filename="{nome_time}_Geral.csv"'); msg.attach(p2)
            
            # Anexo Escudo Avulso
            if escudo:
                p3 = MIMEBase('image', 'png')
                p3.set_payload(escudo.getvalue()); encoders.encode_base64(p3)
                p3.add_header('Content-Disposition', f'attachment; filename="escudo.png"'); msg.attach(p3)

            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_REMETENTE, SENHA_APP)
                server.send_message(msg)
            
            st.success("✅ Tudo pronto! Verifique o e-mail com os dois arquivos.")
            
        except Exception as e:
            st.error(f"Erro na exportação: {e}")
