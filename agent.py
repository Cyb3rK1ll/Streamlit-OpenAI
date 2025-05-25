from __future__ import annotations
import logging
import os
import asyncio
from dotenv import load_dotenv


from openai import AsyncAzureOpenAI, OpenAI, AsyncOpenAI
from agents import Agent, HandoffInputData, Runner, function_tool, handoff, trace, set_default_openai_client, set_tracing_disabled, OpenAIChatCompletionsModel, set_tracing_export_api_key, add_trace_processor
from agents.tracing.processors import ConsoleSpanExporter, BatchTraceProcessor, _global_processor
from agents.extensions import handoff_filters
from agents import set_trace_processors

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

load_dotenv()

azure_openai_client = AsyncAzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT")
)

azure_apim_openai_client = AsyncAzureOpenAI(
    default_headers={"Ocp-Apim-Subscription-Key": os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY")},
    api_key=os.getenv("AZURE_APIM_OPENAI_SUBSCRIPTION_KEY"),
    api_version=os.getenv("AZURE_APIM_OPENAI_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_APIM_OPENAI_ENDPOINT")
)

OpenAiClientApi = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

openai_client = OpenAiClientApi

set_default_openai_client(openai_client)
set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
console_exporter = ConsoleSpanExporter()
console_processor = BatchTraceProcessor(console_exporter)
add_trace_processor(console_processor)
set_tracing_disabled(False)  # Enable tracing

def agent_handoff_message_filter(handoff_message_data: HandoffInputData) -> HandoffInputData:
    handoff_message_data = handoff_filters.remove_all_tools(handoff_message_data)
    return handoff_message_data

cloudflare_agent = Agent(
    name="Cloudlflare Specialist",
    instructions="""
    Eres un especialista en configuración y seguridad en Cloudflare. 

    Indicaciones:
    - Solo hablarás de temas relacionados a Cloudflare.

    SI EL CONTENIDO ESTÁ FUERA DE TU ALCANCE, IR A 'Customer Service Agent'.
    """,
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    tools=[],
)

customer_service_agent = Agent(
    name="Customer Service Agent",
    instructions="""
    Eres un agente de servicio al analista de soporte.

    Tu objetivo es ayudar al analista de soporte a hacer su trabajo:
    - Si el analista pregunta sobre Cloudflare, transfiera al Cloudflare Specialist.

    NO LE DIGAS AL USUARIO QUE LO TRANSFERIRÁS A OTRO AGENTE.

    Sé profesional, amable y servicial.
    """,
    model=OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=openai_client
    ),
    handoffs=[
        handoff(cloudflare_agent, input_filter=agent_handoff_message_filter),
    ],
    tools=[],
)

# Eliminado para evitar handoff circular:
# panalab_cloudflare_agent.handoffs.append(customer_service_agent)

async def get_response(
    agent: Agent,
    conversation_id: str,
    history: list[dict[str, str]],
    user_input: str,
) -> tuple[Agent, str, list[dict[str, str]], str]:
    with trace(workflow_name="Agent Demo", trace_id=f"trace_{conversation_id}", group_id=conversation_id):
        input = history + [{"content": user_input, "role": "user"}]
        result = await Runner.run(
            agent,
            input=input
        )
        updated_history = result.to_input_list()
        return result.last_agent, conversation_id, updated_history, result.final_output
