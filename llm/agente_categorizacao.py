import os
import json
from dotenv import load_dotenv
from pymongo import MongoClient
from bson.objectid import ObjectId
from agno.agent import Agent, RunResponse  # , AgentKnowledge
from agno.models.groq import Groq
from agno.models.openai import OpenAIChat
from motoristas import get_motoristas

# from agno.utils.pprint import pprint_run_response
# from agno.storage.sqlite import SqliteStorage
from agno.tools.reasoning import ReasoningTools

# from agno.tools.tavily import TavilyTools
# from agno.tools.duckdb import DuckDbTools

load_dotenv()


def categorize_order(order: dict) -> str:

    agent = Agent(
        # model=Groq(id="llama-3.3-70b-versatile"),
        model=OpenAIChat(id="gpt-4o-mini"),
        session_id="fixed_id_for_demo",
        tools=[
            # ReasoningTools(add_instructions=True),
        ],
        # Prompt
        description="Você é um agente especialista em roteirização logística. Seu objetivo é analisar qual seria o melhor motorista para realizar a entrega de um pedido, com base na lista de motoristas disponíveis.",
        goal="Seu objetivo é escolher qual das rotas disponíveis é a melhor para um determinado pedido",
        instructions=[
            "A capacidade total de cada veículo e a quantidade de unidades já alocadas.",
            "A proximidade do endereço de origem do motorista em relação ao endereço do pedido.",
            "Priorize motoristas que atuem no mesmo estado do pedido, sempre que possível.",
            'Se nenhum motorista for adequado, retorne mesmo assim um JSON completo com todos os campos do pedido preenchidos. Os campos de motorista devem ser preenchidos com string vazia (`""`), e o campo "motivo_escolha" deve explicar claramente o porquê da não atribuição.',
            'Se o campo "estado" do motorista estiver ausente, preencha com o estado do endereço do pedido.',
            "Quando não tem uma rota para cidade específica, use uma rota que vai para região que aquela cidade está inserida",
            """Não use notação de markdow""",
            'Retorne apenas um JSON válido, sem explicações ou comentários. O JSON deve conter as seguintes chaves: "pedido_id", "motorista_id", "motorista_nome", "tipo_veiculo", "capacidade_total_unidades", "quantidade_atual", "endereco_origem_motorista", "estado", "local_previsto_nova_entrega", "motivo_escolha".',
            """Saída esperada: {
                "pedido_id": "ORDE_244834e9-23f3-45db-a478-5794ff654c76",
                "motorista_id": "<id do motorista>",
                "motorista_nome": "< Nome do motorista>",
                "tipo_veiculo": "<modelo do veículo>",
                "capacidade_total_unidades": "<capacidade em quantidade de itens>",
                "quantidade_atual": "<quantidade de itens já destinados a esse carro>",
                "endereco_origem_motorista": "<endereço de partida do motorista>",
                "estado": "<estado de destino do pedido>",
                "local_previsto_nova_entrega": "<endereco que veio no pedido>",
                "motivo_escolha": "<explicação>"
                }""",
        ],
        additional_context=get_motoristas(),
        
        expected_output="""Saída esperada: {
                "pedido_id": "ORDE_244834e9-23f3-45db-a478-5794ff654c76",
                "motorista_id": "<id do motorista>",
                "motorista_nome": "< Nome do motorista>",
                "tipo_veiculo": "<modelo do veículo>",
                "capacidade_total_unidades": "<capacidade em quantidade de itens>",
                "quantidade_atual": "<quantidade de itens já destinados a esse carro>",
                "endereco_origem_motorista": "<endereço de partida do motorista>",
                "estado": "<estado exemplo MT>",
                "local_previsto_nova_entrega": "Loteamento Ana Clara Leão, nº 2, apto 701 - da Rosa/MT",
                "motivo_escolha": "Nenhum motorista disponível com capacidade suficiente ou no mesmo estado."
                }""",
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


def inserir_documento(colecao_nome, json_doc):
    db = conectar_mongodb()
    collection = db[colecao_nome]
    resultado = collection.insert_one(json_doc)
    print(f"Documento inserido com ID: {resultado.inserted_id}")
    return resultado.inserted_id


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

            resposta_llm = categorize_order(documento)

            try:
                colecao_nome = os.getenv("KAFKA_LLM_TOPIC", "output_llm")
                doc_categorizado = json.loads(resposta_llm)
                print(doc_categorizado)
                inserir_documento(colecao_nome, doc_categorizado)
            except Exception as e:
                print("ERRO:", e)
