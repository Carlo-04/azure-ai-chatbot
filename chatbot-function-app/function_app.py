import azure.functions as func
import azure.identity
import logging
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

from openai import AzureOpenAI
import tiktoken
import json
import os

from Database import Database

# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_SERVICES_ENDPOINT = os.getenv("AZURE_AI_SERVICES_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

MAX_TOKENS = 3000
TEST_USER_ID = "16b8fef2-4058-4654-bbba-6bffe2058d28"
DEFAULT_CHATBOT_PROMPT = """
    You are a friendly retrieval-augmented assistant that serves as a car salesman for a dealership.
    You are in a marketing and sales role, but you cannot give the customer any offers or discounts.
    If the customer asks for offers, invoices or anything related to pricing, you should politely refuse 
    and inform them that you are not authorized to provide such information. You may only give them the listed 
    price of the vehicle and inform them that they can contact the dealership for any offers or discounts.
    Answer the query using only the sources provided in each query in a friendly and concise manner.
    If there isn't enough information below, say you don't know and tell the user to ask questions related to your scope.
    Every message will have the following format:
    query: <user query>, sources:\n<formated list of sources>
    The only exception to this format is when you are asked to summarize the conversation. 
    In this case, rely only on the conversation history.
    Once Initialized, greet the user with a welcome message and introduce yourself.
    If the user is sending a greeting, asking you how are you, or making minor small talk you may reply 
    like a friendly salesman (ignore the sources provided).
    If any of the provided sources are in Arabic, translate them before relaying them to the user. 
    You may only generate responses in English.
    """


def clearTerminal():
    os.system('cls' if os.name == 'nt' else 'clear')

def num_tokens_from_messages(messages):
    encoding = tiktoken.encoding_for_model(AZURE_OPENAI_MODEL_NAME)
    num_tokens = 0
    for message in messages:
        num_tokens += 4  # every message overhead
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
    num_tokens += 2  # every reply overhead
    return num_tokens

def ensureTokenLimit(database, openai_client, search_client, session_id, messages):
    #This function checks if the token limit is almost reached
    #If the limit is almost reached, it summarizes the conversation and creates a new messages list
    #It returns the new/old messages list
    
    if num_tokens_from_messages(messages) >= MAX_TOKENS* 0.8:

        summary_prompt = "Summarize the conversation so far in a concise manner, retaining important details and context. " \
        "The summary should be brief and to the point, capturing the essence of the discussion without unnecessary elaboration. " \
        "The summary will be used to maintain context in future interactions, so ensure it is clear and informative."

        messages.append({
            "role": "user",
            "content": summary_prompt
        })

        messages = sendMessage(database, openai_client, search_client, session_id, messages, False) 

        #last 5 messages + summary will be kept in history. 
        #The rest of the messages will be displayed but not stored within the context window
        if(len(messages) > 10):
            summary_messages = messages[:2] + messages[-7:] 

        else:
            summary_messages = messages[:2] + messages[-2:] #only keep the summary and the system prompt 

        return summary_messages
    
    else:
        return messages


def sendMessage(database, openai_client, search_client, session_id, messages, rag=True):
    #This function is used to handle user messages.
    #It sends the api request to the ai search model then passes the results to the openai model with the user query.
    # and prints the response as it's being generated

    grounded_prompt = """
    Provide an answer to this query while referring to the sources provided. Answer ONLY in english (translate the source if need be). 
    If the user is sending a greeting, asking you how are you, or making minor small talk you may reply 
    like a friendly salesman (ignore the sources provided).\n
    query: {query}, sources:\n{sources}
    """ 
    query = messages[-1]['content']

    if rag: #apply rag. typically used for user messages (except for summarization)

        #embedding the query
        embed_query = openai_client.embeddings.create(
            input=query,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        ).data[0].embedding

        vector_query = VectorizedQuery(
                vector=embed_query,
                k_nearest_neighbors=5,
                fields="text_vector",
                kind="vector",
                exhaustive=True
            )

        #retrieving documents (hybrid search)
        search_results = search_client.search(
                    include_total_count=True,
                    search_text=query,  
                    select="brand,model,type,year,price,chunk,features",
                    top=5,
                    vector_queries=[vector_query]
                )

        sources_formatted = "\n\n".join([
            f"Brand: {doc['brand']}\n"
            f"Model: {doc['model']}\n"
            f"Type: {doc['type']}\n"
            f"Year: {doc['year']}\n"
            f"Price: {doc['price']}\n"
            f"Description: {doc['chunk']}\n"
            f"Features: {', '.join(doc.get('features') or [])}"
            for doc in search_results
        ])

        messages[-1]["content"] = grounded_prompt.format(query=query, sources=sources_formatted)

    full_reply = ""
    response = openai_client.chat.completions.create(
        stream=False,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.75,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    )

    full_reply = response.choices[0].message.content

    #replace the last user message with the original query (without sources in the case of RAG)
    messages[-1]["content"] = query

    #typically the last message is the user's message but sometimes it could be a system message
    database.addMessage(session_id, messages[-1]['role'], messages[-1]['content']) 
    database.addMessage(session_id, "assistant", full_reply)

    messages.append({
        "role": "assistant",
        "content": full_reply
    })
    
    return messages


def initializeClients(user_id):
   
    openai_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_AI_SERVICES_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )

    search_client = SearchClient(
        endpoint=AZURE_SEARCH_ENDPOINT,
        index_name=AZURE_SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(AZURE_SEARCH_API_KEY)
    )
    db = Database(user_id)

    return openai_client, search_client, db
    

############
## Function Apps
###########
app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
@app.function_name(name="HttpChatbotTrigger")
@app.route(route="http_chatbot_trigger", methods=["POST"])
def httpChatbotTrigger(req: func.HttpRequest) -> func.HttpResponse:

    try:
        # Parse request body
        req_body = req.get_json()
        user_id = req_body.get("user_id", TEST_USER_ID)  ##### Default value needs to be removed in production
        session_id = req_body.get("session_id")
        command = req_body.get("command").lower() #this is used to handle special commands like getMessages, clearChat, sendQuery

        if not session_id or not user_id:
            return func.HttpResponse(
                json.dumps({"error": "user_id and session_id are required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        openai_client, search_client, database = initializeClients(user_id)
        messages = database.getMessages(session_id)

        if command == "sendquery":
            query = req_body.get("query")
            rag = req_body.get("rag", True)

            messages.append({
                "role": "user",
                "content": query
            })

            # Call your existing function
            updated_messages = sendMessage(
                database=database,
                openai_client=openai_client,
                search_client=search_client,
                session_id=session_id,
                messages=messages,
                rag=rag
            )
            
            reply = updated_messages[-1]["content"]
            #ensureTokenLimit(database, openai_client, search_client, session_id, updated_messages)  Needs fixing. 
            # I have to call it after retrieving the messages and before sending the prompt
            return func.HttpResponse(
                json.dumps({"reply": reply}, ensure_ascii=False).encode('utf-8'),
                status_code=200,
                mimetype="application/json"
            )
        
        elif command == "getmessages":
            return func.HttpResponse(
                json.dumps({"messages": messages}, ensure_ascii=False).encode('utf-8'),
                status_code=200,
                mimetype="application/json"
            )
        
        elif command == "clearchat":
            
            messages = [
                {
                    "role": "system",
                    "content": DEFAULT_CHATBOT_PROMPT
                }
            ]
            database.clearSession(session_id)
            messages = sendMessage(database, openai_client, search_client, session_id, messages, False)
            return func.HttpResponse(
                json.dumps({"messages": messages}, ensure_ascii=False).encode('utf-8'),
                status_code=200,
                mimetype="application/json"
            )
        
        
        
        

    except Exception as e:
        logging.exception("Error in sendMessage HTTP trigger")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            status_code=500,
            mimetype="application/json"
        )
    
    finally:
        openai_client.close()

