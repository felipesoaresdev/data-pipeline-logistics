import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from agno.agent import Agent, RunResponse  # , AgentKnowledge
from agno.models.groq import Groq

# from agno.utils.pprint import pprint_run_response
# from agno.storage.sqlite import SqliteStorage
from agno.tools.reasoning import ReasoningTools

# from agno.tools.tavily import TavilyTools
# from agno.tools.duckdb import DuckDbTools

load_dotenv()


def categorize_order(order: dict) -> str:

    agent = Agent(
        model=Groq(id="llama-3.3-70b-versatile"),
        session_id="fixed_id_for_demo",
        tools=[
            # ReasoningTools(add_instructions=True),
        ],
        # Prompt
        description="Você é um agente especialista em categorização de logistica",
        goal="Seu objetivo é escolher qual das rotas disponíveis é a melhor para um determinado pedido",
        instructions=[
            "Levem em consideração a capacidade disponível. '10/20' significa que já tem 10 entregas de uma capacidade de 20.",
            "Quando não tem uma rota para cidade específica, use uma rota que vai para região que aquela cidade está inserida",
            """Não use notação de markdow""",
            'Retorne apenas um JSON válido, sem explicações ou comentários. O JSON deve ter as seguintes chaves: "id_motorista", "id_rota", "destino", "lista_produtos".'
            """Saída esperada: {"id_motorista":"MT_0000", "id_rota": RT_0000, "destino": Parnaíba-PI, "lista_produtos": ["Celular", "Camisa", "Sapato"]}""",
        ],
        additional_context="""

        ## Rota 1:
        - id_rota: RT_0085
        - id_motorista: MT_0001
        - motorista: José
        - destino: Fortaleza - CE
        - capacidade: 20/25

        ## Rota 2:
        - id_rota: RT_0011
        - id_motorista: MT_0002
        - motorista: Alex
        - destino: São Paulo - SP
        - capacidade: 25/25

        ## Rota 3:
        - id_rota: RT_0012
        - id_motorista: MT_0003
        - motorista: Carlos
        - destino: São José dos Campos - SP
        - capacidade: 20/25

        ## Rota 4:
        - id_rota: RT_0011
        - id_motorista: MT_0004
        - motorista: Antônio
        - destino: São Paulo - SP
        - capacidade: 10/25

        ## Rota 5:
        - id_rota: RT_0013
        - id_motorista: MT_0005
        - motorista: Antônio Filho
        - destino: Região Nordeste
        - capacidade: 19/25
        - observação: rota mais lenta

        ## Rota 6:
        - id_rota: RT_0014
        - id_motorista: MT_0006
        - motorista: Catiuce
        - destino: Região Sudeste
        - capacidade: 16/25
        - observação: rota mais lenta

        Seja cuidadoso, uma carga enviada para o destino errado pode custar bastante para empresa
        """,
        expected_output='JSON válido, sem explicações ou comentários. O JSON deve ter as seguintes chaves: "id_motorista", "id_rota", "destino", "lista_produtos".',
        # system_message = "Seja", # Substitui todo o prompt do distema, anulando description, goal, instructions, additional_context e expected_output
        # Tentar novamente
        exponential_backoff=True,
        retries=2,
        # show_tool_calls=True,
        # markdown=True,
    )

    try:
        pedido_str = json.dumps(order)
        response: RunResponse = agent.run(pedido_str, stream=False)
        return response.content
    except Exception as e:
        print(e)
        return None


# Conecta no MongoDB e retorna o banco
def conectar_mongodb(db_name="meu_banco"):
    host = os.getenv(
        "MONGODB_HOST", "localhost:27017"
    )  # valor padrão caso a variável não exista
    client = MongoClient(f"mongodb://{host}")
    db = client[db_name]  # nome do banco
    return db


# Função para buscar documento no MongoDB pelo filtro em uma coleção específica
def buscar_documento_no_intervalo(colecao_nome, inicio_corte, fim_corte) -> list | None:

    # Converter datetime para ObjectId
    object_id_inicio = ObjectId.from_datetime(inicio_corte)
    object_id_fim = ObjectId.from_datetime(fim_corte)

    # Buscar documentos com _id no intervalo [início, fim)
    filtro = {"_id": {"$gte": object_id_inicio, "$lt": object_id_fim}}

    db = conectar_mongodb()
    collection = db[colecao_nome]
    documentos = collection.find(filtro)
    if documentos is not None:
        return list(documentos)
    else:
        print("Documento não encontrado.")
        return None


if __name__ == "__main__":
    from datetime import datetime, timedelta, timezone

    MONGODB_COLLECTION = os.getenv("MONGODB_COLLECTION", "staging")

    # Obter o tempo atual e calcular o intervalo de 10 minutos
    fim_corte = datetime.now(timezone.utc)
    inicio_corte = fim_corte - timedelta(minutes=10)

    docs = buscar_documento_no_intervalo(MONGODB_COLLECTION, inicio_corte, fim_corte)

    if docs is not None:
        for documento in docs:
            if "_id" in documento and isinstance(documento["_id"], ObjectId):
                documento["_id"] = str(documento["_id"])

            doc_categorizado = json.loads(categorize_order(documento))
            print(doc_categorizado)
