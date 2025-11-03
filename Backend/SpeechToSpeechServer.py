import asyncio
import base64
import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import websockets
from dotenv import load_dotenv

from ChatbotFunctions import hybridSearch, createSupportRequest
from CustomerServiceDb import queryUserVehicles
load_dotenv()


AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_WSS_ENDPOINT = os.getenv("AZURE_OPENAI_WSS_ENDPOINT")

# default prompt and tools aren't imported because the speechToSpeech page doesn't support image generation
DEFAULT_CHATBOT_PROMPT = """
You are a friendly retrieval-augmented assistant acting as a representative for a dealership. 
Your primary role is to assist old or potential customers with their inquiries about vehicles, dealership information, or service-related issues.

You have 3 core capabilities:
1. **Vehicle & Dealership Information (RAG)** — Use the `hybridSearch` function when 
the user asks questions about vehicles, dealership locations, hours, or services.
2. **Customer Support Requests** — Use the `createSupportRequest` function only when 
the user clearly describes a problem or issue they are facing with their vehicle or dealership services.
3. **User Vehicles Query** — Use the `queryUserVehicles` function to get information about the user's owned vehicles

---

## Conversation Rules:

2. **Support Requests:**
    - Required fields for creating a support request:
        1. Vehicle make
        2. Vehicle model
        3. Vehicle year
        4. A brief description of the specific issue (e.g., "the AC isn't working," "the car is making a noise").

    - Always check the user's messages for these fields.
    - You have access to a queryUserVehicles function that can help you get the user's vehicle information, 
    you may use it to limit the necessary fields to ask the user. Always use this function prior to prompting the user for more info
    - Only after all fields are collected, ask the customer if they want you to create the support request.
    - Whenever the user provides any extra information, use the queryUserVehicles function to check if you 
    can get any vehicle details using the current info (assuming you require more info).
    - If the user agrees on a draft that was missing information, once that info is collected, send the new draft for confirmation.


3. **Vehicle & Dealership Info (RAG Search):**
    - When the user asks for information about cars, services, dealership details, or inventory, call the `hybridSearch` function.
    - Use only retrieved information to answer queries.

4. **User Vehicles Query:**
    - Whenever a user expresses an issue with their vehicle, before asking for more information, use 
    the `queryUserVehicles` function to get details about the user's owned vehicles (use any info that you have at this point).
    - You have access to a `queryUserVehicles` function that retrieves the user's owned vehicles.
    - You may use information already provided by the user to have the function filter results by make, model, and year.
    - If the user has a single vehicle, you can assume that is the vehicle they are referring to in their support request.

---

## Behavioral Guidelines

    - Do not provide offers, invoices, discounts, financing, appointments, test drives, or promotions unless found explicitly in the knowledge base.
    - If a user is asking about a car or service that isn't in the knowledge base, politely inform the user and suggest contacting the dealership.
    - When asked about dealership details, first check the knowledge base; if unavailable, politely decline.
    - If the user  discussing a problem that they have with their vehicle, prompt them for more information about their issue and rely on previous 
    user messages. In this scenario do not use `hybridSearch` unless the user switches topics and asks about the vehicles at the dealership. 
    NEVER come up with or assume details; rely only on what the user has told you when discussing a problem. When a user is expressing a problem they 
    have with their vehicle, prompt them for any necessary info before calling the request function.
    - Only speak the language that's being spoken by the user.

"""

TOOLS = [
        {
            "type": "function",
            "name": "hybridSearch",
            "description": "Performs hybrid search on the search index to retrieve relevant documents. Useful for when you need to find relevant information in the knowledge base to answer the query.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The user prompt that was sent to the chat completion model. It the last user message.",
                        },
                    },
                    "required": ["query"]
                }
        },   
        {
            "type": "function",
            "name": "queryUserVehicles",
                "description": """
                Queries the database for vehicles owned by the user.
                You can provide optional filters such as make, model, and year to narrow down the results
                Useful for when you need to know what vehicles the user owns in order to create a support request.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "This is the model of the vehicle owned by the user.",
                        },
                        "make": {
                            "type": "string",
                            "description": "This is the make of the vehicle owned by the user.",
                        },
                        "year": {
                            "type": "string",
                            "description": "This is the year of the vehicle owned by the user",
                        },
                    },
                    "required": []
                }
        },     
        {
            "type": "function",
            "name": "createSupportRequest",
                "description": """
                Creates a customer support request in the database.
                Useful for when the user wants to create a support request regarding an issue they are facing.
                If you don't have enough information to assist the user or if the user needs actual physical assistance,
                you should create a support request by calling this function.
                """,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "subject": {
                            "type": "string",
                            "description": "This is a title (a brief sentence) summarizing the user's issue. You generate it from the conversation.",
                        },
                        "description": {
                            "type": "string",
                            "description": "A detailed description of the user's issue (under 120 words). You generate it from the user message history. "
                            "It should include the vehicle make, model, year, and issue description EXACTLY as provided by the customer (no added details).",
                        },
                        "model": {
                            "type": "string",
                            "description": "This is the model of the vehicle owned by the user.",
                        },
                        "make": {
                            "type": "string",
                            "description": "This is the make of the vehicle owned by the user.",
                        },
                        "year": {
                            "type": "string",
                            "description": "This is the year of the vehicle owned by the user",
                        },
                    },
                    "required": ["subject", "description", "model", "make", "year"]
                }
        }
    ]


########################
## Server code starts
####################
app = FastAPI()

async def forwardAudioChunk(gpt_ws, pcm16_bytes):
    event = {
        "type": "input_audio_buffer.append",
        "audio": base64.b64encode(pcm16_bytes).decode("utf-8")
    }
    await gpt_ws.send(json.dumps(event))

@app.websocket("/ws/realtime")
async def websocketEndpoint(ws: WebSocket):
    await ws.accept()
    # CLIENT CONNECTED
    
    # Establish GPT Realtime connection
    gpt_ws = await websockets.connect(
        AZURE_OPENAI_WSS_ENDPOINT,
        additional_headers=[("api-key", AZURE_OPENAI_API_KEY)]
    )
    # CONNECTED TO GPT REALTIME

    # Send session config
    session_update = {
        "type": "session.update",
        "session": {
            "voice": "alloy",
            "instructions": DEFAULT_CHATBOT_PROMPT,
            "modalities": ["text", "audio"],  
            "turn_detection": {"type": "server_vad"},
            "tools": TOOLS,
            "tool_choice": "auto"
        }
    }
    await gpt_ws.send(json.dumps(session_update))

    await ws.send_text("ready")

    #get user_id from the client
    user_id = await ws.receive_text()

    ################
    ## From GPT To Client
    ##############
    async def recvFromGpt():
        try:
            async for message in gpt_ws:
                server_event = json.loads(message)

                # forward audio chunk to client
                if server_event.get("type") == "response.audio.delta":
                    delta = server_event.get("delta")
                    if delta:
                        await ws.send_bytes(base64.b64decode(delta))
                # forward transcript chunk to client
                elif server_event.get("type") == "response.audio_transcript.delta":
                    delta = server_event.get("delta")
                    response_id = server_event.get("response_id")
                    await ws.send_json({"response_id": response_id, "transcript_delta": delta})

                # Function Calls
                elif server_event.get("type") == "response.output_item.done":
                    if server_event.get("item").get("type") == "function_call":
                        function_details = server_event.get("item")
                        await ws.send_text("function_in_progress")  #notify client that their request is in progress
                        
                        #RAG: Hybrid Search
                        if function_details.get("name") == "hybridSearch":
                            search_results = hybridSearch(json.loads(function_details.get("arguments")).get("query"))
                            model_response = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": function_details.get("call_id"),
                                    "output": search_results
                                }
                            }
                            await gpt_ws.send(json.dumps(model_response))
                            await gpt_ws.send(json.dumps({"type": "response.create"}))

                        #Support Request
                        elif function_details.get("name") == "createSupportRequest":
                            args = json.loads(function_details.get("arguments"))
                            request_results = createSupportRequest(user_id, args.get("subject"), args.get("description"))
                            model_response = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": function_details.get("call_id"),
                                    "output": request_results
                                }
                            }
                            await gpt_ws.send(json.dumps(model_response))
                            await gpt_ws.send(json.dumps({"type": "response.create"}))

                        elif function_details.get("name") == "queryUserVehicles":
                            args = json.loads(function_details.get("arguments"))
                            vehicle_results = queryUserVehicles(
                                user_id, 
                                make=args.get("make", None), 
                                model=args.get("model", None), 
                                year=args.get("year", None)
                            )
                            model_response = {
                                "type": "conversation.item.create",
                                "item": {
                                    "type": "function_call_output",
                                    "call_id": function_details.get("call_id"),
                                    "output": json.dumps(vehicle_results)
                                }
                            }
                            await gpt_ws.send(json.dumps(model_response))
                            await gpt_ws.send(json.dumps({"type": "response.create"}))
                    
                else:
                    print("Received event:", json.dumps(server_event, indent=2))
        
        except Exception as e:
            print(f"❌ Client disconnected: {e}")
            return
                

    ################
    ## From Client To GPT
    ##############
    async def recvFromClient():
        try:
            while True:
                message = await ws.receive()

                if message["type"] == "websocket.receive":
                    if "text" in message:
                        text_data = message.get("text")

                    elif "bytes" in message:
                        pcm16_bytes = message.get("bytes")
                        await forwardAudioChunk(gpt_ws, pcm16_bytes)

                elif message["type"] == "websocket.disconnect":
                    print("❌ WebSocket disconnected")
                    break

        except Exception as e:
            print(f"❌ Client disconnected: {e}")
            return

    # Run both tasks concurrently
    client_input_task = asyncio.create_task(recvFromClient())
    gpt_input_task = asyncio.create_task(recvFromGpt())

    await asyncio.gather(client_input_task, gpt_input_task)

    print("🔒 WebSocket connection closed")

    #uvicorn SpeechToSpeechServer:app --reload --host 0.0.0.0 --port 8000