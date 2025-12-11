import os
from flask import Flask, render_template, request
from pymongo import MongoClient
import pandas as pd
import joblib
import numpy as np
from datetime import datetime
from dotenv import load_dotenv

app = Flask(__name__)

# iniciando as variaveis para tentar subir no Render (Sugestão IA)
client = None
db = None
col = None
erro_conexao = "Inicializando..."

modelo_natureza = None
modelo_vitimas = None
modelo_tempo = None
modelo_massivo = None
le_regiao = None
le_relato = None
le_natureza = None

# Setando banco
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# --- 3. TENTATIVA DE CONEXÃO E CARREGAMENTO ---
try:
    if not MONGO_URI:
        raise ValueError("A variável de ambiente 'MONGO_URI' não foi encontrada. Configure no Painel do Render.")

    # Conexão com o Banco
    client = MongoClient(MONGO_URI)
    # Teste rápido (5s timeout) para garantir que conectou
    client.admin.command('ping')
    
    db = client['cbmpe_db']
    col = db['ocorrencias']
    
    # Caminho dos modelos (Verifica onde o Render salvou)
    base_path = ''
    if os.path.exists('modelos'):
        base_path = 'modelos/'
    elif os.path.exists('models'):
        base_path = 'models/'
    
    print(f">>> Buscando IA em: '{base_path}'")

    # Carregar IA
    modelo_natureza = joblib.load(base_path + 'modelo_natureza.pkl')
    modelo_vitimas = joblib.load(base_path + 'modelo_vitimas.pkl')
    modelo_tempo = joblib.load(base_path + 'modelo_tempo.pkl')
    modelo_massivo = joblib.load(base_path + 'modelo_massivo.pkl')
    
    le_regiao = joblib.load(base_path + 'encoder_regiao.pkl')
    le_relato = joblib.load(base_path + 'encoder_relato.pkl')
    le_natureza = joblib.load(base_path + 'encoder_natureza.pkl')
    
    print(">>> SISTEMA ONLINE: Conexão e IA carregadas com sucesso.")
    erro_conexao = None # Limpa o erro se tudo deu certo

except Exception as e:
    erro_conexao = str(e)
    print(f"XXX ERRO CRÍTICO NO STARTUP: {e}")

# Rota dash
@app.route('/')
def dashboard():
    # Verificação(Se o banco falhou, não quebra o site)
    if col is None:
        return f"""
        <div style='text-align:center; padding:50px; font-family:sans-serif;'>
            <h1 style='color:red;'>⚠️ Serviço Indisponível</h1>
            <p>O sistema não conseguiu conectar ao Banco de Dados.</p>
            <p><strong>Erro Técnico:</strong> {erro_conexao}</p>
            <hr>
            <p><em>Dica: Verifique se a variável MONGO_URI foi adicionada nas configurações do Render.</em></p>
        </div>
        """, 500

    try:
        # lista de filtros
        filtros_ano = request.args.getlist('ano')
        filtros_grupo = request.args.getlist('grupo')
        filtros_gravidade = request.args.getlist('gravidade')
        filtros_regiao = request.args.getlist('regiao')
        
        query = {}
        
        if filtros_ano and "Todos" not in filtros_ano:            
            query['ano'] = {'$in': [int(x) for x in filtros_ano]}
            
        if filtros_grupo and "Todos" not in filtros_grupo:
            query['natureza.grupo'] = {'$in': filtros_grupo}
            
        if filtros_gravidade and "Todos" not in filtros_gravidade:          
            query['acidente_massivo.nivel'] = {'$in': [int(x) for x in filtros_gravidade]}
            
        if filtros_regiao and "Todos" not in filtros_regiao:
            query['regiao_operacional'] = {'$in': filtros_regiao}

        total = col.count_documents(query)
        
        pipeline_vitimas = [{"$match": query}, {"$group": {"_id": None, "total": {"$sum": "$acidente_massivo.vitimas"}}}]
        res_vitimas = list(col.aggregate(pipeline_vitimas))
        total_vitimas = res_vitimas[0]['total'] if res_vitimas else 0
        
        pipeline_regiao = [{"$match": query}, {"$group": {"_id": "$regiao_operacional", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
        dados_regiao = list(col.aggregate(pipeline_regiao))

        pipeline_natureza = [{"$match": query}, {"$group": {"_id": "$natureza.grupo", "count": {"$sum": 1}}}, {"$sort": {"count": -1}}]
        dados_natureza = list(col.aggregate(pipeline_natureza))

        pipeline_massivo = [{"$match": query}, {"$group": {"_id": "$acidente_massivo.nivel", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}]
        dados_massivo = list(col.aggregate(pipeline_massivo))
        
        ultimas = col.find(query).sort("data_ocorrencia", -1).limit(10)
        
        anos = sorted(col.distinct("ano"), reverse=True)
        grupos = sorted(col.distinct("natureza.grupo"))
        regioes = sorted(col.distinct("regiao_operacional"))
        
        return render_template('dashboard.html', 
                               total=total, 
                               vitimas=total_vitimas, 
                               dados_regiao=dados_regiao, 
                               dados_natureza=dados_natureza, 
                               dados_massivo=dados_massivo, 
                               ultimas=ultimas, 
                               anos=anos, 
                               grupos=grupos, 
                               regioes=regioes,                              
                               filtros_ativos=request.args)
    
    except Exception as e:
        return f"Erro interno: {e}", 500

# --- ROTA 2: PREDICAO ---
@app.route('/predicao', methods=['GET', 'POST'])
def predicao():
    # VERIFICAÇÃO DE SEGURANÇA (Se a IA falhou)
    if modelo_natureza is None:
        return f"""
        <div style='text-align:center; padding:50px; font-family:sans-serif;'>
            <h2 style='color:red;'>⚠️ Módulo de IA Offline</h2>
            <p>Os modelos de inteligência artificial não foram carregados.</p>
            <p><strong>Erro no Banco:</strong> {erro_conexao}</p>
        </div>
        """, 500

    resultado = None
    erro = None
    graficos_dinamicos = None
    
    colunas = ['Região', 'Horário', 'Dia da Semana', 'Relato Inicial']
    
    imps_nat = modelo_natureza.feature_importances_
    fatores_nat = [{"label": c, "valor": round(float(i)*100, 1)} for c, i in zip(colunas, imps_nat)]
    
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
            
            nat_cod = modelo_natureza.predict(X)[0]
            nat_texto = le_natureza.inverse_transform([nat_cod])[0]
            
            vitimas = max(0, int(round(modelo_vitimas.predict(X)[0])))
            vitimas_float = modelo_vitimas.predict(X)[0]
            
            tempo = max(1, int(round(modelo_tempo.predict(X)[0])))
            prob_massivo = modelo_massivo.predict_proba(X)[0][1] * 100
            
            probs = modelo_natureza.predict_proba(X)[0]
            classes = le_natureza.classes_
            
            probs_list = [{"label": c, "valor": round(float(p)*100, 1)} for c, p in zip(classes, probs)]
            probs_list = sorted(probs_list, key=lambda x: x['valor'], reverse=True)

            resultado = {
                "natureza": nat_texto,
                "vitimas": vitimas,
                "vitimas_float": round(float(vitimas_float), 2),
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
            erro = f"Erro no processamento da IA: {str(e)}"

    return render_template('predicao.html', 
                           opcoes_regiao=opcoes_regiao, 
                           opcoes_relato=opcoes_relato,
                           resultado=resultado,
                           graficos_globais=graficos_globais,
                           graficos_dinamicos=graficos_dinamicos,
                           erro=erro)

if __name__ == '__main__':
    app.run(debug=True)