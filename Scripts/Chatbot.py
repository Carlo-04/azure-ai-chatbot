from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.models import VectorizedQuery

from openai import AzureOpenAI
import tiktoken

import os
from dotenv import load_dotenv

from Database import Database

load_dotenv()

# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_SERVICES_ENDPOINT = os.getenv("AZURE_AI_SERVICES_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

MAX_TOKENS = 2500
TEST_USER_ID = os.getenv("TEST_USER_ID")
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
    Once Initialized, greet the user with a welcome message and inform them that they may write "menu", "restart" and "exit" 
    to access the menu, restart the program (no data will be lost) and exit the program respectively.
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
        print("\n/// Token limit almost reached. Summarizing the conversation...\n")
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
    Use ONLY the information from the sources provided to answer to this query.\n
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
        stream=True,
        messages=messages,
        max_tokens=MAX_TOKENS,
        temperature=0.75,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    )

    for update in response:
        if update.choices:
            chunk = update.choices[0].delta.content or ""
            print(chunk, end="", flush=True)  # live printing
            full_reply += chunk #since the response is being streamed, we only get access to chunks at a time
    print()

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

def displayMessages(database, session_id):
    #returns a list of messages [{"role": role, "content": content}, ...]
    #this function retrieves and displays all messages from a specific session
    messages = database.getMessages(session_id)

    for msg in messages:
        if msg['role'] != 'system':

            role = msg['role']
            content = msg['content']
            print(f"\n///{role.capitalize()}: \n{content}")
    return messages

def selectSession(database):
    #returns session_id
    #this function retrieves and displays all sessions for the current user
    #it prompts the user to select a session and returns its id
    sessions = database.getSessions()
    if len(sessions) == 0:
        #There are no sessions
        return None
    
    print("Your Sessions:")
    for idx, session in enumerate(sessions, start=1):
        print(f"{idx}. {session['sessionTitle']}")

    selected_session = input("Select a session by number: ")
    while(not selected_session.isdigit() or int(selected_session) < 1 or int(selected_session) > len(sessions)):
        selected_session = input("Invalid selection. Please select a session by number: ")

    return sessions[int(selected_session) - 1]['id']

def craeteNewSession(database, client):
    #this function creates a new session and returns its id
    session_title = input("Enter a title for the new session: ")
    session_id = database.addSession(session_title)

    return session_id


def displayMenu(database, openai_client, search_client, session_id, messages):
    #returns session_id, messages
    #this function displays the menu and handles user input
    #depending on the user's choice, the session_id and messages may be updated

    
    print("""
    Kindly select an option:
          1. Create New Session
          2. Select Session
          3. Clear Current Session
          4. Delete Session
          """)
    choice = input("Enter your choice (1-5): ")

    if choice == "1": #Create New Session
        #creating a new session on the db and returning its id
        clearTerminal()
        session_id = craeteNewSession(database, openai_client)
        messages = [
            {
                "role": "system",
                "content": DEFAULT_CHATBOT_PROMPT
            }
        ]
        messages = sendMessage(database, openai_client, search_client, session_id, messages, False)

        
    elif choice == "2": #Select Session
        clearTerminal()
        session_id = selectSession(database)
        clearTerminal()

        if(session_id is None):
            print("You have no sessions. Please create a new session first.\n")
            return displayMenu(database, openai_client, search_client, session_id, messages)
        
        messages = displayMessages(database, session_id)
    
    elif choice == "3": #Clear Current Session
        clearTerminal()
        if(session_id is None):
            print("You are not currently in a session. Please select or create a session first.\n")
            return displayMenu(database, openai_client, search_client, session_id, messages)
        
        messages = [
            {
                "role": "system",
                "content": DEFAULT_CHATBOT_PROMPT
            }
        ]
        database.clearSession(session_id)
        print("Current session cleared.\n")
        messages = sendMessage(database, openai_client, search_client, session_id, messages, False)

    elif choice == "4": #Delete Session
        clearTerminal()
        d_session_id = selectSession(database)

        if(d_session_id is None):
            print("You have no sessions. Please create a new session first.\n")
            return displayMenu(database, openai_client, search_client, session_id, messages)
        
        database.deleteSession(d_session_id)
        print("Session deleted.\n")
        return displayMenu(database, openai_client, search_client, session_id, messages)

    else:
        print("Invalid choice. Please try again.")
        return displayMenu(database, openai_client, search_client, session_id, messages)

    return session_id, messages

def runChatbot(openai_client, search_client, database):
    #This function handles the conversation
    #It initializes the messages list and prompts the user for input
    #It calls sendMessage to get the model's response and updates the messages list accordingly
    #It also handles exit and restart commands for the chat session. Dpending on the command, it willr eturn 0 or 1 respectively.
    #If 1 is returned, the main function will call runChatbot again to start a new session

    try:

        session_id = None
        session_id, messages = displayMenu(database, openai_client, search_client, session_id, [])

        #Handeling the conversation
        while True:
            
            user_input = input("\n/// You: ")
            if user_input.lower() == "menu":
                session_id, messages = displayMenu(database, openai_client, search_client, session_id, messages)
                continue

            elif user_input.lower() == "restart":
                print("Restarting the chat session...\n")
                return 1

            elif user_input.lower() == "exit":
                print("Exiting the chat...")
                return 0
            

            messages.append({
                "role": "user",
                 "content": user_input
                })
                            
            messages = sendMessage(database, openai_client, search_client, session_id, messages)

            messages = ensureTokenLimit(database, openai_client, search_client, session_id, messages)

    except Exception as e:
        print("Something went wrong.")
        print(f"Exception details: {e}")

    finally:
        openai_client.close()


def main():

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
    db = Database(TEST_USER_ID)
    
    while(runChatbot(openai_client, search_client, db) == 1): #the loop is used to restart the chat session
        
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
        
        db = Database(TEST_USER_ID)


if __name__ == '__main__':
    main()