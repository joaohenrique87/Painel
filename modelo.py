import os
import pandas as pd
import xgboost as xgb
from pymongo import MongoClient
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
import joblib
from dotenv import load_dotenv

load_dotenv()
#setar banco
MONGO_URI = os.getenv("MONGO_URI")



try:
    client = MongoClient(MONGO_URI)
    db = client['cbmpe_db']
    col = db['ocorrencias']
    print("Conectado! Baixando dados...")
except Exception as e:
    print(f"Erro: {e}")
    exit()

# Preparando os alvos
cursor = col.find({}, {
    "regiao_operacional": 1, 
    "data_ocorrencia": 1,
    "natureza.natureza_inicial_aviso": 1,
    "natureza.grupo": 1,
    "acidente_massivo.vitimas": 1,
    "status_horarios": 1 
})

dados = []
for doc in cursor:
    # Calculando o tempo de resposta (Chegada - Recebimento)
    h1 = doc['status_horarios']['h1_recebimento']
    h4 = doc['status_horarios']['h4_chegada']
    tempo_minutos = (h4 - h1).total_seconds() / 60
    
    # Risco maassivo (se vitimas >= 5 risco alto)
    vitimas = doc['acidente_massivo']['vitimas']
    eh_massivo = 1 if vitimas >= 5 else 0

    dados.append({
        "regiao": doc.get('regiao_operacional', 'RMR'),
        "hora": doc['data_ocorrencia'].hour,
        "dia_semana": doc['data_ocorrencia'].weekday(),
        "relato": doc['natureza']['natureza_inicial_aviso'],
        # ALVOS
        "target_nat": doc['natureza']['grupo'],
        "target_vit": vitimas,
        "target_tempo": tempo_minutos, 
        "target_massivo": eh_massivo
    })

df = pd.DataFrame(dados)
print(f"Dados processados: {len(df)} registros.")

# Encoders
le_regiao = LabelEncoder()
df['regiao_cod'] = le_regiao.fit_transform(df['regiao'])

le_relato = LabelEncoder()
df['relato_cod'] = le_relato.fit_transform(df['relato'])

le_natureza = LabelEncoder()
df['natureza_cod'] = le_natureza.fit_transform(df['target_nat'])

X = df[['regiao_cod', 'hora', 'dia_semana', 'relato_cod']]

# Treinando modelos

print("1. Treinando Natureza...")
modelo_natureza = xgb.XGBClassifier(eval_metric='mlogloss', use_label_encoder=False)
modelo_natureza.fit(X, df['natureza_cod'])

print("2. Treinando Vítimas...")
modelo_vitimas = xgb.XGBRegressor(objective='reg:squarederror')
modelo_vitimas.fit(X, df['target_vit'])

print("3. Treinando Tempo...")
modelo_tempo = xgb.XGBRegressor(objective='reg:squarederror')
modelo_tempo.fit(X, df['target_tempo'])

print("4. Treinando Risco Massivo...")
modelo_massivo = xgb.XGBClassifier(eval_metric='logloss', use_label_encoder=False)
modelo_massivo.fit(X, df['target_massivo'])

# Salvando os modelos
print("Salvando arquivos .pkl...")
joblib.dump(modelo_natureza, 'modelo_natureza.pkl')
joblib.dump(modelo_vitimas, 'modelo_vitimas.pkl')
joblib.dump(modelo_tempo, 'modelo_tempo.pkl')    
joblib.dump(modelo_massivo, 'modelo_massivo.pkl')

joblib.dump(le_regiao, 'encoder_regiao.pkl')
joblib.dump(le_relato, 'encoder_relato.pkl')
joblib.dump(le_natureza, 'encoder_natureza.pkl')

print("Arquivos gerados.")