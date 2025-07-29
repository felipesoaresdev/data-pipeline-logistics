import os
from dotenv import load_dotenv
from pymongo import MongoClient
import pandas as pd

load_dotenv()

def conectar_mongodb(db_name="meu_banco"):
    host = os.getenv("MONGODB_HOST", "localhost:27017")
    client = MongoClient(f"mongodb://{host}")
    return client[db_name]

def carregar_dados_em_dataframe(colecao_nome="output_llm", limite=0) -> pd.DataFrame:
    db = conectar_mongodb()
    collection = db[colecao_nome]
    
    cursor = collection.find().limit(limite) if limite > 0 else collection.find()
    docs = list(cursor)

    for doc in docs:
        doc["_id"] = str(doc["_id"])

    df = pd.DataFrame(docs)
    return df


if __name__ == "__main__":
    df_motorista_real = carregar_dados_em_dataframe("output_llm")

    # Converter colunas numéricas que podem ter vindo como string
    df_motorista_real["capacidade_total_unidades"] = pd.to_numeric(
        df_motorista_real["capacidade_total_unidades"], errors="coerce"
    )
    df_motorista_real["quantidade_atual"] = pd.to_numeric(
        df_motorista_real["quantidade_atual"], errors="coerce"
    )

    # Filtrar motoristas válidos
    df_motorista = df_motorista_real[df_motorista_real["motorista_id"] != ""]

    # Agrupar por motorista
    df_motorista = (
        df_motorista.groupby("motorista_nome")
        .agg({
            "capacidade_total_unidades": "first",
            "quantidade_atual": "sum",
            "pedido_id": "count"
        })
        .reset_index()
    )

    # Renomear colunas
    df_motorista.columns = ["Motorista", "Peso (kg)", "Volume (m³)", "Pedidos"]

    print(df_motorista.head())
