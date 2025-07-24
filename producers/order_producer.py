print("🔥 Iniciando producer...", flush=True)

import os
import sys
import json
from random import randint
from time import sleep
import pendulum
from kafka import KafkaProducer
from dotenv import load_dotenv

sys.path.append(os.getcwd())

from pagseguro.gen_order import OrderGen


load_dotenv()


def set_producer_rate():
    PRODUCER_MAX_INTERVAL = os.getenv("PRODUCER_MAX_INTERVAL")

    if PRODUCER_MAX_INTERVAL is None or PRODUCER_MAX_INTERVAL == "":
        dt = pendulum.now()
        hora = dt.hour
        # Hora de dormir
        if hora < 9 or hora > 21:
            print("Coportamento: Hora de dormir")
            return 60 * 60 * 3  # 3 horas
        # Almoço
        if hora > 11 or hora < 14:
            print("Coportamento: Almoço")
            return 60 * 10  # 10 min
        # Depois do trabalho
        if hora < 9 or hora > 21:
            print("Coportamento: Depois do trabalho")
            return 60 * 10  # 10 min
        print("Coportamento: Padrão")
        return 60 * 60 * 3  # 3 horas
    print("Coportamento: PRODUCER_MAX_INTERVAL no .env")
    return int(PRODUCER_MAX_INTERVAL)


def build_producer(kafka_server):
    return KafkaProducer(
        bootstrap_servers=kafka_server,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks=0,
    )


def main():
    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "orders")
    LIMIT_NUM_ORDERS = os.getenv("LIMIT_NUM_ORDERS", "10000000")

    print("O PRODUCER ESTÁ ATIVO")
    print(f"KAFKA_BOOTSTRAP_SERVERS: {KAFKA_BOOTSTRAP_SERVERS}")
    print(f"KAFKA_TOPIC: {KAFKA_TOPIC}")
    print(f"LIMIT_NUM_ORDERS: {LIMIT_NUM_ORDERS}")

    # Inicia um gerador de vendas
    order_generator = OrderGen()

    # print(order_generator.generate(pendulum.now("America/Fortaleza")))

    try:
        # Connecta o producer
        producer = build_producer(KAFKA_BOOTSTRAP_SERVERS)

        # Verifica se o kafka está ativo
        status = producer.bootstrap_connected()
        print(f"Kafka avaliable at {KAFKA_BOOTSTRAP_SERVERS}: {status}")
    except Exception as e:
        print("ERRO:", e)
        return

    count = 0
    while count < int(LIMIT_NUM_ORDERS):
        count += 1
        payload = order_generator.generate(pendulum.now("America/Fortaleza"))
        print(payload["id"])

        producer.send(KAFKA_TOPIC, value=payload)
        producer.flush()

        intervalo = randint(0, set_producer_rate())
        print(f"Próxima venda em {intervalo}s")
        sleep(randint(0, intervalo))


if __name__ == "__main__":
    main()
