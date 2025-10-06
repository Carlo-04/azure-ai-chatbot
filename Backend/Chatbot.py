import azure.identity
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery
import azure.cognitiveservices.speech as speechsdk

from openai import AzureOpenAI
import tiktoken
import json
import os
import requests
import re

import Database

# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")
AZURE_SPEECH_TO_TEXT_ENDPOINT = os.getenv("AZURE_SPEECH_TO_TEXT_ENDPOINT")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

MAX_TOKENS = 4096

DEFAULT_CHATBOT_PROMPT = """
You are a friendly retrieval-augmented assistant acting as a representative for a dealership. 
Your primary role is to assist old or potential customers with their inquiries about vehicles, dealership information, or service-related issues.

You have 3 core capabilities:
1. **Vehicle & Dealership Information (RAG)** — Use the `hybridSearch` function when 
the user asks questions about vehicles, dealership locations, hours, or services.
2. **Customer Support Requests** — Use the `createSupportRequest` function only when 
the user clearly describes a problem or issue they are facing with their vehicle or dealership services.
3. **Natural Conversation & Small Talk** — Respond to greetings, casual conversation, 
and polite chat in a natural, human-like way **without invoking any function**.

---

## Conversation Rules:

1. **Greetings / Small Talk:**
    - If the user's message is a greeting (e.g., “hi”, “hello”, “good morning”, “hey there”) 
    or small talk (e.g., “how are you?”, “nice to meet you”, “good to see you”), respond naturally and **do not call any function**.
    - Example responses:
        - User: “Hi!” → Assistant: “Hello there! How are you today?”
        - User: “Good afternoon, how's it going?” → Assistant: “Good afternoon! I'm doing great, thank you. How about you?”
    - If the greeting is combined with another intent (e.g., “Hi, I need help with my car”), consider utilizing the following functions.

2. **Support Requests:**
    - Required fields for creating a support request:
        1. Vehicle make
        2. Vehicle model
        3. Vehicle year
        4. A brief description of the specific issue (e.g., "the AC isn't working," "the car is making a noise").

    - Alwways check the user's latest mesage for these fields. They must all be present in the user's message history.
    - Only after all fields are collected, ask the customer if they want you to create the support request.
    - Never skip or bypass the field collection step.
    - If the user agrees on a draft that was missing information, once that info is collected, send the new draft for confirmation.


3. **Vehicle & Dealership Info (RAG Search):**
    - When the user asks for information about cars, services, dealership details, or inventory, call the `hybridSearch` function.
    - Use only retrieved information to answer queries.
    - If the user mixes small talk with a vehicle question (e.g., “Hi, can you tell me about the 2024 Civic?”), respond warmly but prioritize the vehicle question.
    - Use ONLY the information provided from the knowledge base to answer questions related to cars for sale at our dealership.
    - You may reformat or organize the information to make it clearer and easier to understand, 
    but do not add, remove, or alter factual content.
    - Provide only the details that directly address the user's query. Omit irrelevant details 
    unless the user explicitly requests them.


---

## Behavioral Guidelines

    - Never call any function for greetings, casual conversation, or small talk.
    - Only call a function if the user explicitly asks for vehicle info or requests support.
    - Do not provide offers, invoices, discounts, financing, appointments, test drives, or promotions unless found explicitly in the knowledge base.
    - If a user is asking about a car or service that isn't in the knowledge base, politely inform the user and suggest contacting the dealership.
    - When asked about dealership details, first check the knowledge base; if unavailable, politely decline.
    - If the user  discussing a problem that they have with their vehicle, prompt them for more information about their issue and rely on previous 
    user messages. In this scenario do not use `hybridSearch` unless the user switches topics and asks about the vehicles at the dealership. 
    NEVER come up with or assume details; rely only on what the user has told you when discussing a problem. When a user is expressing a problem they 
    have with their vehicle, prompt them for any necessary info before calling the request function.
    - On initialization, greet the user warmly, introduce yourself, and do **not** trigger any function calls.
    - Translate non-English sources to English before responding, and always reply in English.
    - You don't have access to the dealership's contact info so if a user requires it, instruct them to find it in the Contact Us page.
    - You may only call one function at a time.
     
---

"""

####################
## Client Initialization
####################
def initializeClients(): 
    openai_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )

    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
    )

    return openai_client, search_client

####################
## Token Counter
####################
def num_tokens_from_messages(messages):
    encoding = tiktoken.encoding_for_model(AZURE_OPENAI_MODEL_NAME)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message overhead
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
    num_tokens += 2  # every reply overhead
    return num_tokens

####################
## Ensuring Token Limit
####################
def ensureTokenLimit(openai_client, search_client, user_id, session_id, messages):
    #This function checks if the token limit is almost reached and if so performs a combination of sliding window and summarization
    #If the limit is almost reached, it summarizes the conversation and creates a new messages list
    #It returns the new/old messages list. If summarized, the message list is only returned with 
    # the summary not the summarization prompt
    
    if num_tokens_from_messages(messages) >= MAX_TOKENS* 0.8 and len(messages)>2:

        summary_prompt = "Summarize the conversation so far in a concise manner, retaining important details and context. " \
        "The summary should be brief and to the point, capturing the essence of the discussion without unnecessary elaboration. " \
        "The summary will be used to maintain context in future interactions, so ensure it is clear and informative."

        messages.append({
            "role": "user",
            "content": summary_prompt
        })

        response = openai_client.chat.completions.create(
            stream=False,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=0.75,
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
        )
        full_reply = response.choices[0].message.content
        messages.pop() #removing the summary prompt
        messages.append({
            "role": "assistant",
            "content": full_reply
        }) 


        #last 5 messages + summary will be kept in history. 
        #The rest of the messages will be displayed but not stored within the context window
        if(len(messages) > 10):
            summary_messages = messages[:2] + messages[-7:] 

        else:
            summary_messages = messages[:2] + messages[-2:] #only keep the summary and the system prompt 

        return summary_messages
    
    else:
        return messages

####################
## Hybrid Search    --  Chatbot Function
####################
def hybridSearch(query):
    #This function is used to perform a hybrid search on the search index with context expansion
    #It returns the search results

    #embedding the query
    openai_client, search_client = initializeClients()
    embed_query = openai_client.embeddings.create(
        input=query,
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
    ).data[0].embedding

    vector_query = VectorizedQuery(
            vector=embed_query,
            k_nearest_neighbors=5,
            fields="content_vector",
            kind="vector",
            exhaustive=True
        )

    search_results = search_client.search(
                include_total_count=True,
                search_text=query,  
                select="id, chunk, file_name, page_number, chunk_index, parent_id",
                top=5,
                vector_queries=[vector_query]
            )

    #fetchin neighbouring chunks (Contextual expansion)
    window= 1 #how many neighbouring chunks do we take from each direction
    expanded_results = []
    ids_in_expanded_results = []
    for doc in search_results:

        if doc["id"] not in ids_in_expanded_results:
            expanded_results.append(doc)
            ids_in_expanded_results.append(doc["id"])

        parent_id = doc["parent_id"]
        chunk_index = doc["chunk_index"]
        neighbor_filter = f"parent_id eq '{parent_id}' and chunk_index ge {chunk_index - window} and chunk_index le {chunk_index + window}"

        neighbors = search_client.search(
            search_text="*",
            filter=neighbor_filter,
            select="id, chunk, file_name, page_number, chunk_index, parent_id"
        )

        for n in neighbors:
            if n["id"] != doc["id"] and n["id"] not in ids_in_expanded_results: 
                expanded_results.append(n)
                ids_in_expanded_results.append(n["id"])

    #formatting results to pass to model
    sources_formatted = "\n\n".join([
        f"chunk: {doc['chunk']}\n"
        f"file_name: {doc['file_name']}\n"
        f"page_number: {doc['page_number']}\n"
        f"chunk_index: {doc['chunk_index']}\n"
        for doc in expanded_results
    ])

    return json.dumps({"vector_search_results": sources_formatted})
    
####################
## Create Customer Support Request    --  Chatbot Function
####################
def createSupportRequest(user_id, subject, description):
    #This function is used to create a customer support request
    #It stores the request in the database and returns a confirmation message
    
    request_id = Database.addSupportRequest(user_id, subject, description)
    return json.dumps({"request_id": request_id, "status": "Support request created successfully."})

####################
## Validate Support Request    --  Chatbot Function Helper
####################
def validateSupportRequest(user_messages, parameters_required, arguments):
    """
    Validates if a user's message contains the required fields for a support request.
    checks the values giving to the make, model, and year parameters and uses a regex to 
    verify that the model didn't hallucinate them.
    returns an array of the missing/false parameters
    """
    missing = []
    for i in range(len(arguments)):
        if arguments[i] is None:
            missing.append(parameters_required[i])
        
        else:
            arg = arguments[i].lower()
            pattern = r'\b' + re.escape(arg) + r'\b'
            if not re.search(pattern, user_messages):
                missing.append(parameters_required[i])
    return missing

####################
## Send Message
####################
def sendMessage(user_id, openai_client, search_client, session_id, messages):
    #This function is used to handle user messages.
    #It sends the api request to the ai search model then passes the results to the openai model with the user query.


    #add the user query
    Database.addMessage(user_id, session_id, messages[-1]['role'], messages[-1]['content']) 

    query = messages[-1]['content']
    latest_message = messages[-1]

    #applying sliding window + summarization to ensure the context window is met
    messages.pop() #removing the query before in case messages needs to be summarized
    messages = ensureTokenLimit(openai_client, search_client, user_id, session_id, messages)
    messages.append(latest_message)

    tools = [
        {
            "type": "function",
            "function": {
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
                    "required": ["query"],
                },
            }
        },        
        {
            "type": "function",
            "function": {
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
                        "user_id": {
                            "type": "string",
                            "description": "The id of the user issuing the support request. This will be passed from the backend. you don't have access to it directly.",
                        },
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
                    "required": ["user_id", "subject", "description"],
                },
            }
        }
    ]

    # First API call: Ask the model to use the functions
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        temperature=0.5,
        max_tokens=MAX_TOKENS,
        tools=tools,
        tool_choice="auto",
        )

    response_message = response.choices[0].message
    messages.append(response_message)

    # Handle function calls
    if response_message.tool_calls:
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            if function_name == "hybridSearch":
                function_response = hybridSearch(
                    query=function_args.get("query")
                )
            elif function_name == "createSupportRequest":
                #checking if the user provided all the required details throughout the conversation (accounting for hallucinations)
                user_messages = " ".join([m['content'] for m in messages[:-1] if m.get('role') == "user"]).lower()
                parameters_required = ["model", "make", "year"]
                arguments = [function_args.get(param, None) for param in parameters_required]
                missing = validateSupportRequest(user_messages, parameters_required, arguments)

                if len(missing)>0:
                    # Prompt the user for missing fields instead of creating the request
                    followup_prompt = f"Thank you for your cooperation. In order for me to create your support request, I need you to provide me with: {', '.join(missing)}."
                    "\n Kindly type out the term as it is formally defined (might contain a \"-\" or special characters) "
                    messages.append({
                        "role": "assistant",
                        "content": followup_prompt
                    })
                    Database.addMessage(user_id, session_id, "assistant", followup_prompt)
                    return messages
                else:
                    function_response = createSupportRequest(
                        user_id=user_id,
                        subject=function_args.get("subject"),
                        description=function_args.get("description")
                    )
            else:
                function_response = json.dumps({"error": "Unknown function"})
            
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": function_response,
            })

        # Second API call: Get the final response from the model
        final_response = openai_client.chat.completions.create(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
            messages=messages,
            temperature=0.8,
            max_tokens=MAX_TOKENS,
        )

        full_reply = final_response.choices[0].message.content
        Database.addMessage(user_id, session_id, "assistant", full_reply)

        messages.append({
            "role": "assistant",
            "content": full_reply
        })
        
        return messages
    
    else: #if the first API call decided not to call a fucntion
        reply = response_message.content
        Database.addMessage(user_id, session_id, "assistant", reply)

        messages.append({
            "role": "assistant",
            "content": reply
        })
        
        return messages

####################
## Send Message Helper
####################
def sendMessageHelper(user_id, session_id, query):
    
    openai_client, search_client = initializeClients()
    messages = Database.getMessages(user_id=user_id, session_id=session_id)

    messages.append({
        "role": "user",
        "content": query
    })

    # Call your existing function
    updated_messages = sendMessage(
        user_id=user_id,
        openai_client=openai_client,
        search_client=search_client,
        session_id=session_id,
        messages=messages,
    )
    
    reply = updated_messages[-1]["content"]
    openai_client.close()
    return reply

###################
## Initialize Chat
###################
def initializeChat(user_id, session_id):
    """
    Initializes a new chat session with a greeting message from the assistant
    Mainly used when creating a new session and clearing the session
    """
    openai_client, search_client = initializeClients()
    messages = [
                {
                    "role": "system",
                    "content": DEFAULT_CHATBOT_PROMPT
                }
            ]
    
    full_reply = ""
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.75,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME,
        )

    full_reply = response.choices[0].message.content

    Database.addMessage(user_id, session_id, messages[-1]['role'], messages[-1]['content']) 
    Database.addMessage(user_id, session_id, "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
        
    openai_client.close()
    return messages


def listMessages(user_id, session_id):
        return Database.getMessages(user_id=user_id, session_id=session_id)

###################
## Create Session
###################
def createSession(user_id, session_name):

    new_session_id = Database.addSession(user_id, session_name)
    initializeChat(user_id, new_session_id)
    return new_session_id


###################
## Clear Chat
###################
def clearChat(user_id, session_id):

    Database.clearSession(user_id=user_id, session_id=session_id)
    messages = initializeChat(user_id, session_id)
    return messages

        
###################
## Speech To Text
###################
def transcribeAudio(file):
    """
    Sends an audio file to Azure AI Foundry Fast Transcription service
    and returns the transcript (string or JSON).
    """

    url = f"{AZURE_AI_FOUNDRY_ENDPOINT}/speechtotext/transcriptions:transcribe?api-version=2024-11-15"
    headers = {
        "Ocp-Apim-Subscription-Key": AZURE_OPENAI_API_KEY,
        "Accept": "application/json"
    }

    # Attach audio + transcription definition
    files = {
        "audio": (file.filename, file.stream, file.content_type),
        "definition": (
            None,
            '{"locales":["en-US"],'
            '"profanityFilterMode":"Masked",'
            '"channels":[0,1]}',
            "application/json"
        )
    }

    response = requests.post(url, headers=headers, files=files)
    response.raise_for_status()

    response_json = response.json()
    combined_phrases = response_json.get('combinedPhrases')
    transcript = combined_phrases[0].get('text')
    # Extract text if available, else return raw JSON
    return transcript

###################
## Text To Speech
###################
def generateAudio(text):
    #Takes a string and returns the audio content as raw bytes

    endpoint = os.getenv("AZURE_TEXT_TO_SPEECH_ENDPOINT")
    speech_config = speechsdk.SpeechConfig(subscription=AZURE_OPENAI_API_KEY, 
                                           endpoint=endpoint)
    speech_config.speech_synthesis_voice_name = "en-US-BrandonMultilingualNeural"
    
    speech_config.set_speech_synthesis_output_format(
        speechsdk.SpeechSynthesisOutputFormat.Audio16Khz32KBitRateMonoMp3
    )
    synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
    
    result = synthesizer.speak_text_async(text).get()

    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        
        audio_stream = speechsdk.AudioDataStream(result)
        audio_bytes = bytearray()

        chunk_size = 4096
        buffer = bytes(chunk_size) 

        while True:
            size_filled = audio_stream.read_data(buffer)
            if size_filled == 0:
                break
            audio_bytes.extend(buffer[:size_filled])
        return bytes(audio_bytes)

    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        raise RuntimeError(
            f"Speech synthesis canceled: {cancellation_details.reason}, "
            f"details: {cancellation_details.error_details}"
        )
