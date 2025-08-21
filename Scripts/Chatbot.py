from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage, AssistantMessage
from azure.core.credentials import AzureKeyCredential

import os
from dotenv import load_dotenv
load_dotenv()

# Retrieve environment variables
# global AZURE_FOUNDRY_ENDPOINT, AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY, AZURE_OPENAI_MODEL_NAME, AZURE_OPENAI_CHAT_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_MODEL_NAME = os.getenv("AZURE_OPENAI_MODEL_NAME")
AZURE_OPENAI_CHAT_DEPLOYMENT_NAME = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

AZURE_MODEL_ENDPOINT = os.getenv("AZURE_MODEL_ENDPOINT")


def sendMessage(client, messages):
    #This function sends the api request to the model
    # and prints the response as it's being generated

    full_reply = ""
    response = client.complete(
        stream=True,
        messages=messages,
        max_tokens=4096,
        temperature=1.0,
        top_p=1.0,
        model=AZURE_OPENAI_CHAT_DEPLOYMENT_NAME
    )

    for update in response:
        if update.choices:
            chunk = update.choices[0].delta.content or ""
            print(chunk, end="", flush=True)  # live printing
            full_reply += chunk #since the response is being streamed, we only get access to chunks at a time
    print()

    messages.append(AssistantMessage(content=full_reply))
    return messages


def main():
    client = ChatCompletionsClient(
        endpoint=AZURE_MODEL_ENDPOINT,
        credential=AzureKeyCredential(AZURE_OPENAI_API_KEY),
    )

    try:

        #Model Outputs a welcome message
        messages = [
            SystemMessage(content="You are a helpful assistant. "
                                  "Start the conversation by greeting the user warmly and asking how you can help.")
        ]
        #in a more specific use-case (eg: customer service chatbot) we would include more thorough constraints on the model
        messages = sendMessage(client, messages)

        #Handeling the conversation
        while True:
            user_input = input("You: ")
            if user_input.lower() == "exit":
                break

            messages.append(UserMessage(content=user_input))
            messages = sendMessage(client, messages)

    except Exception as e:
        print("Something went wrong.")
        print(f"Exception details: {e}")

    finally:
        client.close()


if __name__ == '__main__':
    main()