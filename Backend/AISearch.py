#################
# This module is a serires of helper functions for search index management
#   
################
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential, AzureNamedKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.ai.formrecognizer import DocumentAnalysisClient, DocumentField
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    ComplexField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswParameters,
    VectorSearchAlgorithmConfiguration,
    VectorSearchAlgorithmKind,
    VectorSearchProfile
)
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
import json
import os
import uuid

AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_AI_FOUNDRY_ENDPOINT = os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME")

AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_API_KEY = os.getenv("AZURE_SEARCH_API_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME")

AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_API_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_API_KEY")
AZURE_STORAGE_ACCOUNT_CONTAINER_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_CONTAINER_NAME")

##############
# Getting the embedding dimension of a model
#############
def getEmbeddingDimension():
    openai_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )

    response = openai_client.embeddings.create(
        model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME,
        input="test"
    )
    
    embedding_vector = response.data[0].embedding
    openai_client.close()
    return len(embedding_vector)


################
# Listing Search Indexes 
############
def listIndexes():

    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    # List all indexes
    indexes = index_client.list_indexes()
    index_list = []
    for idx in indexes:
        index_list.append(idx.name)
    return index_list

###################
# List the Documents in an Index
#################
def listDocuments(index_name):
    #lists all the documents in an index, given the index name
    #chunked documents will be returned as is (as separate docs)

    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=index_name, credential=credential)

    results = []
    pages = search_client.search(
        search_text="*",
        include_total_count=True
    )

    for result in pages:
        # result is a dict-like object
        clean_doc = {k: v for k, v in result.items() if not k.startswith("@")}
        results.append(clean_doc)

    return results

###############
#  Creating an Index  
###############
def createIndex(index_name, index_fields):
    # index_fields = [
    #     {"field_name": <name>, "field_type": <type>, "data_type": <data_type>,
    #        "key": True/False, "filterable": True/False, "sortable": True/False, "vectorized": True/False}
    #     ...
    #     {"field_name": <name>, "field_type": "ComplexField", "sub_fields": [{...}, {...}, ...]}
    # ]
    #
    #This function is used to create the search index and define its fields

    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    vector_profile_name = "vector-search-01"
    vector_config_name = "vector-search-config"
    vector_algo_config = VectorSearchAlgorithmConfiguration(name=vector_config_name)
    vector_algo_config.kind = VectorSearchAlgorithmKind.HNSW
    vector_search = VectorSearch(
        profiles= [VectorSearchProfile(name=vector_profile_name, algorithm_configuration_name=vector_config_name)],
        algorithms=[vector_algo_config]
    )

    fields = []
    for field in index_fields:

        if field["field_type"] == "SimpleField":
            fields.append(SimpleField(
                name=field["field_name"],
                type=field["data_type"],
                key=field.get("key", False),
                filterable=field.get("filterable", False),
                sortable=field.get("sortable", False),
            ))
        elif field["field_type"] == "SearchableField":
            fields.append(SearchableField(
                name=field["field_name"],
                type=field["data_type"],
                key=field.get("key", False),
                filterable=field.get("filterable", False),
                sortable=field.get("sortable", False)
            ))


        elif field["field_type"] == "SearchField": #Vectorized field
            fields.append(SearchField(
                name = field["field_name"],
                type = SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions = getEmbeddingDimension(),        
                vector_search_profile_name = vector_profile_name
            ))
            
        elif field["field_type"] == "ComplexField":
            sub_fields = []
            for row in field["sub_fields"]:
                if row["field_type"] == "SimpleField":
                    sub_fields.append(SimpleField(
                        name=row["field_name"], 
                        type=row["data_type"], 
                        key=row.get("key", False), 
                        filterable=row.get("filterable", False)))

                elif row["field_type"] == "SearchableField":
                    sub_fields.append(SearchableField(
                        name=row["field_name"], 
                        type=row["data_type"], 
                        key=row.get("key", False), 
                        filterable=row.get("filterable", False)))

            fields.append(ComplexField(name=field["field_name"], fields=sub_fields, collection=True))

    index = SearchIndex(name=index_name, fields=fields, vector_search=vector_search)
    result = index_client.create_index(index)

###############
# Divide Text into Chunk
###############
def chunkText(text, chunk_size = 400):
    #str, int -> list[str]

    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

################
# Vectorize String 
#############
def vectorizeString(text):
    openai_client = AzureOpenAI(
        api_version=AZURE_OPENAI_API_VERSION,
        azure_endpoint=AZURE_AI_FOUNDRY_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )

    embed_text = openai_client.embeddings.create(
            input=text,
            model=AZURE_OPENAI_EMBEDDING_DEPLOYMENT_NAME
        ).data[0].embedding
    
    openai_client.close()
    return embed_text

################
# Add Document to an Index 
###############
def addDocuments(index_name, documents, vector_fields=[], chunk_size=400):

    # Uploads documents to a vector search index with vectorization and chunking.
    # The function only expects an id field to be present in the search index
    # It also assumes that for every vectorized field there is a non-vectorized field for it. eg: content_vector and content.
    # Parameters:
    # - documents: list of dicts with raw document fields
    # - vector_fields: list of fields to vectorize (e.g., ["content", "summary"])
    # - chunk_size: number of words per chunk


    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=index_name, credential=credential)

    if(len(vector_fields)==0):
        result = search_client.upload_documents(documents)
        return

    docs_to_upload = []
    for doc in documents:
        doc_id = doc.get("id")

        for field in vector_fields:
            if field not in doc:
                continue
            text = doc[field]
            chunks = chunkText(text, chunk_size)

            for i, chunk in enumerate(chunks):
                doc_chunk = {
                    "chunk_id": f"{doc_id}_{field}_{i}",   
                    "parent_id": doc_id,            
                    "chunk_index": str(i), 
                    "chunk": chunk,
                    f"{field}_vector": vectorizeString(chunk)
                }
                doc_chunk["id"] = f"{doc_id}-{i}"
                for k, v in doc.items():
                    if k not in vector_fields and k != "id":
                        doc_chunk[k] = v
                docs_to_upload.append(doc_chunk)
    
    result = search_client.upload_documents(docs_to_upload)

#############
# Process Document with Doc Intelligence
############
def scanDocuments(files):
    """
    Receives a list of dicts containing 'url' and 'file_name',
    runs Azure Document Intelligence 'prebuilt-read' model on each URL,
    and returns a list of parsed JSON objects for vector DB ingestion. each page is a separate object.
    
    files example:
    [
        {"url": "https://<storage-account>.blob.core.windows.net/container/file1.pdf?SAS_TOKEN", "file_name": "file1.pdf"},
        {"url": "https://<storage-account>.blob.core.windows.net/container/file2.pdf?SAS_TOKEN", "file_name": "file2.pdf"}
    ]
    """

    endpoint = AZURE_AI_FOUNDRY_ENDPOINT
    key = AZURE_OPENAI_API_KEY

    client = DocumentAnalysisClient(endpoint=endpoint, 
                                    credential=AzureKeyCredential(key))
    results = []
    for file_info in files:
        file_url = file_info["url"]
        file_name = file_info.get("file_name", file_url.split("/")[-1])

        poller = client.begin_analyze_document_from_url(
            model_id="prebuilt-read",
            document_url=file_url
        )
        result = poller.result()
        document_id = str(uuid.uuid4())  

        for page_num, page in enumerate(result.pages, start=1):
            page_text = " ".join([line.content for line in page.lines])

            parsed_result = {
                "id": f"{document_id}-page{page_num}",  
                "file_name": file_name,
                "page_number": page_num,
                "content": page_text, 
            }

            results.append(parsed_result)

    return results


####################
# Handles the process of uploading a file to blob storage, processing it with doc intell, adding to index and deleting the blob
##################
def addDocumentHelper(index_name, files):
    """
    Receives a dict of uploaded files (werkzeug.datastructures.FileStorage),
    Returns a list of successfully added file names.
    """
    # Connecting to blob storage
    account_name = AZURE_STORAGE_ACCOUNT_NAME
    storage_account_key = AZURE_STORAGE_ACCOUNT_API_KEY
    credential = AzureNamedKeyCredential(account_name, storage_account_key)

    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential
    )

    container_name = AZURE_STORAGE_ACCOUNT_CONTAINER_NAME
    container_client = blob_service_client.get_container_client(container_name)

    uploaded_files = []
    added_files = [] #files successfully added to the index
    for file_key in files:
        file = files[file_key]

        # Generate unique file name by appending UUID
        unique_id = uuid.uuid4().hex
        name, ext = os.path.splitext(file.filename)
        unique_filename = f"{name}_{unique_id}{ext}"
        
        # Uploading file to blob storage
        blob_client = container_client.get_blob_client(unique_filename)
        blob_client.upload_blob(file.stream, overwrite=True)

        current_file = {
            "file_name": file.filename,
            "url": blob_client.url
        }
        uploaded_files.append(current_file)

        #processing uploaded file with document intelligence
        processed_file = scanDocuments([current_file])
        addDocuments(index_name, processed_file, ["content"])
        blob_client.delete_blob(delete_snapshots="include") #deleting the file after processing
        added_files.append(file.filename)

    return added_files


####################
# Find which field is the key field
##################
def getKeyField(index_name):
    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    index = index_client.get_index(index_name)
    for field in index.fields:
        if getattr(field, "key", False):  
            return field.name

    raise ValueError(f"No key field found for index {index_name}")

#################
# Get fields info
###############
def getFields(index_name):
    #Returns a list of dics containing info about each field
    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)
    index = index_client.get_index(index_name)
    fields = []

    for field in index.fields:
        fields.append({"name": field.name, "type": field.type})

###################
# Delete a Document in an Index
#################
def deleteDocument(index_name, file_name):
    """
    deletes all the documents in the index with the same fileName field
    """
    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    search_client = SearchClient(endpoint=AZURE_SEARCH_ENDPOINT, index_name=index_name, credential=credential)

    # Search for documents with the given filename
    results = search_client.search(search_text="", filter=f"file_name eq '{file_name}'")

    # Collect document keys
    keys_to_delete = []
    id_field = getKeyField(index_name)
    for doc in results:
        keys_to_delete.append({"@search.action": "delete", id_field: doc[id_field]})

    if not keys_to_delete:
        print(f"No documents found with file_name = {file_name}")
        return

    #deleting keys
    search_client.upload_documents(documents=keys_to_delete)
    print(f"Deleted {len(keys_to_delete)} documents with fileName = {file_name}")

###############
# Delete Index
##############
def deleteIndex(index_name):
    credential = AzureKeyCredential(AZURE_SEARCH_API_KEY)
    index_client = SearchIndexClient(endpoint=AZURE_SEARCH_ENDPOINT, credential=credential)

    index_client.delete_index(index_name)     

