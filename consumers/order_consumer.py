import os
import json
from pymongo import MongoClient
from kafka import KafkaConsumer


# Conecta no MongoDB e retorna a coleção
def conectar_mongodb(db_name="meu_banco"):
    host = os.getenv(
        "MONGODB_HOST", "localhost:27017"
    )  # valor padrão caso a variável não exista
    client = MongoClient(f"mongodb://{host}")
    db = client[db_name]  # nome do banco
    return db


# Função para inserir documento JSON em uma coleção específica
def inserir_documento(colecao_nome, json_doc):
    db = conectar_mongodb()
    collection = db[colecao_nome]
    resultado = collection.insert_one(json_doc)
    return resultado.inserted_id


# Função para buscar documento no MongoDB pelo filtro em uma coleção específica
def buscar_documento(colecao_nome, filtro):
    db = conectar_mongodb()
    collection = db[colecao_nome]
    documento = collection.find_one(filtro)
    if documento:
        return documento
    else:
        return None


def kafka_admin(kafka_server):
    return KafkaConsumer(bootstrap_servers=kafka_server)


def main():
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "orders")
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "staging")

    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="orders-consumer-group",
        request_timeout_ms=60 * 1000,
    )
    # .bootstrap_connected()
    print(f"Conectado ao Kafka - tópico: {KAFKA_TOPIC}")
    for msg in consumer:
        print("\n--- Mensagem Recebida ---")

        doc = msg.value
        id_inserido = inserir_documento(MONGODB_COLLECTION, doc)
        print(f"- ID MONGODB: {id_inserido}")


if __name__ == "__main__":
    print("INICIANDO CONSUMER")
    main()
