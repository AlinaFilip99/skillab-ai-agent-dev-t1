from dotenv import load_dotenv
load_dotenv()  # Încarcă variabilele din .env în os.environ

import asyncio
import signal
import os
import gradio as gr
import pprint

from prompts.registry import PromptRegistry
from tools.tool_wrapper import ToolWrapper
from langchain_google_genai import ChatGoogleGenerativeAI

from langchain_core.messages import (
    BaseMessage, SystemMessage, HumanMessage, ToolMessage
)

_shutdown = False
google_api_key = os.environ.get("GOOGLE_API_KEY")

# Variabilă la nivel de modul = cache pentru instanță
_registry: PromptRegistry | None = None

def get_prompt_registry() -> PromptRegistry:
    global _registry

    # Prima apelare: creează instanța
    if _registry is None:
        _registry = PromptRegistry(folder="prompts/")

    # Apelările următoare: returnează aceeași instanță
    return _registry

def _handle_shutdown(signum, frame):
    global _shutdown
    if _shutdown:
        # Al doilea Ctrl+C → exit imediat
        raise SystemExit(1)
    _shutdown = True
    print("\nFinishing iteration... (Ctrl+C again to force)")

signal.signal(signal.SIGINT, _handle_shutdown)

# # ------ Simple qa chatbot (tools + prompts) ------
# # --- START ---
# class QAAgent:
#     """Agent conversational cu istoric."""
    
#     def __init__(self, **kwargs):
#         self.llm = self.create_llm(**kwargs)

#         prompt_registry = get_prompt_registry()
#         self.registry = prompt_registry

#     def create_llm(self, **kwargs):
#         llm = ChatGoogleGenerativeAI(
#             model="gemini-3.5-flash-lite", google_api_key=google_api_key, **kwargs)
#         return llm

#     def run_prompt(self, prompt_name: str, **kwargs) -> str:
#         prompt = self.registry.render(
#             prompt_name,
#             **kwargs
#         )

#         response = self.llm.invoke([
#             HumanMessage(content=prompt)
#         ])

#         return response.text

#     def create_plan(self, user_input: str) -> str:
#         return self.run_prompt(
#             "planner",
#             user_input=user_input
#         )

#     def extract(
#         self,
#         user_input: str,
#         plan: str
#     ) -> str:

#         return self.run_prompt(
#             "extractor",
#             user_input=user_input,
#             plan=plan
#         )

#     def analyze(
#         self,
#         user_input: str,
#         information: str
#     ) -> str:

#         return self.run_prompt(
#             "analyst",
#             user_input=user_input,
#             information=information
#         )

#     def summarize(
#         self,
#         user_input: str,
#         analysis: str,
#         max_words: int = 150
#     ) -> str:

#         return self.run_prompt(
#             "summarizer",
#             user_input=user_input,
#             analysis=analysis,
#             max_words=max_words
#         )

#     def answer(self, user_input: str) -> str:
#         plan = self.create_plan(user_input)

#         information = self.extract(
#             user_input,
#             plan
#         )
        
#         analysis = self.analyze(
#             user_input,
#             information
#         )
        
#         return self.summarize(
#             user_input,
#             analysis
#         )
#     # Execuție (Python)
#     async def execute_all_tools(self, tool_calls: list) -> list:
#         # Lansăm toate tool-urile simultan, nu așteptăm pe rând
#         tasks = [self.execute_tool_async(tc) for tc in tool_calls]
#         return await asyncio.gather(*tasks)
    
#     async def execute_tool_async(self,tool_call: dict) -> dict:
#         name = tool_call["name"]
#         args = tool_call["args"]
#         # Rulăm tool-ul sincron într-un thread separat
#         rezultat = await asyncio.to_thread(ToolWrapper.call, name, args)
#         return {"tool_call_id": tool_call["id"], "content": str(rezultat)}


# qa_chatbot = QAAgent()

# def generate_response(message: str) -> str:
#     chatbot_response = qa_chatbot.answer(message)
#     return chatbot_response

# # Create Gradio interface
# agent_application = gr.Interface(
#     fn=generate_response,
#     inputs=[
#         gr.Textbox(label="Input", lines=2, placeholder="Type your question here...")
#     ],
#     outputs=gr.Textbox(label="Output"),
#     title="Chatbot"
# )

# # Launch the app
# agent_application.launch(server_name="127.0.0.1", server_port=7860)

# # --- END ---


# ------ ReAct QA chatbot ------
# --- START ---
class ReActQAAgent:
    """ReAct agent conversational cu istoric."""
    
    def __init__(self,  **kwargs):
        self.llm = self.create_llm_with_tools(**kwargs)

        prompt_registry = get_prompt_registry()
        system_prompt = prompt_registry.render(
            "ask_ai_system",
            role="legal expert",
            field="labor law",
            max_words=150
        )

        self.history: list[BaseMessage] = [SystemMessage(content=system_prompt)] # lista goala la start

    def create_llm_with_tools(self, **kwargs):
        llm = ChatGoogleGenerativeAI(
            model="gemini-3.5-flash-lite", google_api_key=google_api_key, **kwargs)
        tools = ToolWrapper.catalog_google()
        return llm.bind_tools(tools)

    def react_loop(self, message,  max_iterations: int = 5) -> str:
        self.history.append(HumanMessage(content=message))
        # Loop Think → Act → Observe
        for _ in range(max_iterations):
            # Verifică shutdown înainte de fiecare iterație
            if _shutdown:
                return "Interrupted — partial response."
            raspuns = self.llm.invoke(self.history)
            self.history.append(raspuns)


            # Dacă LLM-ul nu mai cere tool-uri → răspuns final
            if not raspuns.tool_calls:
                # self.history.append(AIMessage(content=raspuns.content))
                return raspuns.content

            rezultate = asyncio.run(self.execute_all_tools(raspuns.tool_calls))
            # Altfel, execută toate tool-urile cerute (Act)
            for rezultat in rezultate:
                # Observe: trimitem rezultatul înapoi la LLM
                self.history.append(ToolMessage(
                    tool_call_id=rezultat["tool_call_id"],
                    content=rezultat["content"]
                ))
        
        raise RuntimeError("Max iterations reached — LLM did not finish.")
    
    # Execuție (Python)
    async def execute_all_tools(self, tool_calls: list) -> list:
        # Lansăm toate tool-urile simultan, nu așteptăm pe rând
        tasks = [self.execute_tool_async(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)

    async def execute_tool_async(self,tool_call: dict) -> dict:
        name = tool_call["name"]
        args = tool_call["args"]
        # Rulăm tool-ul sincron într-un thread separat
        rezultat = await asyncio.to_thread(ToolWrapper.call, name, args)
        return {"tool_call_id": tool_call["id"], "content": str(rezultat)}


react_chatbot = ReActQAAgent()

def generate_response(message: str, history: list) -> str:
    chatbot_response: str
    try:
        chatbot_response = react_chatbot.react_loop(message)
    except Exception as e:
        chatbot_response = f"Error during response generation: {e}"
        
    return chatbot_response

# Create Gradio interface
rag_application = gr.ChatInterface(
    fn=generate_response,
    chatbot=gr.Chatbot(height=300),
    textbox=gr.Textbox(placeholder="Ask something...", container=False, scale=7),
    title="Chatbot with Tools",
)

# Launch the app
rag_application.launch(server_name="127.0.0.1", server_port=7860)

# --- END ---