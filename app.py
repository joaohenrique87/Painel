from flask import Flask, render_template, request
from pymongo import MongoClient
import pandas as pd
import joblib
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv

app = Flask(__name__)

try:
    if not MONGO_URI:
        raise ValueError("A variável MONGO_URI não foi encontrada. Verifique o .env ou as configurações do Render.")

    client = MongoClient(MONGO_URI)
    # Teste rápido de conexão (timeout de 5s para não travar o server)
    client.admin.command('ping')
    
    db = client['cbmpe_db']
    col = db['ocorrencias']
    
    # Caminho dos modelos
    # Tenta descobrir se está na raiz ou na pasta models/
    base_path = ''
    if os.path.exists('modelos'):
        base_path = 'modelos/'
    elif os.path.exists('models'):
        base_path = 'models/'
    
    print(f">>> Buscando IA em: '{base_path}'")

    modelo_natureza = joblib.load(base_path + 'modelo_natureza.pkl')
    modelo_vitimas = joblib.load(base_path + 'modelo_vitimas.pkl')
    modelo_tempo = joblib.load(base_path + 'modelo_tempo.pkl')
    modelo_massivo = joblib.load(base_path + 'modelo_massivo.pkl')
    
    le_regiao = joblib.load(base_path + 'encoder_regiao.pkl')
    le_relato = joblib.load(base_path + 'encoder_relato.pkl')
    le_natureza = joblib.load(base_path + 'encoder_natureza.pkl')
    
    print(">>> SISTEMA ONLINE: Conexão e IA carregadas.")

except Exception as e:
    erro_conexao = str(e)
    print(f"XXX ERRO CRÍTICO NO STARTUP: {e}")
# --- DASHBOARD COM FILTROS ---
@app.route('/')
def dashboard():
    # Filtros
    filtro_ano = request.args.get('ano')
    filtro_grupo = request.args.get('grupo')
    filtro_gravidade = request.args.get('gravidade')
    filtro_regiao = request.args.get('regiao')

    # Gerando a query
    query = {}
    
    if filtro_ano and filtro_ano != "Todos":
        query['ano'] = int(filtro_ano)
        
    if filtro_grupo and filtro_grupo != "Todos":
        query['natureza.grupo'] = filtro_grupo
        
    if filtro_gravidade and filtro_gravidade != "Todos":
        query['acidente_massivo.nivel'] = int(filtro_gravidade)
        
    if filtro_regiao and filtro_regiao != "Todos":
        query['regiao_operacional'] = filtro_regiao

    # agregando aos KPIs
    
    
    total = col.count_documents(query)
    
    # KPI Vítimas 
    pipeline_vitimas = [
        {"$match": query}, 
        {"$group": {"_id": None, "total": {"$sum": "$acidente_massivo.vitimas"}}}
    ]
    res_vitimas = list(col.aggregate(pipeline_vitimas))
    total_vitimas = res_vitimas[0]['total'] if res_vitimas else 0
    
    # Graf região
    pipeline_regiao = [
        {"$match": query},
        {"$group": {"_id": "$regiao_operacional", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    dados_regiao = list(col.aggregate(pipeline_regiao))

    # Graf natureza
    pipeline_natureza = [
        {"$match": query},
        {"$group": {"_id": "$natureza.grupo", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    dados_natureza = list(col.aggregate(pipeline_natureza))

    # Graf gravidade
    pipeline_massivo = [
        {"$match": query},
        {"$group": {"_id": "$acidente_massivo.nivel", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}}
    ]
    dados_massivo = list(col.aggregate(pipeline_massivo))
    
    # Tabela
    ultimas = col.find(query).sort("data_ocorrencia", -1).limit(10)
    
    # listas
    anos_disponiveis = sorted(col.distinct("ano"), reverse=True)
    grupos_disponiveis = sorted(col.distinct("natureza.grupo"))
    regioes_disponiveis = sorted(col.distinct("regiao_operacional"))
    
    return render_template('dashboard.html', 
                           total=total, 
                           vitimas=total_vitimas,
                           dados_regiao=dados_regiao,
                           dados_natureza=dados_natureza,
                           dados_massivo=dados_massivo,
                           ultimas=ultimas,                           
                           anos=anos_disponiveis,
                           grupos=grupos_disponiveis,
                           regioes=regioes_disponiveis,
                           filtros_ativos=request.args) 

# Preditivo
@app.route('/predicao', methods=['GET', 'POST'])
def predicao():
    resultado = None
    erro = None
    graficos_dinamicos = None
    
    # Gerar gráf
    colunas = ['Região', 'Horário', 'Dia da Semana', 'Relato Inicial']
    
    # 1. O que define a NATUREZA? 
    imps_nat = modelo_natureza.feature_importances_
    fatores_nat = [{"label": c, "valor": round(float(i)*100, 1)} for c, i in zip(colunas, imps_nat)]
    
    # 2. O que define as VÍTIMAS? 
    imps_vit = modelo_vitimas.feature_importances_
    fatores_vit = [{"label": c, "valor": round(float(i)*100, 1)} for c, i in zip(colunas, imps_vit)]
    
    graficos_globais = {
        "natureza": {
            "labels": [f['label'] for f in sorted(fatores_nat, key=lambda x: x['valor'], reverse=True)],
            "data": [f['valor'] for f in sorted(fatores_nat, key=lambda x: x['valor'], reverse=True)]
        },
        "vitimas": {
            "labels": [f['label'] for f in sorted(fatores_vit, key=lambda x: x['valor'], reverse=True)],
            "data": [f['valor'] for f in sorted(fatores_vit, key=lambda x: x['valor'], reverse=True)]
        }
    }

    opcoes_regiao = le_regiao.classes_
    opcoes_relato = le_relato.classes_
    
    if request.method == 'POST':
        try:
            regiao_input = request.form['regiao']
            relato_input = request.form['relato']
            dt_obj = datetime.strptime(request.form['data_hora'], '%Y-%m-%dT%H:%M')
            
            regiao_cod = le_regiao.transform([regiao_input])[0]
            relato_cod = le_relato.transform([relato_input])[0]
            
            X = pd.DataFrame([[regiao_cod, dt_obj.hour, dt_obj.weekday(), relato_cod]], 
                             columns=['regiao_cod', 'hora', 'dia_semana', 'relato_cod'])
            
            # Previsões
            nat_cod = modelo_natureza.predict(X)[0]
            nat_texto = le_natureza.inverse_transform([nat_cod])[0]
            
            vitimas = max(0, int(round(modelo_vitimas.predict(X)[0])))
            vitimas_float = modelo_vitimas.predict(X)[0]
            
            tempo = max(1, int(round(modelo_tempo.predict(X)[0])))
            prob_massivo = modelo_massivo.predict_proba(X)[0][1] * 100
            
            # Graf prob por natureza            
            probs = modelo_natureza.predict_proba(X)[0]
            classes = le_natureza.classes_             
            probs_list = [{"label": c, "valor": round(p*100, 1)} for c, p in zip(classes, probs)]
            probs_list = sorted(probs_list, key=lambda x: x['valor'], reverse=True) # Ordena do mais provável

            resultado = {
                "natureza": nat_texto,
                "vitimas": vitimas,
                "vitimas_float": round(vitimas_float, 2),
                "tempo": tempo,
                "risco": round(prob_massivo, 1)
            }
            
            graficos_dinamicos = {
                "natureza_probs": {
                    "labels": [x['label'] for x in probs_list],
                    "data": [x['valor'] for x in probs_list]
                }
            }

        except Exception as e:
            erro = f"Erro IA: {str(e)}"

    return render_template('predicao.html', 
                           opcoes_regiao=opcoes_regiao, 
                           opcoes_relato=opcoes_relato,
                           resultado=resultado,
                           graficos_globais=graficos_globais,
                           graficos_dinamicos=graficos_dinamicos,
                           erro=erro)

if __name__ == '__main__':
    app.run(debug=True)