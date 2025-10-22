"""
This script contains all functions related to user operatiosn on the database.
"""
from azure.cosmos import CosmosClient
from azure.cosmos.exceptions import CosmosResourceNotFoundError

import uuid
from datetime import datetime, timezone
import os
import bcrypt
from dotenv import load_dotenv

load_dotenv()

COSMO_DB_URI = os.getenv("COSMO_DB_URI")
COSMO_DB_PRIMARY_KEY = os.getenv("COSMO_DB_PRIMARY_KEY")
COSMO_DB_NAME = os.getenv("COSMO_DB_NAME")
COSMO_DB_CONVERSATIONS_CONTAINER_NAME = os.getenv("COSMO_DB_CONVERSATIONS_CONTAINER_NAME")
COSMO_DB_SUPPORT_CONTAINER_NAME = os.getenv("COSMO_DB_SUPPORT_CONTAINER_NAME")


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
## Add User
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
        "userType": user_type,
        "email": email,
        "password": hashed_password,
        "createdAt": datetime.now(timezone.utc).isoformat()
    }
    container.create_item(body=user)
    return id

##################
## Check if Admin
###############
def isAdmin(user_id):
    container = initializeContainer(0)
    try:
        user = container.read_item(item=user_id, partition_key=user_id)
        return user.get("documentType") == "user" and user.get("userType") == "admin"
    except CosmosResourceNotFoundError:
        return False

##################
## Check if user exists
###############
def userIsValid(user_id):
    container = initializeContainer(0)
    try:
        item = container.read_item(item=user_id, partition_key=user_id)
        return item.get("documentType") == "user"
    except CosmosResourceNotFoundError:
        return False    

##################
## Get User Information
###############
def getUserInfo(user_id):
    if not userIsValid(user_id):
        raise ValueError("This user does not exist")
    
    container = initializeContainer(0)
    user = container.read_item(item=user_id, partition_key=user_id)
    return user

##################
## Login
###############
def login(email, password):
    """
    Attempt to log in a user by email and password.
    Returns a dictionary with userId and userType if found, otherwise None.
    """
    container = initializeContainer(0)

    query = """
        SELECT c.userId, c.userType, c.password
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
        return {"userId": results[0]["userId"], "userType": results[0]["userType"]}

    return None
