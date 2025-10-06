from azure.cosmos import CosmosClient, PartitionKey
from azure.identity import DefaultAzureCredential
from azure.cosmos.exceptions import CosmosResourceNotFoundError
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential

import uuid
from datetime import datetime, timezone
import os
import bcrypt



COSMO_DB_URI = os.getenv("COSMO_DB_URI")
COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")
COSMO_DB_SUPPORT_CONTAINER_NAME = os.getenv("COSMO_DB_SUPPORT_CONTAINER_NAME")

AZURE_COMMUNICATION_ENDPOINT = os.getenv("AZURE_COMMUNICATION_ENDPOINT")
AZURE_COMMUNICATION_API_KEY = os.getenv("AZURE_COMMUNICATION_API_KEY")


def initializeContainer(container_num):
    # container numbers: Conversations: 0, Support: 1

    client = CosmosClient(COSMO_DB_URI, credential=COSMO_DB_PRIMARY_KEY)
    database = client.get_database_client(COSMO_DB_NAME)
    match container_num:
        case 0:
            container = database.get_container_client(COSMO_DB_CONVERSATIONS_CONTAINER_NAME) #partition key is userId
        case 1:
            container = database.get_container_client(COSMO_DB_SUPPORT_CONTAINER_NAME) #partition key is supportAgentId
    return container
    
##################
## User Management Functions
###############

def addUser(first_name, last_name, email, password, user_type="user"):
    # returns the userId if created successfully. 
    # Returns None if the email already exists
    # user_type = user || admin

    container = initializeContainer(0)
    query = """
        SELECT c.userId
        FROM c
        WHERE c.email=@email 
        """

    parameters = [
        {"name": "@email", "value": email}
    ]

    results = list(container.query_items(
        query=query,
        parameters=parameters,
        enable_cross_partition_query=True
    ))

    if results:
        #email already in use
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
        "email": email,
        "password": hashed_password,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container.create_item(body=user)
    return id

def isAdmin(user_id):
    container = initializeContainer(0)
    try:
        user = container.read_item(item=user_id, partition_key=user_id)
        return user.get("documentType") == "user" and user.get("user_type") == "admin"
    except CosmosResourceNotFoundError:
        return False

def userIsValid(user_id):
    container = initializeContainer(0)
    try:
        item = container.read_item(item=user_id, partition_key=user_id)
        return item.get("documentType") == "user"
    except CosmosResourceNotFoundError:
        return False
    
def getUserInfo(user_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(0)
    user = container.read_item(item=user_id, partition_key=user_id)
    return user

def login(email, password):
    """
    Attempt to log in a user by email and password.
    Returns a dictionary with userId and user_type if found, otherwise None.
    """
    container = initializeContainer(0)

    query = """
        SELECT c.userId, c.user_type, c.password
        FROM c
        WHERE c.documentType="user" AND c.email=@email
        """

    parameters = [
        {"name": "@email", "value": email},
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
    container = initializeContainer(0)
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
    container = initializeContainer(0)
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
    
    container = initializeContainer(0)    
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
    
    container = initializeContainer(0)
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

    container = initializeContainer(0)
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
    container = initializeContainer(0)
    messages = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    
    for message in messages:
        container.delete_item(item=message['id'], partition_key=user_id)


#############
## Customer Support Functions
#############
def getOpenSupportRequests():
    query = """
            SELECT c.id, c.userId, c.subject, c.description, c.createdAt
            FROM c 
            WHERE c.documentType="support_request" AND c.status="open"
            ORDER BY c.createdAt ASC
        """
    
    container = initializeContainer(1)    
    requests = list(container.query_items(
        query=query,
        partition_key="none"
    ))

    formatted_requests = [
        {
            "request_id": r["id"], 
            "user_id": r["userId"], 
            "subject": r["subject"], 
            "description": r["description"], 
            "createdAt": r["createdAt"]
        }
        for r in requests
    ]
    
    return formatted_requests

def getSupportInProgressRequestsByAgent(user_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)    
    query = """
            SELECT c.id, c.userId, c.subject, c.description, c.status, c.createdAt
            FROM c 
            WHERE c.documentType="support_request" AND c.supportAgentId=@userId AND c.status = "in_progress"
            ORDER BY c.createdAt ASC
        """
    parameters = [
        {"name": "@userId", "value": user_id}
    ]
    
    requests = list(container.query_items(
        query=query,
        parameters=parameters,
        partition_key=user_id
    ))

    formatted_requests = [
        {
            "request_id": r["id"], 
            "user_id": r["userId"], 
            "subject": r["subject"], 
            "description": r["description"], 
            "status": r["status"],
            "createdAt": r["createdAt"]
        }
        for r in requests
    ]
    
    return formatted_requests


def addSupportRequest(user_id, subject, description):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    request_id = str(uuid.uuid4())
    support_request = {
        "id": request_id,  
        "userId": user_id,
        "documentType": "support_request",
        "subject": subject,
        "description": description,
        "status": "open",  # open, in_progress, resolved
        "supportAgentId": "none",  # to be assigned later
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container = initializeContainer(1)
    container.create_item(body=support_request)
    return request_id

def handleSupportRequest(user_id, customer_id, request_id):
    # This function assigns a support request to an agent (user_id) once the agent selects it
    if not userIsValid(user_id) or not userIsValid(customer_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)

    query_messages = """
            SELECT *
            FROM c 
            WHERE c.documentType="support_request" AND c.id=@id
        """
    parameters = [
        {"name": "@id", "value": request_id}
    ]
    requests = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key="none"
        ))
    if requests:
        request = requests[0]
        if request["supportAgentId"] != "none":
            return -1  # already assigned to another agent
        
        container.delete_item(
            item=request["id"],
            partition_key="none"
        )
        
        request["status"] = 'in_progress'
        request["supportAgentId"] = user_id
        container.create_item(body=request)
    else:
        raise ValueError("This request does not exist anymore.")



def closeSupportRequest(user_id, customer_id, request_id):
    # This function closes a support request and markes it as resolved
    if not userIsValid(user_id) or not userIsValid(customer_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(1)

    query_messages = """
            SELECT *
            FROM c 
            WHERE c.documentType="support_request" AND c.id=@id
        """
    parameters = [
        {"name": "@id", "value": request_id}
    ]
    requests = list(container.query_items(
        query=query_messages,
        parameters=parameters,
        partition_key=user_id
        ))
    if requests:
        request = requests[0]
        if request["supportAgentId"] != user_id:
            raise ValueError("This request is assigned to another agent.")
        
        request["status"] = 'resolved'
        container.replace_item(item=request["id"], body=request)
    else:
        raise ValueError("This request does not exist anymore.")
    
def sendEmail(user_id, recipient_id, subject, body_text, body_html):
    if not userIsValid(user_id) or not userIsValid(recipient_id):
        raise ValueError("This user does not exist")
    
    sender_email = "DoNotReply@a4a02730-2bef-46ed-beaa-64e5c3ed0fc9.azurecomm.net"
    recipient_info = getUserInfo(recipient_id)
    rec_email = recipient_info.get("email")
    rec_fname = recipient_info.get("firstName")
    rec_lname = recipient_info.get("lastName")
    email_client = EmailClient(endpoint=AZURE_COMMUNICATION_ENDPOINT, credential=AzureKeyCredential(AZURE_COMMUNICATION_API_KEY))

    message = {
        "content": {
            "subject": subject,
            "plainText": body_text,
            "html": body_html
        },
        "recipients": {
            "to": [
                {
                    "address": rec_email,
                    "displayName": f"{rec_fname} {rec_lname}"
                }
            ]
        },
        "senderAddress": sender_email
    }   
    poller = email_client.begin_send(message)
    return poller.result()