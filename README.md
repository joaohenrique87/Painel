🚒 SIS-CBMPE | Sistema de Gestão Operacional e Inteligência
Sistema de Dashboard e Predição Tática desenvolvido para auxiliar o Corpo de Bombeiros Militar de Pernambuco (CBMPE). O sistema utiliza Inteligência Artificial (XGBoost) para prever a natureza de ocorrências, estimar o número de vítimas e calcular o tempo de resposta, além de fornecer um painel gerencial completo com filtros dinâmicos.

🚀 Funcionalidades
1. 📊 Dashboard Operacional (Homepage)
Panorama Geral: KPIs de total de ocorrências e vítimas atendidas.

Gráficos Interativos (Chart.js):

Distribuição por Região (RMR, Sertão, Agreste, etc.).

Tipos de Natureza (Incêndio, APH, Salvamento...).

Níveis de Gravidade (Normal vs. Acidente Massivo).

Filtros Dinâmicos: Filtre todos os dados por Ano (2020-2025), Região, Natureza e Gravidade.

Tabela em Tempo Real: Visualização dos últimos registros do banco.

2. 🧠 Módulo de Inteligência Artificial
Simulação de Despacho: O operador insere dados iniciais (Hora, Local, Relato do 193).

Predição Multi-Target: O sistema prevê simultaneamente:

Natureza Provável: (Ex: É Incêndio ou APH?)

Estimativa de Vítimas: Quantidade exata e alerta de risco.

Tempo de Resposta: Previsão de deslocamento em minutos.

Risco Massivo: Probabilidade de ser uma catástrofe.

Explicabilidade (XAI):

Gráfico de Fatores: Mostra por que a IA tomou aquela decisão (Ex: "O horário de pico influenciou 60% na previsão de vítimas").

Probabilidades: Mostra a certeza do modelo para cada tipo de ocorrência.

🛠️ Tecnologias Utilizadas
Backend: Python 3.x, Flask

Banco de Dados: MongoDB Atlas (Cloud)

Machine Learning: XGBoost, Scikit-Learn, Pandas, Joblib

Frontend: HTML5, CSS3, Bootstrap 5, Chart.js

Segurança: Python-Dotenv (Variáveis de Ambiente)

📂 Estrutura do Projeto
Plaintext

/projeto-cbmpe
│
├── app.py                 # Servidor Web (Flask) e Rotas
├── banco.py               # Script para povoar o MongoDB com dados fictícios inteligentes
├── treinar_modelo.py      # Script para treinar a IA e gerar os arquivos .pkl
│
├── .env                   # Arquivo de configuração (NÃO COMPARTILHAR)
├── .gitignore             # Arquivos ignorados pelo Git
├── requirements.txt       # Lista de dependências do projeto
│
├── models/                # Pasta onde os modelos treinados são salvos
│     ├── modelo_natureza.pkl
│     ├── modelo_vitimas.pkl
│     └── ... (encoders)
│
└── templates/             # Páginas HTML (Frontend)
      ├── dashboard.html   # Painel com gráficos e filtros
      └── predicao.html    # Interface da IA com simulação
⚙️ Como Executar o Projeto
1. Pré-requisitos
Certifique-se de ter o Python instalado. Recomenda-se usar um ambiente virtual (venv).

Bash

# Clone o repositório
git clone https://github.com/seu-usuario/seu-repositorio.git
cd projeto-cbmpe

# Crie e ative o ambiente virtual (Opcional, mas recomendado)
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate
2. Instalação das Dependências
Bash

pip install -r requirements.txt
3. Configuração do Banco de Dados
Crie um arquivo .env na raiz do projeto e adicione sua string de conexão do MongoDB Atlas:

Snippet de código

MONGO_URI=mongodb+srv://admin:SUA_SENHA@cluster0.euh9zno.mongodb.net/?appName=Cluster0
4. Preparação dos Dados (ETL e Treinamento)
Antes de rodar o site, você precisa gerar os dados e treinar a inteligência artificial. Execute na ordem:

Bash

# 1. Gerar dados históricos (2020-2025) no MongoDB
python banco.py

# 2. Treinar os 4 modelos de IA (Gera os arquivos na pasta /models)
python modelo.py
5. Executar a Aplicação
Bash

python app.py
Acesse no seu navegador: http://127.0.0.1:5000

🧪 Como Testar a IA
Vá para a aba "Inteligência (IA)" no menu superior.

Preencha o formulário de simulação:

Data/Hora: Tente colocar um horário de madrugada (ex: 02:00) vs horário de pico (18:00).

Região: Tente "RMR" (Recife) vs "SERTAO".

Relato: Escolha algo vago como "Solicitação de vistoria".

Clique em CALCULAR.

Observe como os gráficos de "Fatores Preponderantes" mudam dependendo das suas escolhas, mostrando a inteligência do modelo em ação.