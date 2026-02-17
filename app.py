import streamlit as st
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os

# --- CONFIGURAÇÕES BÁSICAS ---
st.set_page_config(page_title="Diagnóstico PES 2013", layout="wide")

# Suas credenciais
EMAIL_REMETENTE = "leallimagui@gmail.com" 
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"

# --- CARREGAMENTO LEVE ---
@st.cache_data
def load_data():
    if not os.path.exists("jogadores.xlsx"): return None
    return pd.read_excel("jogadores.xlsx", sheet_name=None) # Carrega todas as abas

data_dict = load_data()

# --- ESTADO DA SESSÃO ---
if 'selecoes' not in st.session_state: st.session_state.selecoes = {}

# --- INTERFACE DE STATUS (SEMPRE VISÍVEL) ---
st.title("🛠️ Painel de Diagnóstico de Inscrição")

with st.sidebar:
    st.header("📋 Requisitos de Envio")
    
    # Validação Técnica 1: Nomes
    nome1 = st.text_input("Nome Técnico 1", key="t1")
    nome2 = st.text_input("Nome Técnico 2", key="t2")
    time = st.text_input("Nome do Time", "MEU TIME", key="tm")
    
    # Validação Técnica 2: Jogadores
    qtd = len([p for p in st.session_state.selecoes.values() if p])
    
    st.write("---")
    # Mostra o que falta em tempo real
    check_nomes = "✅ Nomes OK" if (nome1 and nome2) else "❌ Faltam nomes dos técnicos"
    check_jogadores = f"✅ Elenco OK ({qtd}/16)" if qtd >= 16 else f"❌ Faltam jogadores ({qtd}/16)"
    
    st.write(check_nomes)
    st.write(check_jogadores)

# --- SELEÇÃO SIMPLIFICADA (Para teste rápido) ---
if data_dict:
    st.subheader("Monte seu time rápido para testar")
    # Criamos 16 seletores automáticos só para você preencher e testar o envio
    tabs = list(data_dict.keys())
    for i in range(16):
        aba = tabs[i % len(tabs)]
        df = data_dict[aba]
        # Pega os primeiros 50 nomes da aba para o seletor ficar leve
        opcoes = [None] + df['NAME'].head(50).tolist()
        res = st.selectbox(f"Jogador {i+1}", opcoes, key=f"sel_{i}")
        if res:
            st.session_state.selecoes[f"p_{i}"] = res
else:
    st.error("Arquivo jogadores.xlsx não encontrado!")

st.write("---")

# --- O BOTÃO DE ENVIO COM FEEDBACK FORÇADO ---
if st.button("🚀 CLIQUE AQUI PARA TESTAR O ENVIO AGORA", type="primary", use_container_width=True):
    # Forçamos a exibição de uma mensagem imediata
    st.info("Iniciando processo de envio... verificando conexão com Gmail.")
    
    if not (nome1 and nome2):
        st.error("Erro: Você não preencheu os nomes dos técnicos na barra lateral.")
    elif qtd < 16:
        st.warning(f"Erro: Você só selecionou {qtd} jogadores. O sistema exige 16.")
    else:
        try:
            # Criando corpo do email
            corpo = f"Inscrição do Time: {time}\nTécnicos: {nome1} e {nome2}\n\nJogadores:\n"
            for k, v in st.session_state.selecoes.items():
                corpo += f"- {v}\n"
            
            msg = MIMEMultipart()
            msg['Subject'] = f"TESTE PES: {time}"
            msg['From'] = EMAIL_REMETENTE
            msg['To'] = EMAIL_DESTINO
            msg.attach(MIMEText(corpo, 'plain'))
            
            # Conexão
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_REMETENTE, SENHA_APP)
                server.send_message(msg)
            
            st.success("✅ O EMAIL FOI ENVIADO! Verifique sua caixa de entrada agora.")
            st.balloons()
            
        except Exception as e:
            st.error(f"❌ FALHA NO ENVIO: {str(e)}")
            st.write("Dica: Verifique se sua 'Senha de App' do Google ainda é válida.")
