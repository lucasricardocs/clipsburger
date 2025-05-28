import streamlit as st
import gspread
import pandas as pd
import altair as alt
import numpy as np
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from gspread.exceptions import SpreadsheetNotFound
import warnings
import matplotlib.pyplot as plt
import calplot
import os # Adicionado para manipulação de caminhos

# Suprimir warnings específicos do pandas
warnings.filterwarnings("ignore", category=FutureWarning, message=".*observed=False.*")

# --- Configurações Globais e Constantes ---
SPREADSHEET_ID = "1NTScbiIna-iE7roQ9XBdjUOssRihTFFby4INAAQNXTg"
WORKSHEET_NAME = "Vendas"
HEATMAP_FILENAME = "/home/ubuntu/sales_heatmap.png" # Caminho para salvar o heatmap
LOGO_URL = "https://raw.githubusercontent.com/lucasricardocs/clipsburger/main/logo.png" # URL da logo no GitHub

# Configuração da página Streamlit
st.set_page_config(page_title="Sistema Financeiro - Clips Burger", layout="wide", page_icon="🍔")

# Configuração de tema para gráficos mais bonitos
alt.data_transformers.enable("json")

# Paleta de cores otimizada para modo escuro
CORES_MODO_ESCURO = ["#4c78a8", "#54a24b", "#f58518", "#e45756", "#72b7b2", "#ff9da6", "#9d755d", "#bab0ac"]

# Define a ordem correta dos dias da semana e meses
dias_semana_ordem = ["Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira", "Sexta-feira", "Sábado", "Domingo"]
meses_ordem = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

# CSS para melhorar a aparência
def inject_css():
    st.markdown("""
    <style>
    .stSelectbox label, .stNumberInput label {
        font-weight: bold;
        color: #4c78a8;
    }
    
    .stNumberInput input::placeholder {
        color: #888;
        font-style: italic;
    }
    
    .stButton > button {
        height: 3rem;
        font-size: 1.2rem;
        font-weight: bold;
        width: 100%;
    }
    
    .element-container {
        margin-bottom: 0.5rem;
    }
    
    .stMetric {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
        min-height: 120px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Dashboard Premium Styles */
    .stApp {
        background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
    }
    
    /* Grid para gráficos do dashboard premium */
    .premium-charts-grid {
        display: grid;
        grid-template-columns: 2fr 1fr;
        gap: 2rem;
        margin: 2rem 0;
    }
    
    .premium-chart-full {
        grid-column: 1 / -1;
        margin: 2rem 0;
    }

    /* Estilo para a logo com aura */
    .logo-container {
        display: flex;
        align-items: center;
        gap: 15px; /* Espaço entre a logo e o título */
        margin-bottom: 20px;
    }
    .logo-image {
        width: 60px; /* Tamanho da logo */
        height: auto;
        filter: drop-shadow(0 0 10px rgba(76, 120, 168, 0.8)); /* Aura azul vibrante */
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% {
            filter: drop-shadow(0 0 8px rgba(76, 120, 168, 0.6));
        }
        50% {
            filter: drop-shadow(0 0 15px rgba(76, 120, 168, 1));
        }
        100% {
            filter: drop-shadow(0 0 8px rgba(76, 120, 168, 0.6));
        }
    }

    /* Responsividade */
    @media (max-width: 992px) { /* Ajustes para tablets e telas menores */
        .premium-charts-grid {
            grid-template-columns: 1fr; /* Coluna única */
        }
        .stMetric {
            padding: 0.8rem;
            min-height: 110px;
        }
        .logo-container h1 {
            font-size: 1.9rem;
        }
    }

    @media (max-width: 768px) { /* Ajustes para mobile */
        .logo-image {
            width: 45px; /* Logo menor */
        }
        .logo-container h1 {
            font-size: 1.6rem; /* Título menor */
        }
        .stMetric {
            min-height: 90px; /* Métricas menores */
            padding: 0.6rem;
        }
        .stTabs [role="tab"] { /* Reduz padding das abas */
            padding: 0.5rem 0.8rem;
        }
        .stDateInput, .stNumberInput, .stSelectbox, .stMultiselect { /* Melhora espaçamento dos inputs */
             margin-bottom: 0.8rem;
        }
        /* Ajusta tabela DRE para telas pequenas */
        div[style*="font-family: 'Segoe UI'"] table {
            font-size: 13px; /* Reduz fonte da tabela DRE */
        }
        div[style*="font-family: 'Segoe UI'"] h3 {
            font-size: 1.1rem;
        }
         div[style*="font-family: 'Segoe UI'"] p {
            font-size: 13px;
        }
    }

    @media (max-width: 480px) { /* Ajustes finos para telas muito pequenas */
        .logo-container h1 {
            font-size: 1.4rem;
        }
         .stMetric > div > div {
             font-size: 1.1rem !important; /* Tenta forçar redução do valor da métrica */
         }
         .stMetric label {
             font-size: 0.8rem !important; /* Tenta forçar redução do label da métrica */
         }
         .stButton > button {
            font-size: 1rem;
            height: 2.5rem;
         }
    }
    </style>
    """, unsafe_allow_html=True)

inject_css()

# --- Funções de Cache para Acesso ao Google Sheets (Nova versão robusta) ---
@st.cache_resource(ttl=600) # Cache por 10 minutos
def get_google_auth(_ttl=600): # Adicionado _ttl para forçar re-execução se necessário
    """Autoriza o acesso ao Google Sheets de forma robusta e retorna o cliente gspread."""
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/spreadsheets.readonly",
        "https://www.googleapis.com/auth/drive.readonly"
    ]
    
    # Tenta obter credenciais do st.secrets
    credentials_dict = None
    if hasattr(st, 'secrets') and "google_credentials" in st.secrets:
        credentials_dict = st.secrets["google_credentials"]
    
    # Verifica se as credenciais foram encontradas e são válidas
    if not credentials_dict or not isinstance(credentials_dict, dict):
        st.error(
            "**Erro de Credenciais do Google:** As credenciais não foram encontradas ou estão mal formatadas em `st.secrets`.\n\n" 
            "**Como configurar:**\n" 
            "1. Crie um arquivo chamado `secrets.toml` na pasta `.streamlit` do seu projeto.\n" 
            "2. Adicione o seguinte conteúdo ao arquivo, substituindo pelos valores da sua conta de serviço do Google Cloud:\n" 
            "```toml\n" 
            "[google_credentials]\n" 
            "type = \"service_account\"\n" 
            "project_id = \"SEU_PROJECT_ID\"\n" 
            "private_key_id = \"SUA_PRIVATE_KEY_ID\"\n" 
            "private_key = \"-----BEGIN PRIVATE KEY-----\nSUA_PRIVATE_KEY\n-----END PRIVATE KEY-----\"\n" 
            "client_email = \"SEU_CLIENT_EMAIL\"\n" 
            "client_id = \"SEU_CLIENT_ID\"\n" 
            "auth_uri = \"https://accounts.google.com/o/oauth2/auth\"\n" 
            "token_uri = \"https://oauth2.googleapis.com/token\"\n" 
            "auth_provider_x509_cert_url = \"https://www.googleapis.com/oauth2/v1/certs\"\n" 
            "client_x509_cert_url = \"URL_DO_SEU_CERTIFICADO_CLIENT_X509\"\n" 
            "```\n" 
            "3. Certifique-se de que a conta de serviço tem permissão para acessar a Planilha Google desejada.\n" 
            "4. Reinicie a aplicação Streamlit."
        )
        return None

    # Verifica se as chaves essenciais estão presentes
    required_keys = ["type", "project_id", "private_key_id", "private_key", "client_email", "client_id"]
    missing_keys = [key for key in required_keys if key not in credentials_dict or not credentials_dict[key]]
    if missing_keys:
        st.error(f"**Erro de Credenciais do Google:** As seguintes chaves estão em falta ou vazias nas credenciais em `st.secrets`: {", ".join(missing_keys)}. Verifique o arquivo `secrets.toml`.")
        return None

    try:
        creds = Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)
        gc = gspread.authorize(creds)
        # Teste rápido para verificar se a autenticação funciona (opcional, mas recomendado)
        # Tenta listar planilhas acessíveis para confirmar a autenticação
        gc.list_spreadsheet_files() 
        # Removido st.info de sucesso para não poluir a interface final
        return gc
    except ValueError as ve:
        st.error(f"**Erro de Credenciais do Google:** Formato inválido nas credenciais. Detalhes: {ve}")
        return None
    except Exception as e:
        # Captura erros genéricos de autenticação ou API
        st.error(f"**Erro de Autenticação com Google:** Não foi possível conectar ao Google Sheets. Verifique as permissões da conta de serviço e a conexão de rede. Detalhes: {e}")
        return None

@st.cache_resource(ttl=600)
def get_worksheet(_ttl=600):
    """Retorna o objeto worksheet da planilha especificada."""
    gc = get_google_auth() # Chama a nova função de autenticação
    if gc:
        try:
            spreadsheet = gc.open_by_key(SPREADSHEET_ID)
            worksheet = spreadsheet.worksheet(WORKSHEET_NAME)
            return worksheet
        except SpreadsheetNotFound:
            st.error(f"**Erro:** Planilha com ID `{SPREADSHEET_ID}` não encontrada ou sem permissão de acesso. Verifique o ID e as permissões da conta de serviço.")
            return None
        except Exception as e:
            st.error(f"**Erro ao Acessar Planilha:** Não foi possível abrir a planilha '{WORKSHEET_NAME}'. Detalhes: {e}")
            return None
    # Se gc for None, o erro já foi mostrado por get_google_auth()
    return None

@st.cache_data(ttl=300) # Cache de dados por 5 minutos
def read_sales_data(_ttl=300):
    """Lê todos os registros da planilha de vendas e retorna como DataFrame."""
    worksheet = get_worksheet()
    if worksheet:
        try:
            rows = worksheet.get_all_records()
            if not rows:
                # st.info("A planilha de vendas está vazia.") # Comentado para interface mais limpa
                return pd.DataFrame()

            df = pd.DataFrame(rows)
            
            # Garante que colunas de valor existem e são numéricas
            for col in ["Cartão", "Dinheiro", "Pix"]:
                if col in df.columns:
                    # Tenta converter para numérico, substituindo vírgulas por pontos se necessário
                    if df[col].dtype == 'object':
                         df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
                else:
                    df[col] = 0 # Cria a coluna com zeros se não existir
            
            # Garante que a coluna Data existe
            if "Data" not in df.columns:
                st.warning("Coluna 'Data' não encontrada na planilha. As análises temporais podem ser afetadas.")
                # Cria uma coluna 'Data' vazia para evitar erros posteriores, mas idealmente deveria existir
                df["Data"] = pd.NaT 
            else:
                 # Tenta converter a coluna 'Data' para datetime (mais robusto)
                original_data_type = df["Data"].dtype
                try:
                    # Primeiro tenta formato DD/MM/YYYY ou DD-MM-YYYY
                    df["Data"] = pd.to_datetime(df["Data"], format='%d/%m/%Y', errors='coerce')
                    if df["Data"].isnull().all(): # Se falhou, tenta DD-MM-YYYY
                        df["Data"] = pd.to_datetime(df_input["Data"], format='%d-%m-%Y', errors='coerce')
                    if df["Data"].isnull().all(): # Se falhou, tenta inferir
                         df["Data"] = pd.to_datetime(df_input["Data"], errors='coerce', dayfirst=True)
                    if df["Data"].isnull().all(): # Última tentativa, formato americano
                         df["Data"] = pd.to_datetime(df_input["Data"], errors='coerce')

                    # Se ainda assim falhar para algumas linhas, reporta mas continua
                    if df["Data"].isnull().any():
                        st.warning(f"Algumas datas na coluna 'Data' não puderam ser convertidas para o formato datetime. Verifique a planilha.")

                except Exception as e:
                    st.error(f"Erro crítico ao converter a coluna 'Data' para datetime: {e}. Tipo original: {original_data_type}. Verifique o formato das datas na planilha (ex: DD/MM/YYYY).")
                    # Retorna dataframe original para evitar quebrar a aplicação
                    return df_input 

            return df
        except Exception as e:
            st.error(f"**Erro ao Ler Dados:** Não foi possível ler ou processar os dados da planilha. Detalhes: {e}")
            return pd.DataFrame() # Retorna DataFrame vazio em caso de erro
    # Se worksheet for None, o erro já foi mostrado por get_worksheet()
    return pd.DataFrame()

# --- Funções de Manipulação de Dados ---
def add_data_to_sheet(date, cartao, dinheiro, pix, worksheet_obj):
    """Adiciona uma nova linha de dados à planilha Google Sheets."""
    if worksheet_obj is None:
        st.error("**Erro:** Não foi possível acessar a planilha para adicionar dados. Verifique a conexão e as credenciais.")
        st.warning("Os dados não foram salvos.")
        return False
    try:
        # Limpa e converte os valores
        cartao_str = str(cartao).replace(',', '.') if cartao else '0'
        dinheiro_str = str(dinheiro).replace(',', '.') if dinheiro else '0'
        pix_str = str(pix).replace(',', '.') if pix else '0'
        
        cartao_val = float(cartao_str)
        dinheiro_val = float(dinheiro_str)
        pix_val = float(pix_str)
        
        # Formata a data como string DD/MM/YYYY para consistência na planilha
        date_str = date.strftime("%d/%m/%Y")

        new_row = [date_str, cartao_val, dinheiro_val, pix_val]
        worksheet_obj.append_row(new_row, value_input_option='USER_ENTERED') # Garante formatação correta
        st.success("Dados registrados com sucesso na planilha! ✅")
        # Limpa o cache de leitura para refletir a adição
        read_sales_data.clear()
        process_data.clear() # Limpa cache de processamento também
        return True
    except ValueError as ve:
        st.error(f"**Erro de Valor:** Não foi possível converter os valores inseridos (Cartão, Dinheiro, Pix) para números. Verifique se contêm apenas números e ponto decimal (ex: 123.45). Detalhes: {ve}")
        return False
    except Exception as e:
        st.error(f"**Erro ao Adicionar Dados:** Não foi possível salvar os dados na planilha. Detalhes: {e}")
        return False

@st.cache_data(ttl=300)
def process_data(df_input):
    """Processa e prepara os dados de vendas para análise."""
    if df_input is None or df_input.empty:
        # Retorna um DataFrame vazio estruturado se a entrada for vazia
        cols = ["Data", "Cartão", "Dinheiro", "Pix", "Total", "Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
        return pd.DataFrame(columns=cols)
        
    df = df_input.copy()
    
    # --- 1. Garantir Colunas Numéricas Essenciais ---
    numeric_cols = ["Cartão", "Dinheiro", "Pix"]
    for col in numeric_cols:
        if col in df.columns:
             # Conversão robusta para numérico
            if df[col].dtype == 'object':
                 df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        else:
            df[col] = 0 # Cria coluna com zeros se não existir

    # --- 2. Calcular Total ---
    df["Total"] = df[numeric_cols].sum(axis=1)

    # --- 3. Processar Coluna de Data ---
    date_derived_cols = ["Ano", "Mês", "MêsNome", "AnoMês", "DataFormatada", "DiaSemana", "DiaDoMes"]
    if "Data" in df.columns and not pd.api.types.is_datetime64_any_dtype(df["Data"]):
         # Se a coluna Data existe mas não é datetime (pode ter falhado na leitura)
         # Tenta converter novamente aqui
        try:
            df["Data"] = pd.to_datetime(df["Data"], errors='coerce', dayfirst=True)
            if df["Data"].isnull().all(): # Se ainda falhar, tenta sem dayfirst
                df["Data"] = pd.to_datetime(df_input["Data"], errors='coerce')
        except Exception:
            st.warning("Falha ao converter 'Data' durante o processamento. Análises temporais podem estar incorretas.")
            df["Data"] = pd.NaT # Define como NaT para evitar erros

    if "Data" in df.columns and pd.api.types.is_datetime64_any_dtype(df["Data"]):
        # Remove linhas onde a data é inválida (NaT) após a conversão
        df.dropna(subset=["Data"], inplace=True)
        
        if not df.empty:
            df["Ano"] = df["Data"].dt.year
            df["Mês"] = df["Data"].dt.month
            # Mapeia nome do mês em português
            df["MêsNome"] = df["Mês"].map(lambda x: meses_ordem[int(x)-1] if pd.notna(x) and 1 <= int(x) <= 12 else "Inválido")
            df["AnoMês"] = df["Data"].dt.strftime("%Y-%m")
            df["DataFormatada"] = df["Data"].dt.strftime("%d/%m/%Y")
            # Mapeia dia da semana em português
            day_map = {0: "Segunda-feira", 1: "Terça-feira", 2: "Quarta-feira", 3: "Quinta-feira", 4: "Sexta-feira", 5: "Sábado", 6: "Domingo"}
            df["DiaSemana"] = df["Data"].dt.dayofweek.map(day_map)
            df["DiaDoMes"] = df["Data"].dt.day

            # Garante que DiaSemana seja categórico com a ordem correta
            df["DiaSemana"] = pd.Categorical(df["DiaSemana"], categories=dias_semana_ordem, ordered=True)
        else:
             # Se o DataFrame ficou vazio após dropna, cria colunas derivadas vazias
            for col in date_derived_cols:
                df[col] = pd.NA
    else:
        # Se a coluna "Data" não existe ou não pôde ser convertida
        st.warning("Coluna 'Data' ausente ou inválida. Análises temporais não disponíveis.")
        for col in date_derived_cols:
            df[col] = pd.NA # Cria colunas vazias
            
    # Garante que todas as colunas esperadas existam, mesmo que vazias
    all_expected_cols = ["Data"] + numeric_cols + ["Total"] + date_derived_cols
    for col in all_expected_cols:
        if col not in df.columns:
            if col in numeric_cols + ["Total"]:
                 df[col] = 0.0
            elif col == "Data":
                 df[col] = pd.NaT
            else:
                 df[col] = pd.NA
                 
    return df[all_expected_cols] # Retorna com colunas na ordem esperada

# --- Funções de Gráficos Interativos em Altair (Ajustes para Responsividade) ---

def create_radial_plot(df):
    """Cria um gráfico radial plot (substituto do pizza) responsivo."""
    if df.empty or not any(col in df.columns for col in ["Cartão", "Dinheiro", "Pix"]):
        return None
    
    payment_data = pd.DataFrame({
        "Método": ["Cartão", "Dinheiro", "PIX"],
        "Valor": [df["Cartão"].sum(), df["Dinheiro"].sum(), df["Pix"].sum()]
    })
    payment_data = payment_data[payment_data["Valor"] > 0]
    
    if payment_data.empty:
        return None

    base = alt.Chart(payment_data).encode(
        theta=alt.Theta("Valor:Q", stack=True),
        radius=alt.Radius("Valor:Q", scale=alt.Scale(type="sqrt", zero=True, rangeMin=20)),
        color=alt.Color(
            "Método:N", 
            scale=alt.Scale(range=CORES_MODO_ESCURO[:len(payment_data)]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient="bottom",
                direction="horizontal",
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=100,
                padding=10
            )
        ),
        tooltip=[
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f")
        ]
    )

    radial_plot = base.mark_arc(
        innerRadius=20, 
        stroke="#FFFFFF", # Branco para contraste com fundo escuro
        strokeWidth=1.5
    ).properties(
        title=alt.TitleParams(
            text="Distribuição por Método de Pagamento", 
            fontSize=16,
            anchor="middle", # Centraliza o título
            dy=-10 # Ajusta posição vertical do título
        ),
        # Altura fixa, largura usa container
        height=350, 
    ).configure_view(
        stroke=None
    ).configure_title(
        color='white' # Cor do título
    ).configure_legend(
        titleColor='white', # Cor do título da legenda
        labelColor='white' # Cor dos labels da legenda
    ).configure(
        background="transparent" # Fundo transparente
    )

    # Usar use_container_width=True no st.altair_chart
    return radial_plot

def create_area_chart_with_gradient(df):
    """Cria gráfico de área com gradiente responsivo."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns or df["Data"].isnull().all():
        return None
    
    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data", "Total"], inplace=True)
    
    if df_sorted.empty:
        return None
    
    area_chart = alt.Chart(df_sorted).mark_area(
        interpolate="monotone",
        line={"color": CORES_MODO_ESCURO[0], "strokeWidth": 2},
        color=alt.Gradient(
            gradient="linear",
            stops=[
                alt.GradientStop(color=CORES_MODO_ESCURO[0], offset=0),
                alt.GradientStop(color="#1a1a2e", offset=1) # Gradiente para a cor de fundo
            ],
            x1=1, x2=1, y1=1, y2=0
        )
    ).encode(
        x=alt.X(
            "Data:T", 
            title="Data", 
            axis=alt.Axis(format="%d/%m/%y", labelAngle=-45, labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', grid=False)
        ),
        y=alt.Y(
            "Total:Q", 
            title="Total de Vendas (R$)", 
            axis=alt.Axis(labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', gridColor='rgba(255, 255, 255, 0.1)')
        ),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Total:Q", title="Vendas (R$)", format=",.2f")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Evolução das Vendas Diárias", 
            fontSize=16,
            anchor="middle",
            color='white',
            dy=-10
        ),
        height=400 # Altura fixa
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    # Usar use_container_width=True no st.altair_chart
    return area_chart

def create_advanced_daily_sales_chart(df):
    """Cria um gráfico de vendas diárias empilhadas responsivo."""
    if df.empty or "Data" not in df.columns or df["Data"].isnull().all():
        return None
    
    df_sorted = df.sort_values("Data").copy()
    df_sorted.dropna(subset=["Data"], inplace=True)

    if df_sorted.empty:
        return None
    
    df_melted = df_sorted.melt(
        id_vars=["Data", "DataFormatada"],
        value_vars=["Cartão", "Dinheiro", "Pix"],
        var_name="Método",
        value_name="Valor"
    )
    
    # Remove entradas com valor zero ou NaN para não poluir o gráfico
    df_melted = df_melted[df_melted["Valor"].notna() & (df_melted["Valor"] > 0)]
    
    if df_melted.empty:
        return None
    
    bars = alt.Chart(df_melted).mark_bar(
        # size=15 # Tamanho pode ser ajustado ou removido para auto
    ).encode(
        x=alt.X(
            "Data:T",
            title="Data",
            axis=alt.Axis(format="%d/%m/%y", labelAngle=-45, labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', grid=False)
        ),
        y=alt.Y(
            "Valor:Q",
            title="Valor (R$)",
            stack="zero", # Empilha as barras
            axis=alt.Axis(labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', gridColor='rgba(255, 255, 255, 0.1)')
        ),
        color=alt.Color(
            "Método:N",
            scale=alt.Scale(range=CORES_MODO_ESCURO[:3]),
            legend=alt.Legend(
                title="Método de Pagamento",
                orient="bottom",
                direction="horizontal",
                titleFontSize=14,
                labelFontSize=12,
                symbolSize=100,
                padding=10,
                titleColor='white',
                labelColor='white'
            )
        ),
        tooltip=[
            alt.Tooltip("DataFormatada:N", title="Data"),
            alt.Tooltip("Método:N", title="Método"),
            alt.Tooltip("Valor:Q", title="Valor (R$)", format=",.2f")
        ],
        order=alt.Order("Método", sort="descending") # Garante ordem consistente de empilhamento
    ).properties(
        title=alt.TitleParams(
            text="Vendas Diárias por Método",
            fontSize=16,
            anchor="middle",
            color='white',
            dy=-10
        ),
        height=400 # Altura fixa
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    # Usar use_container_width=True no st.altair_chart
    return bars

def create_enhanced_weekday_analysis(df):
    """Cria análise de vendas por dia da semana responsiva."""
    if df.empty or "DiaSemana" not in df.columns or "Total" not in df.columns or df["DiaSemana"].isnull().all():
        return None, None
    
    df_copy = df.copy()
    df_copy["Total"] = pd.to_numeric(df_copy["Total"], errors="coerce")
    df_copy.dropna(subset=["Total", "DiaSemana"], inplace=True)
    
    if df_copy.empty:
        return None, None
    
    # Calcula Média e Total, tratando divisão por zero
    weekday_stats = df_copy.groupby("DiaSemana", observed=False).agg(
        Média=("Total", "mean"),
        Total=("Total", "sum"),
        Dias_Vendas=("Total", "count")
    ).reset_index()

    # Reordena para a ordem correta dos dias da semana
    weekday_stats["DiaSemana"] = pd.Categorical(weekday_stats["DiaSemana"], categories=dias_semana_ordem, ordered=True)
    weekday_stats = weekday_stats.sort_values("DiaSemana").reset_index(drop=True)

    # Calcula percentual da média total
    total_media_geral = weekday_stats["Média"].sum()
    weekday_stats["Percentual_Media"] = (weekday_stats["Média"] / total_media_geral * 100).round(1) if total_media_geral > 0 else 0

    chart = alt.Chart(weekday_stats).mark_bar(
        color=CORES_MODO_ESCURO[0],
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X(
            "DiaSemana:O",
            title="Dia da Semana",
            sort=dias_semana_ordem, # Garante a ordem correta no eixo X
            axis=alt.Axis(labelAngle=-45, labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', grid=False)
        ),
        y=alt.Y(
            "Média:Q",
            title="Média de Vendas (R$)",
            axis=alt.Axis(labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', gridColor='rgba(255, 255, 255, 0.1)')
        ),
        tooltip=[
            alt.Tooltip("DiaSemana:N", title="Dia"),
            alt.Tooltip("Média:Q", title="Média (R$)", format=",.2f"),
            alt.Tooltip("Percentual_Media:Q", title="% da Média Total", format=".1f"),
            alt.Tooltip("Dias_Vendas:Q", title="Nº Dias c/ Vendas")
        ]
    ).properties(
        title=alt.TitleParams(
            text="Média de Vendas por Dia da Semana",
            fontSize=16,
            anchor="middle",
            color='white',
            dy=-10
        ),
        height=400 # Altura fixa
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    best_day = weekday_stats.loc[weekday_stats["Média"].idxmax(), "DiaSemana"] if not weekday_stats.empty else "N/A"
    
    # Usar use_container_width=True no st.altair_chart
    return chart, best_day

def create_sales_histogram(df, title="Distribuição dos Valores de Venda Diários"):
    """Cria histograma responsivo."""
    if df.empty or "Total" not in df.columns or df["Total"].isnull().all():
        return None
    
    df_filtered_hist = df[df["Total"] > 0].copy()
    if df_filtered_hist.empty:
        return None
    
    histogram = alt.Chart(df_filtered_hist).mark_bar(
        color=CORES_MODO_ESCURO[0],
        opacity=0.8,
        cornerRadiusTopLeft=3,
        cornerRadiusTopRight=3
    ).encode(
        x=alt.X(
            "Total:Q",
            bin=alt.Bin(maxbins=20), # Agrupamento automático
            title="Faixa de Valor da Venda Diária (R$)",
            axis=alt.Axis(labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', grid=False)
        ),
        y=alt.Y(
            "count():Q",
            title="Número de Dias (Frequência)",
            axis=alt.Axis(labelFontSize=11, titleFontSize=13, titleColor='white', labelColor='white', gridColor='rgba(255, 255, 255, 0.1)')
        ),
        tooltip=[
            alt.Tooltip("Total:Q", bin=True, title="Faixa de Valor (R$)", format=",.0f"),
            alt.Tooltip("count():Q", title="Número de Dias")
        ]
    ).properties(
        title=alt.TitleParams(
            text=title,
            fontSize=16,
            anchor="middle",
            color='white',
            dy=-10
        ),
        height=400 # Altura fixa
    ).configure_view(
        stroke=None
    ).configure(
        background="transparent"
    )
    
    # Usar use_container_width=True no st.altair_chart
    return histogram

# --- Função para criar o Heatmap de Vendas --- 
# Mantida como estava, pois calplot gera imagem estática
@st.cache_data(ttl=3600) # Cache por 1 hora
def create_sales_heatmap(df, filename=HEATMAP_FILENAME):
    """Cria um heatmap de vendas diárias estilo GitHub e salva como imagem."""
    if df.empty or "Data" not in df.columns or "Total" not in df.columns or df["Data"].isnull().all():
        st.warning("Dados insuficientes para gerar o heatmap de vendas.")
        return None

    df_heatmap = df.copy()
    df_heatmap.dropna(subset=["Data"], inplace=True)
    
    if df_heatmap.empty:
        st.warning("Dados insuficientes após processamento para o heatmap.")
        return None

    # Agrega vendas por dia
    daily_sales = df_heatmap.groupby(df_heatmap["Data"].dt.date)["Total"].sum()
    daily_sales.index = pd.to_datetime(daily_sales.index)
    
    if daily_sales.empty:
        st.warning("Nenhuma venda diária encontrada para o heatmap.")
        return None

    try:
        cmap_name = "YlGn" # Colormap sequencial (Amarelo-Verde)
        
        plt.style.use("dark_background")
        plt.rcParams["figure.facecolor"] = "#0f0f23"
        plt.rcParams["axes.facecolor"] = "#0f0f23"
        plt.rcParams["savefig.facecolor"] = "#0f0f23"
        plt.rcParams["text.color"] = "white"
        plt.rcParams["axes.labelcolor"] = "white"
        plt.rcParams["xtick.color"] = "white"
        plt.rcParams["ytick.color"] = "white"

        fig, ax = calplot.calplot(daily_sales, 
                                cmap=cmap_name, 
                                figsize=(15, 3), 
                                colorbar=True,
                                suptitle="Calendário de Vendas Diárias (R$)",
                                yearlabel_kws={"color": "white", "fontsize": 14},
                                monthlabel_kws={"color": "white", "fontsize": 8},
                                daylabel_kws={"color": "white", "fontsize": 8},
                                dayticks=[0, 2, 4] # Mostra Seg, Qua, Sex
                               )
        
        # Salva a figura
        plt.savefig(filename, bbox_inches="tight", dpi=150)
        plt.close(fig) 
        return filename
    except Exception as e:
        st.error(f"Erro ao gerar o heatmap: {e}")
        try:
            plt.close(fig)
        except:
            pass
        return None

# --- Funções de Cálculos Financeiros (sem alterações significativas na lógica) ---
def calculate_financial_results(df, salario_minimo, custo_contadora, custo_fornecedores_percentual):
    """Calcula os resultados financeiros com base nos dados de vendas."""
    results = {
        "receita_bruta": 0, "receita_tributavel": 0, "receita_nao_tributavel": 0,
        "impostos_sobre_vendas": 0, "receita_liquida": 0, "custo_produtos_vendidos": 0,
        "lucro_bruto": 0, "margem_bruta": 0, "despesas_administrativas": 0,
        "despesas_com_pessoal": 0, "despesas_contabeis": custo_contadora,
        "total_despesas_operacionais": 0, "lucro_operacional": 0, "margem_operacional": 0,
        "lucro_antes_ir": 0, "lucro_liquido": 0, "margem_liquida": 0,
        "diferenca_tributavel_nao_tributavel": 0
    }
    
    if df is None or df.empty: 
        return results
    
    # Garante que as colunas existem antes de somar
    receita_bruta = df["Total"].sum() if "Total" in df else 0
    receita_tributavel = (df["Cartão"].sum() if "Cartão" in df else 0) + (df["Pix"].sum() if "Pix" in df else 0)
    receita_nao_tributavel = df["Dinheiro"].sum() if "Dinheiro" in df else 0
    
    results["receita_bruta"] = receita_bruta
    results["receita_tributavel"] = receita_tributavel
    results["receita_nao_tributavel"] = receita_nao_tributavel
    results["impostos_sobre_vendas"] = results["receita_tributavel"] * 0.06
    results["receita_liquida"] = results["receita_bruta"] - results["impostos_sobre_vendas"]
    results["custo_produtos_vendidos"] = results["receita_bruta"] * (custo_fornecedores_percentual / 100)
    results["lucro_bruto"] = results["receita_liquida"] - results["custo_produtos_vendidos"]
    
    if results["receita_liquida"] != 0:
        results["margem_bruta"] = (results["lucro_bruto"] / results["receita_liquida"]) * 100
    
    # Calcula despesas baseadas no número de meses únicos nos dados filtrados
    num_meses = 1 # Default para evitar divisão por zero se não houver dados
    if "AnoMês" in df and not df["AnoMês"].isnull().all():
        num_meses = df["AnoMês"].nunique()
        if num_meses == 0: num_meses = 1 # Garante pelo menos 1 mês
        
    results["despesas_com_pessoal"] = (salario_minimo * 1.55) * num_meses
    results["despesas_contabeis"] = custo_contadora * num_meses
    results["despesas_administrativas"] = 0 # Manter zero ou adicionar input se necessário
    results["total_despesas_operacionais"] = (
        results["despesas_com_pessoal"] + 
        results["despesas_contabeis"] + 
        results["despesas_administrativas"]
    )
    
    results["lucro_operacional"] = results["lucro_bruto"] - results["total_despesas_operacionais"]
    if results["receita_liquida"] != 0:
        results["margem_operacional"] = (results["lucro_operacional"] / results["receita_liquida"]) * 100
    
    results["lucro_antes_ir"] = results["lucro_operacional"] # Simples Nacional
    results["lucro_liquido"] = results["lucro_antes_ir"]
    if results["receita_liquida"] != 0:
        results["margem_liquida"] = (results["lucro_liquido"] / results["receita_liquida"]) * 100
    
    results["diferenca_tributavel_nao_tributavel"] = results["receita_nao_tributavel"]
    
    return results

def create_dre_textual(resultados, ano_dre):
    """Cria uma apresentação textual do DRE no estilo tradicional contábil para um ano específico."""
    def format_val(value):
        # Formata como inteiro se for próximo, senão com 2 decimais
        if abs(value - round(value)) < 0.01:
            return f"{value:,.0f}".replace(",", "#").replace(".", ",").replace("#", ".")
        else:
            return f"{value:,.2f}".replace(",", "#").replace(".", ",").replace("#", ".")

    dre_html = f"""
    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; color: #EAEAEA; padding: 15px; border: 1px solid #444; border-radius: 8px; background-color: rgba(45, 51, 59, 0.8); margin-bottom: 20px;">
        <h3 style="text-align: center; margin: 0 0 10px 0; font-weight: 600; color: #A0D0FF;">DEMONSTRAÇÃO DO RESULTADO DO EXERCÍCIO</h3>
        <p style="text-align: center; margin: 0 0 20px 0; font-style: italic; font-size: 14px;">Clips Burger - Exercício de {ano_dre}</p>
        
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
            <tr style="border-bottom: 1px solid #555;">
                <td style="padding: 8px 0;">Receita Bruta de Vendas</td>
                <td style="text-align: right; padding: 8px 0;">{format_val(resultados.get('receita_bruta', 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0 2px 15px; font-style: italic;">(-) Impostos sobre Vendas (Simples Nacional ~6% s/ Cartão+Pix)</td>
                <td style="text-align: right; padding: 8px 0 2px 0;">({format_val(resultados.get('impostos_sobre_vendas', 0))})</td>
            </tr>
            <tr style="border-bottom: 1px solid #555;">
                <td style="padding: 2px 0 8px 0; font-weight: bold;">(=) Receita Líquida</td>
                <td style="text-align: right; padding: 2px 0 8px 0; font-weight: bold;">{format_val(resultados.get('receita_liquida', 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0 2px 15px; font-style: italic;">(-) Custo dos Produtos Vendidos (CPV - Estimado)</td>
                <td style="text-align: right; padding: 8px 0 2px 0;">({format_val(resultados.get('custo_produtos_vendidos', 0))})</td>
            </tr>
             <tr style="border-bottom: 1px solid #555;">
                <td style="padding: 2px 0 8px 0; font-weight: bold;">(=) Lucro Bruto</td>
                <td style="text-align: right; padding: 2px 0 8px 0; font-weight: bold;">{format_val(resultados.get('lucro_bruto', 0))}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0 2px 0;">(-) Despesas Operacionais:</td>
                <td style="text-align: right; padding: 8px 0 2px 0;"></td>
            </tr>
            <tr>
                <td style="padding: 2px 0 2px 15px; font-style: italic;">Despesas com Pessoal (Salário + Encargos)</td>
                <td style="text-align: right; padding: 2px 0 2px 0;">({format_val(resultados.get('despesas_com_pessoal', 0))})</td>
            </tr>
            <tr>
                <td style="padding: 2px 0 2px 15px; font-style: italic;">Despesas Contábeis</td>
                <td style="text-align: right; padding: 2px 0 2px 0;">({format_val(resultados.get('despesas_contabeis', 0))})</td>
            </tr>
             <tr>
                <td style="padding: 2px 0 8px 15px; font-style: italic;">Despesas Administrativas</td>
                <td style="text-align: right; padding: 2px 0 8px 0;">({format_val(resultados.get('despesas_administrativas', 0))})</td>
            </tr>
            <tr style="border-bottom: 1px solid #555;">
                <td style="padding: 2px 0 8px 0; font-weight: bold;">(=) Lucro Operacional (LAJIR / EBIT)</td>
                <td style="text-align: right; padding: 2px 0 8px 0; font-weight: bold;">{format_val(resultados.get('lucro_operacional', 0))}</td>
            </tr>
             <tr>
                <td style="padding: 8px 0 8px 0; font-weight: bold;">(=) Lucro Antes do Imposto de Renda (LAIR)</td>
                <td style="text-align: right; padding: 8px 0 8px 0; font-weight: bold;">{format_val(resultados.get('lucro_antes_ir', 0))}</td>
            </tr>
             <tr style="border-top: 2px solid #666; border-bottom: 2px solid #666;">
                <td style="padding: 10px 0; font-weight: bold; font-size: 15px;">(=) Lucro Líquido do Exercício</td>
                <td style="text-align: right; padding: 10px 0; font-weight: bold; font-size: 15px; color: {'#90EE90' if resultados.get('lucro_liquido', 0) >= 0 else '#FF7F7F'};">{format_val(resultados.get('lucro_liquido', 0))}</td>
            </tr>
        </table>
        
        <div style="margin-top: 20px; font-size: 13px; text-align: center; color: #BBB;">
            Margem Bruta: {resultados.get('margem_bruta', 0):.1f}% | Margem Operacional: {resultados.get('margem_operacional', 0):.1f}% | Margem Líquida: {resultados.get('margem_liquida', 0):.1f}%
        </div>
        <div style="margin-top: 5px; font-size: 12px; text-align: center; color: #999;">
            Valores em Reais (R$). Estimativas baseadas nos dados e parâmetros fornecidos.
        </div>
    </div>
    """
    st.markdown(dre_html, unsafe_allow_html=True)

# --- Interface Streamlit --- 

def main():    # --- Título com Logo e Aura (usando URL remoto) ---
    st.markdown(
        f"""
        <div class="logo-container">
            <img src="{LOGO_URL}" class="logo-image" alt="Clips Burger Logo">
            <h1 style="color: white; margin: 0;">Sistema Financeiro - Clips Burger</h1>
        </div>
        """, 
        unsafe_allow_html=True
    )
    # Removida a verificação de existência local e o aviso.
    # --- Abas Principais ---
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "📅 Registrar Venda", "📈 Análise Detalhada", "💰 DRE (Demonstrativo)"])

    # --- Obter e Processar Dados ---
    # Tenta ler os dados. Se falhar, df_raw será None ou vazio, e df_processed também.
    df_raw = read_sales_data()
    df_processed = process_data(df_raw)

    # Verifica se a autenticação ou leitura falhou gravemente
    if get_google_auth() is None:
        st.stop() # Interrompe a execução se a autenticação falhar
    if df_raw is None: # Erro durante a leitura
        st.error("Falha ao carregar os dados da planilha. Verifique as mensagens de erro acima.")
        st.stop()
    if df_processed.empty and not df_raw.empty:
        st.warning("Os dados brutos foram lidos, mas o processamento resultou em um conjunto vazio. Verifique os formatos de data e valores na planilha.")
        # Permite continuar, mas algumas visualizações podem falhar

    # --- Filtros Globais (Sidebar) ---
    st.sidebar.header("Filtros")
    anos_disponiveis = sorted(df_processed["Ano"].dropna().unique().astype(int), reverse=True) if "Ano" in df_processed and not df_processed["Ano"].isnull().all() else []
    meses_disponiveis_map = {i+1: mes for i, mes in enumerate(meses_ordem)} if not df_processed.empty else {}

    # Filtro de Ano
    selected_anos = []
    if anos_disponiveis:
        selected_anos = st.sidebar.multiselect(
            "Selecione o(s) Ano(s)", 
            options=anos_disponiveis, 
            default=anos_disponiveis[0] if anos_disponiveis else []
        )
    else:
        st.sidebar.info("Nenhum ano disponível para filtro.")

    # Filtro de Mês (depende dos anos selecionados)
    meses_filtrados_opts = {}
    if selected_anos and "MêsNome" in df_processed:
        meses_filtrados_opts = sorted(
            df_processed[df_processed["Ano"].isin(selected_anos)]["MêsNome"].dropna().unique(),
            key=lambda m: meses_ordem.index(m) if m in meses_ordem else -1
        )
    
    selected_meses = []
    if meses_filtrados_opts:
        selected_meses = st.sidebar.multiselect(
            "Selecione o(s) Mês(es)", 
            options=meses_filtrados_opts, 
            default=meses_filtrados_opts # Seleciona todos por padrão
        )
    elif selected_anos:
        st.sidebar.info("Nenhum mês disponível para os anos selecionados.")

    # Aplica filtros
    df_filtered = df_processed.copy()
    if selected_anos:
        df_filtered = df_filtered[df_filtered["Ano"].isin(selected_anos)]
    if selected_meses:
        df_filtered = df_filtered[df_filtered["MêsNome"].isin(selected_meses)]

    # --- Tab 1: Dashboard --- 
    with tab1:
        st.header("Visão Geral Financeira")
        
        if df_filtered.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            # Métricas Principais (Layout Responsivo)
            col1, col2, col3 = st.columns(3)
            total_vendas = df_filtered["Total"].sum()
            media_diaria = df_filtered.groupby(df_filtered["Data"].dt.date)["Total"].sum().mean()
            dias_com_vendas = df_filtered["Data"].nunique()

            with col1:
                st.metric(label="💰 Receita Total (Filtrada)", value=f"R$ {total_vendas:,.2f}")
            with col2:
                st.metric(label="📈 Média Diária (Filtrada)", value=f"R$ {media_diaria:,.2f}" if not np.isnan(media_diaria) else "R$ 0,00")
            with col3:
                st.metric(label="🗓️ Dias com Vendas (Filtrados)", value=f"{dias_com_vendas}")
            
            st.markdown("--- ") # Separador

            # Gráficos Principais (Layout Responsivo)
            # Usando colunas para organizar melhor em telas maiores
            chart_col1, chart_col2 = st.columns([2, 1]) # Gráfico de área maior, radial menor

            with chart_col1:
                st.subheader("Evolução das Vendas")
                area_chart = create_area_chart_with_gradient(df_filtered)
                if area_chart:
                    st.altair_chart(area_chart, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para gerar o gráfico de evolução.")

            with chart_col2:
                st.subheader("Métodos de Pagamento")
                radial_plot = create_radial_plot(df_filtered)
                if radial_plot:
                    st.altair_chart(radial_plot, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para gerar o gráfico de métodos de pagamento.")

            st.markdown("--- ")

            # Heatmap de Vendas (Ocupa largura total)
            st.subheader("Calendário de Atividade de Vendas")
            heatmap_path = create_sales_heatmap(df_filtered) # Usa dados filtrados
            if heatmap_path and os.path.exists(heatmap_path):
                st.image(heatmap_path, use_column_width=True)
            else:
                st.info("Não foi possível gerar o heatmap de vendas para o período selecionado.")

    # --- Tab 2: Registrar Venda --- 
    with tab2:
        st.header("Registrar Nova Venda Diária")
        
        worksheet = get_worksheet() # Pega a planilha para escrita
        if worksheet is None:
            st.error("Não é possível registrar vendas pois a conexão com a planilha falhou.")
        else:
            with st.form("sales_form", clear_on_submit=True):
                col_form1, col_form2 = st.columns([1, 3])
                with col_form1:
                    sale_date = st.date_input("Data da Venda", value=datetime.today())
                
                with col_form2:
                    st.write("Valores por Método de Pagamento:")
                    sub_col1, sub_col2, sub_col3 = st.columns(3)
                    with sub_col1:
                        cartao_val = st.number_input("💳 Cartão", min_value=0.0, step=0.01, format="%.2f", key="cartao_input", help="Valor total recebido em cartão no dia.")
                    with sub_col2:
                        dinheiro_val = st.number_input("💵 Dinheiro", min_value=0.0, step=0.01, format="%.2f", key="dinheiro_input", help="Valor total recebido em dinheiro no dia.")
                    with sub_col3:
                        pix_val = st.number_input("📱 Pix", min_value=0.0, step=0.01, format="%.2f", key="pix_input", help="Valor total recebido via Pix no dia.")
                
                submitted = st.form_submit_button("💾 Registrar Venda")
                
                if submitted:
                    if not sale_date:
                        st.warning("Por favor, selecione a data da venda.")
                    elif cartao_val == 0 and dinheiro_val == 0 and pix_val == 0:
                        st.warning("Pelo menos um método de pagamento deve ter valor maior que zero.")
                    else:
                        # Chama a função para adicionar dados
                        success = add_data_to_sheet(sale_date, cartao_val, dinheiro_val, pix_val, worksheet)
                        if success:
                            # Limpa caches para forçar a releitura dos dados nas outras abas
                            get_worksheet.clear()
                            read_sales_data.clear()
                            process_data.clear()
                            create_sales_heatmap.clear() # Limpa cache do heatmap também
                            st.rerun() # Força o recarregamento da app para atualizar visualizações
                        # Mensagens de erro/sucesso são tratadas dentro de add_data_to_sheet

    # --- Tab 3: Análise Detalhada --- 
    with tab3:
        st.header("Análise Detalhada das Vendas")
        
        if df_filtered.empty:
            st.info("Nenhum dado encontrado para os filtros selecionados.")
        else:
            st.subheader("Vendas Diárias Detalhadas por Método")
            daily_sales_chart = create_advanced_daily_sales_chart(df_filtered)
            if daily_sales_chart:
                st.altair_chart(daily_sales_chart, use_container_width=True)
            else:
                st.info("Não há dados suficientes para o gráfico de vendas diárias.")
            
            st.markdown("--- ")
            
            col_analysis1, col_analysis2 = st.columns(2)
            
            with col_analysis1:
                st.subheader("Análise por Dia da Semana")
                weekday_chart, best_day = create_enhanced_weekday_analysis(df_filtered)
                if weekday_chart:
                    st.altair_chart(weekday_chart, use_container_width=True)
                    if best_day != "N/A":
                        st.markdown(f"💡 **Melhor dia em média:** {best_day}")
                else:
                    st.info("Não há dados suficientes para a análise por dia da semana.")
            
            with col_analysis2:
                st.subheader("Distribuição dos Valores de Venda")
                histogram = create_sales_histogram(df_filtered)
                if histogram:
                    st.altair_chart(histogram, use_container_width=True)
                else:
                    st.info("Não há dados suficientes para o histograma de vendas.")
            
            st.markdown("--- ")
            st.subheader("Dados Brutos Filtrados")
            # Mostra apenas colunas relevantes e formatadas
            cols_to_show = ["DataFormatada", "DiaSemana", "Cartão", "Dinheiro", "Pix", "Total"]
            df_display = df_filtered[[col for col in cols_to_show if col in df_filtered.columns]].copy()
            # Formata valores monetários
            for col in ["Cartão", "Dinheiro", "Pix", "Total"]:
                if col in df_display.columns:
                    df_display[col] = df_display[col].map('R$ {:,.2f}'.format)
            
            st.dataframe(df_display.sort_values(by="Data", ascending=False).reset_index(drop=True), use_container_width=True)

    # --- Tab 4: DRE (Demonstrativo) --- 
    with tab4:
        st.header("Demonstrativo de Resultado do Exercício (DRE) - Anual")
        st.info("Este DRE é uma **estimativa** anual baseada nos dados e parâmetros fornecidos. Consulte seu contador para valores oficiais.")

        # Inputs para cálculo do DRE Anual
        st.subheader("Parâmetros para Cálculo Anual")
        col_dre1, col_dre2, col_dre3 = st.columns(3)
        with col_dre1:
            # Usar st.session_state para persistir valores dos inputs
            if 'salario_tab4' not in st.session_state: st.session_state.salario_tab4 = 1550.0
            if 'contadora_tab4' not in st.session_state: st.session_state.contadora_tab4 = 316.0
            if 'fornecedores_tab4' not in st.session_state: st.session_state.fornecedores_tab4 = 30.0
            
            salario_base_mensal = st.number_input(
                "Salário Base Mensal (1 Funcionário)", 
                min_value=0.0, 
                value=st.session_state.salario_tab4, 
                step=50.0, 
                format="%.2f", 
                key="salario_input_tab4",
                help="Salário bruto mensal. Encargos (~55%) serão adicionados automaticamente.",
                on_change=lambda: st.session_state.update({'salario_tab4': st.session_state.salario_input_tab4})
            )
        with col_dre2:
            custo_contadora_mensal = st.number_input(
                "Custo Mensal Contadora", 
                min_value=0.0, 
                value=st.session_state.contadora_tab4, 
                step=10.0, 
                format="%.2f", 
                key="contadora_input_tab4",
                help="Valor mensal pago pelos serviços de contabilidade.",
                on_change=lambda: st.session_state.update({'contadora_tab4': st.session_state.contadora_input_tab4})
            )
        with col_dre3:
            custo_fornecedores_perc = st.number_input(
                "Custo Fornecedores (% da Receita Bruta)", 
                min_value=0.0, 
                max_value=100.0, 
                value=st.session_state.fornecedores_tab4, 
                step=1.0, 
                format="%.1f", 
                key="fornecedores_input_tab4",
                help="Percentual estimado do custo de insumos/fornecedores sobre a receita bruta.",
                on_change=lambda: st.session_state.update({'fornecedores_tab4': st.session_state.fornecedores_input_tab4})
            )
        
        # Seleção do Ano para o DRE
        st.subheader("Selecione o Ano para o DRE")
        if anos_disponiveis:
            selected_ano_dre = st.selectbox("Ano do Exercício", options=anos_disponiveis, index=0)
            
            # Filtra dados APENAS para o ano selecionado
            df_dre_ano = df_processed[df_processed["Ano"] == selected_ano_dre].copy()
            
            if not df_dre_ano.empty:
                # Calcula os resultados financeiros para o ano TODO
                # Passa os custos MENSAIS para a função, ela multiplica por 12 internamente
                resultados_ano = calculate_financial_results(
                    df_dre_ano, 
                    salario_base_mensal, 
                    custo_contadora_mensal, 
                    custo_fornecedores_perc
                )
                # Ajusta despesas para serem anuais (multiplica por 12)
                num_meses_no_ano = df_dre_ano['AnoMês'].nunique()
                if num_meses_no_ano == 0: num_meses_no_ano = 1 # Evita multiplicar por 0
                
                # Recalcula despesas baseado nos meses COM DADOS no ano
                resultados_ano["despesas_com_pessoal"] = (salario_base_mensal * 1.55) * num_meses_no_ano
                resultados_ano["despesas_contabeis"] = custo_contadora_mensal * num_meses_no_ano
                # Recalcula totais e lucros com despesas ajustadas
                resultados_ano["total_despesas_operacionais"] = resultados_ano["despesas_com_pessoal"] + resultados_ano["despesas_contabeis"]
                resultados_ano["lucro_operacional"] = resultados_ano["lucro_bruto"] - resultados_ano["total_despesas_operacionais"]
                resultados_ano["lucro_antes_ir"] = resultados_ano["lucro_operacional"]
                resultados_ano["lucro_liquido"] = resultados_ano["lucro_antes_ir"]
                # Recalcula margens anuais
                if resultados_ano["receita_liquida"] != 0:
                    resultados_ano["margem_operacional"] = (resultados_ano["lucro_operacional"] / resultados_ano["receita_liquida"]) * 100
                    resultados_ano["margem_liquida"] = (resultados_ano["lucro_liquido"] / resultados_ano["receita_liquida"]) * 100
                else:
                     resultados_ano["margem_operacional"] = 0
                     resultados_ano["margem_liquida"] = 0

                # Exibe o DRE textual
                create_dre_textual(resultados_ano, selected_ano_dre)
            else:
                st.warning(f"Não há dados de vendas registrados para o ano {selected_ano_dre} para gerar o DRE.")
                # Exibe DRE zerado
                create_dre_textual({key: 0 for key in calculate_financial_results(pd.DataFrame(),0,0,0).keys()}, selected_ano_dre)

        else:
            st.warning("Não há dados anuais disponíveis para gerar o DRE.")

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    main()

