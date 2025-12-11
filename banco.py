import os
import random
from datetime import datetime, timedelta
from pymongo import MongoClient
from faker import Faker
from dotenv import load_dotenv

load_dotenv()


#setar banco

MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)
    db = client['cbmpe_db']
    col = db['ocorrencias']
    print("Conectado")
except Exception as e:
    print(f"Erro de conexão: {e}")
    exit()

fake = Faker('pt_BR')

# Localidades e dados estruturais
locais_pe = [
    # RMR
    {"cidade": "Recife", "bairro": "Boa Viagem", "lat": -8.1147, "lng": -34.9048, "regiao": "RMR"},
    {"cidade": "Recife", "bairro": "Casa Amarela", "lat": -8.0261, "lng": -34.9149, "regiao": "RMR"},
    {"cidade": "Olinda", "bairro": "Rio Doce", "lat": -7.9593, "lng": -34.8415, "regiao": "RMR"},
    {"cidade": "Jaboatão", "bairro": "Prazeres", "lat": -8.1634, "lng": -34.9256, "regiao": "RMR"},
    # Interior
    {"cidade": "Caruaru", "bairro": "Centro", "lat": -8.2849, "lng": -35.9696, "regiao": "AGRESTE"},
    {"cidade": "Petrolina", "bairro": "Centro", "lat": -9.3970, "lng": -40.5033, "regiao": "SERTAO"},
    {"cidade": "Serra Talhada", "bairro": "Bom Jesus", "lat": -7.9931, "lng": -38.2972, "regiao": "SERTAO"},
    {"cidade": "Palmares", "bairro": "Centro", "lat": -8.6811, "lng": -35.5908, "regiao": "MATA"}
]

relatos_ambiguos = [
    "Solicitação de vistoria", "Populares informam estrondo", "Cheiro forte no local",
    "Fumaça avistada de longe", "Pedido de socorro via 193", "Animal em situação de risco",
    "Ocorrência em via pública", "Queda de estrutura", "Vazamento não identificado"
]

relatos_especificos = {
    "APH": ["Colisão moto x carro", "Atropelamento", "Queda de própria altura", "Mal súbito em via"],
    "INCENDIO": ["Fogo em vegetação", "Chamas em edificação", "Incêndio veicular", "Princípio de incêndio"],
    "SALVAMENTO": ["Pessoa presa em elevador", "Afogamento", "Gato em árvore", "Desabamento"],
    "PRODUTOS_PERIGOSOS": ["Vazamento de GLP", "Derramamento de óleo", "Cheiro de amônia"],
    "PREVENCAO": ["Vistoria em evento", "Prevenção orla"],
    "COMUNITARIA": ["Palestras educativas", "Simulado"]
}

naturezas_config = {
    "1": {"nome": "ATENDIMENTO PRÉ-HOSPITALAR", "cor": "AZUL", "grupo": "APH"},
    "2": {"nome": "INCÊNDIO", "cor": "VERMELHA", "grupo": "INCENDIO"},
    "3": {"nome": "SALVAMENTO", "cor": "LARANJA", "grupo": "SALVAMENTO"},
    "4": {"nome": "PRODUTOS PERIGOSOS", "cor": "AMARELA", "grupo": "PRODUTOS_PERIGOSOS"},
    "5": {"nome": "PREVENÇÃO", "cor": "VERDE", "grupo": "PREVENCAO"},
    "6": {"nome": "ATIVIDADE COMUNITÁRIA", "cor": "CAQUI", "grupo": "COMUNITARIA"}
}

def gerar_horarios(data_inicio):
    h1 = data_inicio   
    h2 = h1 + timedelta(minutes=random.randint(1, 5))     
    tempo_viagem = random.randint(5, 45)
    h4 = h2 + timedelta(minutes=tempo_viagem)
    
    return { "h1_recebimento": h1, "h4_chegada": h4 }

def gerar_ocorrencia():
    local = random.choice(locais_pe)
    
    # datas de 20-25
    data_base = fake.date_time_between(start_date='-5y', end_date='now')
    hora = data_base.hour
    mes = data_base.month

    # Forçando coorelação
    if local["regiao"] == "SERTAO" and 12 <= hora <= 16 and mes > 8:
        grupo = "INCENDIO"
    
        relato = random.choice(relatos_ambiguos) if random.random() < 0.5 else random.choice(relatos_especificos["INCENDIO"])
    
    
    elif local["regiao"] == "RMR" and (7 <= hora <= 9 or 17 <= hora <= 19):
        grupo = "APH"
        relato = random.choice(relatos_ambiguos) if random.random() < 0.4 else random.choice(relatos_especificos["APH"])
    
    
    else:
        grupo = random.choices(
            ["APH", "INCENDIO", "SALVAMENTO", "PRODUTOS_PERIGOSOS", "PREVENCAO", "COMUNITARIA"],
            weights=[40, 20, 20, 5, 10, 5]
        )[0]
        relato = random.choice(relatos_especificos[grupo])

    # Vítimas
    vitimas = 0
    if grupo == "APH": vitimas = random.choices([1, 2, 5], weights=[70, 20, 10])[0]
    if grupo == "INCENDIO" and random.random() < 0.2: vitimas = random.randint(1, 3)

    nivel_massivo = 0
    if vitimas >= 5: nivel_massivo = 1
    if vitimas > 10: nivel_massivo = 2

    return {
        "numero_aviso": f"AV-{fake.random_number(digits=8)}",
        "data_ocorrencia": data_base,
        "ano": int(data_base.year), 
        "regiao_operacional": local["regiao"],
        "natureza": {
            "natureza_inicial_aviso": relato,
            "grupo": grupo
        },
        "endereco": {
            "municipio": local["cidade"],
            "bairro": "Centro" 
        },
        "status_horarios": gerar_horarios(data_base),
        "acidente_massivo": { "nivel": nivel_massivo, "vitimas": vitimas }
    }

def povoar_banco(qtd=5000):
    print("Limpando")
    col.delete_many({}) 
    print(f"Gerando {qtd}(2020-2025)...")
    lista = [gerar_ocorrencia() for _ in range(qtd)]
    col.insert_many(lista)
    print("Sucesso")

if __name__ == "__main__":
    povoar_banco(5000)