from nicegui import ui, app
import pandas as pd
from fpdf import FPDF
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import os
import re

# --- SUAS CONFIGURAÇÕES ---
EMAIL_REMETENTE = "leallimagui@gmail.com"
SENHA_APP = "nmrytcivcuidhryn" 
EMAIL_DESTINO = "leallimagui@gmail.com"
ORCAMENTO_MAX = 2000.0

# Configura pasta de imagens estáticas
app.add_static_files('/static', 'static')

# Lista de camisas (apontando para a pasta static)
OPCOES_CAMISAS = {f"Padrão {i}": f"static/uniforme{i}.jpg" for i in range(1, 8)}

# --- FUNÇÕES DE DADOS (Carrega 1x só) ---
def clean_price(val):
    if pd.isna(val) or val == '': return 0.0
    s = str(val)
    s = re.sub(r'[^\d.,]', '', s)
    if not s: return 0.0
    return float(s.replace(',', '.'))

# Cache em memória
CACHE = {"df": None}

def get_data():
    if CACHE["df"] is not None:
        return CACHE["df"]
    
    file_path = "jogadores.xlsx"
    if not os.path.exists(file_path):
        ui.notify("Erro: jogadores.xlsx não encontrado!", type='negative')
        return {}

    dados = {}
    cols_ui = ['INDEX', 'NAME', 'MARKET PRICE', 'OVERALL']
    
    for tab in ['GK', 'DF', 'MF', 'FW']:
        try:
            df = pd.read_excel(file_path, sheet_name=tab)
            df.columns = df.columns.str.strip().str.upper()
            df.rename(columns={df.columns[0]: 'INDEX'}, inplace=True)
            
            col_price = next((c for c in df.columns if 'PRICE' in c or 'VALUE' in c), None)
            if col_price:
                df['MARKET PRICE'] = df[col_price].apply(clean_price)
            else:
                df['MARKET PRICE'] = 0.0
            
            if 'OVERALL' not in df.columns and len(df.columns) > 2:
                df['OVERALL'] = df.iloc[:, 2] 
            
            df = df[[c for c in cols_ui if c in df.columns]].copy()
            df['label'] = df.apply(lambda x: f"{x['NAME']} (OV: {x.get('OVERALL', '?')} | €{x['MARKET PRICE']:.1f})", axis=1)
            
            dados[tab] = df.to_dict('records')
        except Exception as e:
            print(f"Erro na aba {tab}: {e}")
            dados[tab] = []
            
    CACHE["df"] = dados
    return dados

data_source = get_data()

# --- ESTADO DO APP ---
class State:
    def __init__(self):
        self.jogador1 = ""
        self.jogador2 = ""
        self.time_nome = "MEU TIME"
        self.email = ""
        self.formacao = "4-3-3"
        self.filtro_preco = 2000.0
        self.kit_titular = {"modelo": "Padrão 1", "c1": "#FF0000", "c2": "#FFFFFF", "c3": "#000000", "calcao": "#FFFFFF", "meia": "#FFFFFF"}
        self.kit_reserva = {"modelo": "Padrão 2", "c1": "#0000FF", "c2": "#FFFFFF", "c3": "#000000", "calcao": "#000000", "meia": "#000000"}
        self.selecoes = {} 
        self.numeros = {} 

state = State()

# --- INTERFACE ---
@ui.page('/')
def main_page():
    ui.add_head_html('<style>body { background-color: #f0f2f5; }</style>')
    
    with ui.column().classes('w-full max-w-6xl mx-auto p-4'):
        ui.label('⚽ SQUAD BUILDER PRO').classes('text-4xl font-bold text-slate-800 mb-4')
        
        # --- PAINEL CADASTRO ---
        with ui.expansion('📋 Cadastro & Uniformes', icon='assignment', value=True).classes('w-full bg-white shadow-sm rounded-lg'):
            with ui.column().classes('p-4 w-full gap-4'):
                with ui.grid(columns=2).classes('w-full gap-4'):
                    ui.input('Jogador 1', on_change=lambda e: setattr(state, 'jogador1', e.value))
                    ui.input('Jogador 2', on_change=lambda e: setattr(state, 'jogador2', e.value))
                    ui.input('Nome do Time', value='MEU TIME', on_change=lambda e: setattr(state, 'time_nome', e.value))
                    ui.input('E-mail', on_change=lambda e: setattr(state, 'email', e.value))
                
                ui.upload(label='Upload Escudo', auto_upload=True, on_upload=lambda e: ui.notify('Escudo carregado!'))
                ui.separator()
                
                # --- UNIFORMES ---
                with ui.tabs().classes('w-full') as tabs:
                    tab_home = ui.tab('🏠 Titular')
                    tab_away = ui.tab('✈️ Reserva')
                
                with ui.tab_panels(tabs, value=tab_home).classes('w-full'):
                    def render_kit_selector(kit_state):
                        with ui.column().classes('w-full'):
                            ui.label('Escolha o Modelo:').classes('font-bold')
                            # Grid de 7 imagens
                            with ui.row().classes('flex-wrap gap-2 justify-center'):
                                for nome, path in OPCOES_CAMISAS.items():
                                    # Card clicável
                                    with ui.card().classes('w-[130px] p-1 cursor-pointer no-shadow border hover:border-blue-500 transition') as card:
                                        ui.image(path).classes('w-full h-auto rounded')
                                        btn = ui.button('Selecionar', on_click=lambda n=nome, k=kit_state, c=card: select_kit(n, k)).props('sm w-full flat')
                                        
                                        def update_card(k=kit_state, n=nome, b=btn, c=card):
                                            if k['modelo'] == n:
                                                b.text = '✅'
                                                b.props('color=green')
                                                c.classes('ring-2 ring-green-500', remove='border')
                                            else:
                                                b.text = 'Usar'
                                                b.props('color=primary')
                                                c.classes('border', remove='ring-2 ring-green-500')
                                        ui.timer(0.5, update_card)

                            def select_kit(nome, kit):
                                kit['modelo'] = nome
                            
                            ui.separator().classes('my-2')
                            with ui.row().classes('w-full gap-4'):
                                with ui.column():
                                    ui.label('Principal')
                                    ui.color_input(value=kit_state['c1'], on_change=lambda e: kit_state.update({'c1': e.value})).props('filled')
                                with ui.column():
                                    ui.label('Secundária')
                                    ui.color_input(value=kit_state['c2'], on_change=lambda e: kit_state.update({'c2': e.value})).props('filled')
                                with ui.column():
                                    ui.label('Calção')
                                    ui.color_input(value=kit_state['calcao'], on_change=lambda e: kit_state.update({'calcao': e.value})).props('filled')
                                with ui.column():
                                    ui.label('Meias')
                                    ui.color_input(value=kit_state['meia'], on_change=lambda e: kit_state.update({'meia': e.value})).props('filled')

                    with ui.tab_panel(tab_home): render_kit_selector(state.kit_titular)
                    with ui.tab_panel(tab_away): render_kit_selector(state.kit_reserva)

        # --- PAINEL CONTROLE ---
        with ui.card().classes('w-full sticky top-0 z-50 bg-white/95 backdrop-blur shadow-md'):
            with ui.row().classes('w-full items-center gap-4 p-2'):
                ui.select(['4-3-3', '4-4-2', '3-5-2', '4-5-1', '3-4-3'], value='4-3-3', label='Formação', 
                          on_change=lambda e: [setattr(state, 'formacao', e.value), render_players.refresh()]).classes('w-32')
                ui.number(label='Max €', value=2000.0, step=100, 
                          on_change=lambda e: [setattr(state, 'filtro_preco', e.value), render_players.refresh()]).classes('w-32')
                
                with ui.column().classes('flex-grow'):
                    label_saldo = ui.label()
                    progress = ui.linear_progress(value=0).props('size=20px rounded color=green track-color=grey-3')
                    def update_finance():
                        gasto = sum(p['MARKET PRICE'] for p in state.selecoes.values() if p)
                        saldo_atual = ORCAMENTO_MAX - gasto
                        perc = min(gasto / ORCAMENTO_MAX, 1.0)
                        label_saldo.text = f"Gasto: €{gasto:.0f} | Saldo: €{saldo_atual:.0f}"
                        progress.value = perc
                        progress.props(f'color={"red" if perc > 0.9 else "green"}')
                    ui.timer(0.2, update_finance)

        # --- JOGADORES ---
        @ui.refreshable
        def render_players():
            formacao_map = {
                "4-5-1": {"Z":2,"L":2,"M":5,"A":1}, "3-4-3": {"Z":3,"L":2,"M":2,"A":3},
                "4-4-2": {"Z":2,"L":2,"M":4,"A":2}, "4-3-3": {"Z":2,"L":2,"M":3,"A":3},
                "3-5-2": {"Z":3,"L":2,"M":3,"A":2}
            }
            cfg = formacao_map.get(state.formacao, formacao_map["4-3-3"])
            
            def player_select(pos_label, key, data_list):
                with ui.card().classes('w-full p-2 gap-1 bg-slate-50 border'):
                    ui.label(pos_label).classes('text-xs font-bold text-gray-500 uppercase')
                    with ui.row().classes('w-full no-wrap items-center gap-2'):
                        opts = [p for p in data_list if p['MARKET PRICE'] <= state.filtro_preco]
                        ui.select(options=opts, label='Escolha...', with_input=True,
                                  option_label='label', value=state.selecoes.get(key)) \
                                  .props('dense options-dense').classes('w-full') \
                                  .on_value_change(lambda e, k=key: state.selecoes.update({k: e.value}))
                        ui.input(label='#', value=state.numeros.get(key, ''), 
                                 on_change=lambda e, k=key: state.numeros.update({k: e.value})).props('dense').classes('w-12')

            with ui.row().classes('w-full gap-6'):
                with ui.column().classes('flex-1'):
                    ui.label('TITULARES').classes('text-xl font-bold mb-2')
                    player_select("Goleiro", "gk_tit", data_source['GK'])
                    for i in range(cfg['Z']): player_select(f"Zagueiro {i+1}", f"zag_{i}", data_source['DF'])
                    for i in range(cfg['L']): player_select(f"Lateral {i+1}", f"lat_{i}", data_source['DF'] + data_source['MF'])
                    for i in range(cfg['M']): player_select(f"Meio {i+1}", f"mei_{i}", data_source['MF'])
                    for i in range(cfg['A']): player_select(f"Atacante {i+1}", f"ata_{i}", data_source['FW'])

                with ui.column().classes('flex-1'):
                    ui.label('RESERVAS').classes('text-xl font-bold mb-2')
                    player_select("Goleiro Res.", "gk_res", data_source['GK'])
                    todos = data_source['DF'] + data_source['MF'] + data_source['FW']
                    for i in range(4): player_select(f"Reserva {i+1}", f"res_{i}", todos)

        render_players()

        # --- BOTÃO ENVIAR ---
        async def enviar_inscricao():
            erros = []
            if not state.jogador1: erros.append("Jogador 1")
            if not state.email: erros.append("E-mail")
            if len(state.selecoes) < 16: erros.append(f"Faltam {16 - len(state.selecoes)} jogadores")
            
            if erros:
                ui.notify(f"Faltando: {', '.join(erros)}", type='negative')
                return

            notification = ui.notify('Gerando PDF e enviando...', type='info', spinner=True, timeout=0)
            try:
                await app.io_bound(processar_envio)
                notification.dismiss()
                ui.notify('✅ Inscrição Enviada com Sucesso!', type='positive', close_button=True)
            except Exception as e:
                notification.dismiss()
                ui.notify(f"Erro: {str(e)}", type='negative', close_button=True)

        def processar_envio():
            txt = f"TIME: {state.time_nome}\nJOGADORES: {state.jogador1} & {state.jogador2}\n"
            txt += "ELENCO:\n"
            for k, p in state.selecoes.items():
                if p: 
                    num = state.numeros.get(k, "")
                    txt += f"{k}: {p['NAME']} (ID: {p['INDEX']}) - Camisa: {num}\n"
            
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Inscricao: {state.time_nome}", ln=1, align="C")
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 10, txt)
            
            msg = MIMEMultipart()
            msg['From'] = EMAIL_REMETENTE
            msg['To'] = EMAIL_DESTINO
            msg['Subject'] = f"Inscricao NiceGUI: {state.time_nome}"
            msg.attach(MIMEText(txt, 'plain'))
            
            att = MIMEBase('application', 'pdf')
            att.set_payload(pdf.output(dest='S').encode('latin-1'))
            encoders.encode_base64(att)
            att.add_header('Content-Disposition', 'attachment; filename="elenco.pdf"')
            msg.attach(att)
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
                s.login(EMAIL_REMETENTE, SENHA_APP)
                s.send_message(msg)

        ui.separator()
        ui.button('✅ ENVIAR INSCRIÇÃO', on_click=enviar_inscricao).props('size=lg color=green w-full')

ui.run(title='Squad Builder', language='pt-BR', port=8080)
