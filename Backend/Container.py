from azure.storage.blob import BlobServiceClient, generate_blob_sas, BlobSasPermissions
from azure.core.credentials import AzureNamedKeyCredential

from datetime import datetime, timedelta
import os
####################
# This script contains functions for managing a storage account
#
####################3
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_API_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_API_KEY")

def deleteContainerDirectory(container_name, directory_name):

    #delete all media stored on the storage account (deleting the session directory in the container)
    account_name = AZURE_STORAGE_ACCOUNT_NAME
    storage_account_key = AZURE_STORAGE_ACCOUNT_API_KEY
    credential = AzureNamedKeyCredential(account_name, storage_account_key)

    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential
    )
    container_client = blob_service_client.get_container_client(container_name)

    blobs_to_delete = container_client.list_blobs(name_starts_with=f"{directory_name}/")
    for blob in blobs_to_delete:
        blob_client = container_client.get_blob_client(blob.name)
        blob_client.delete_blob()


def uploadBlob(container_name, blob_directory, blob_content, expiry_days=3650):
    """
    blob_directory includes blob name
    The function uploads a blob to a container and returns an SAS url
    """
    account_name = AZURE_STORAGE_ACCOUNT_NAME
    storage_account_key = AZURE_STORAGE_ACCOUNT_API_KEY
    credential = AzureNamedKeyCredential(account_name, storage_account_key)

    blob_service_client = BlobServiceClient(
        account_url=f"https://{account_name}.blob.core.windows.net",
        credential=credential
    )
    container_client = blob_service_client.get_container_client(container_name)
    blob_client = container_client.get_blob_client(blob_directory)
    blob_client.upload_blob(
        blob_content,
        overwrite=True,
        connection_timeout=30,
        read_timeout=120
    )

    sas_token = generate_blob_sas(
        account_name=AZURE_STORAGE_ACCOUNT_NAME,
        container_name=container_name,
        blob_name=blob_directory,
        account_key=AZURE_STORAGE_ACCOUNT_API_KEY,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(days=expiry_days)
    )

    sas_url = f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{container_name}/{blob_directory}?{sas_token}"
    return sas_url
