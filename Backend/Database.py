from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError

import uuid
from datetime import datetime, timezone
import os
import bcrypt



COSMO_DB_URI = os.getenv("COSMO_DB_URI")
COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")

# Initialize Cosmos client only when instance is created
client = CosmosClient(COSMO_DB_URI, credential=COSMO_DB_PRIMARY_KEY)
database = client.get_database_client(COSMO_DB_NAME)
container = database.get_container_client(COSMO_DB_CONVERSATIONS_CONTAINER_NAME)

def initializeContainer():
    client = CosmosClient(COSMO_DB_URI, credential=COSMO_DB_PRIMARY_KEY)
    database = client.get_database_client(COSMO_DB_NAME)
    container = database.get_container_client(COSMO_DB_CONVERSATIONS_CONTAINER_NAME)
    return container
    
##################
## User Management Functions
###############

def addUser(first_name, last_name, username, password, user_type="user"):
    # returns the userId if created successfully. 
    # Returns None if the username already exists
    # user_type = user || admin

    container = initializeContainer()
    query = """
        SELECT c.userId
        FROM c
        WHERE c.username=@username 
        """

    parameters = [
        {"name": "@username", "value": username}
    ]

    results = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    if results:
        #username already exists
        return None
    
    id = str(uuid.uuid4())

    #hashing the password
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    hashed_password = hashed_password.decode('utf-8')
    user = {
        "id": id,  # unique per user
        "userId": id,
        "firstName": first_name,
        "lastName": last_name,
        "documentType": "user",
        "user_type": user_type,
        "username": username,
        "password": hashed_password,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container.create_item(body=user)
    return id

def isAdmin(user_id):
    container = initializeContainer()
    try:
        user = container.read_item(item=user_id, partition_key=user_id)
        return user.get("documentType") == "user" and user.get("user_type") == "admin"
    except CosmosResourceNotFoundError:
        return False

def userIsValid(user_id):
    container = initializeContainer()
    try:
        item = container.read_item(item=user_id, partition_key=user_id)
        return item.get("documentType") == "user"
    except CosmosResourceNotFoundError:
        return False

def login(username, password):
    """
    Attempt to log in a user by username and password.
    Returns a dictionary with userId and user_type if found, otherwise None.
    """
    container = initializeContainer()

    query = """
        SELECT c.userId, c.user_type, c.password
        FROM c
        WHERE c.documentType="user" AND c.username=@username
        """

    parameters = [
        {"name": "@username", "value": username},
    ]

    results = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    #comparing the passwords
    if results and bcrypt.checkpw(password.encode('utf-8'), results[0]["password"].encode('utf-8')):
        # Return the first match (there should only be one)
        return {"userId": results[0]["userId"], "user_type": results[0]["user_type"]}

    return None

##################
## Chatbot Functions
################
    
def addMessage(user_id, session_id, role, content):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    message = {
        "id": str(uuid.uuid4()),  # unique per document
        "userId": user_id,        # partition key
        "sessionId": session_id,
        "documentType": "message",
        "role": role,             # "user" or "assistant"
        "content": content,
        "sentAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer()
    container.create_item(body=message)

def addSession(user_id, session_title):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    session_id = str(uuid.uuid4())
    session = {
        "id": session_id,  
        "userId": user_id,
        "documentType": "session",
        "sessionTitle": session_title,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer()
    container.create_item(body=session)
    return session_id

def getSessions(user_id):
    # returns a list of dictionaries [{"session_id": ..., "session_title": ...}]

    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    query = """
            SELECT c.sessionTitle, c.id 
            FROM c 
            WHERE c.documentType="session"
            ORDER BY c.createdAt DESC
        """
    
    container = initializeContainer()    
    sessions = list(container.query_items(
        query=query,
        partition_key=user_id  
    ))

    formatted_sessions = [
        {"session_id": s["id"], "session_title": s["sessionTitle"]}
        for s in sessions
    ]
    
    return formatted_sessions


def getMessages(user_id, session_id):
    #returns a list of tuples/messages (role, content) for a given session_id

    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    query = """
            SELECT c.role, c.content 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
            ORDER BY c.sentAt ASC
        """
        
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]
    
    container = initializeContainer()
    messages = list(container.query_items(
        query=query,
        parameters=parameters,
        partition_key=user_id  #since the partition key is userId, the query will only search within the user's documents
        ))
    return messages

def deleteSession(user_id, session_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    # Delete all messages associated with the session
    query_messages = """
            SELECT c.id 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
        """
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]

    container = initializeContainer()
    messages = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    
    for message in messages:
        container.delete_item(item=message['id'], partition_key=user_id)
    
    # Delete the session itself
    container.delete_item(item=session_id, partition_key=user_id)

def clearSession(user_id, session_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    # Delete all messages associated with the session
    query_messages = """
            SELECT c.id 
            FROM c 
            WHERE c.documentType="message" AND c.sessionId=@sessionId
        """
    parameters = [
        {"name": "@sessionId", "value": session_id}
    ]
    container = initializeContainer()
    messages = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    
    for message in messages:
        container.delete_item(item=message['id'], partition_key=user_id)



