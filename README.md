# azure-ai-chatbot

## Setup Instructions

To run the script you must install the following python packages (Python >= 3.8 required):
<ul>
    <li>dotenv</li>
    <li>tiktoken</li>
    <li>azure-core</li>
    <li>azure-cosmos</li>
    <li>azure-search-documents</li>
    <li>openai</li>
</ul>

Once the dependencies are installed, you may run the script to initialize a session 
with the chatbot and converse with it.

You may use the following command to install all the dependencies:
```
pip install -r requirements.txt
```

## Chatbot  Information
This chatbot acts as a hotel assistant which recommends hotels based on certain activities and amenities. The model relies on information from the hotel-sample database provided by Azure.
