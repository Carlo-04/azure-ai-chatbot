# GPT-4o Chatbot

## Lab II
### Azure Resources
This exercise utilized the following azure resources:

<ul>
    <li><b>Resource Group:</b> Used to store the resources to be used.</li>
    <li><b>Azure AI Foundry:</b> Used to manage and group Azure AI projects. 
        Future AI projects will be children of this foundry. 
        Additionally, when more Azure AI resources are later added, costs will be 
        centralized in this foundry to better track the added costs of 
        all AI features.</li>
    <li><b>Azure AI Foundry Project:</b> Used to deploy openAI models.
        It is where the API key and endpoints are configured.</li>
    <li><b>Azure Cosmo DB:</b> Used to store chat and user history to be accessed by the code.</li>
    <li><b>Azure AI Search:</b> Used to apply RAG to the chatbot.</li>
</ul>

### OpenAI Model
Within the AI Foundry project, a GPT-4o model was deployed using a global deployment. The model is to be used as a personal assistant that helps you choose a hotel to book. For this model, the default content filters were kept.

When a user submits a prompt, the following steps are taken:
<ol>
  <li>The user query is sent to the Azure AI Search resource, which queries the <i>hotels-sample</i> index. This index contains structured hotel information such as descriptions, tags, and metadata.</li>
  <li>The retrieved documents (top-k results) are formatted into a structured context which includes the hotels' names, descriptions, categories, and tags.</li>
  <li>GPT-4o processes the grounded input and generates a response. If no relevant results are retrieved from the index, the model is instructed to inform the user that it is unable to provide an answer.</li>
  <li>The current messages list's token count is estimated and compared to the set token limit. In case the limit is nearly reached, the conversation is summarized and the messages list is shortened to remain within the context window.</li>
</ol>

### Azure Cosmo DB
A simple NoSQL database was setup and linked to the chatbot. The database contains 3 types of documents: user profile, session, and message (of any role). Each user can have multiple sessions and every session contains a list of messages.

A user profile document contains the following attributes:
<ul>
  <li>id</li>
  <li>firstName</li>
  <li>lastName</li>
  <li>documentType: "user"</li>
  <li>createdAt</li>
</ul>

A session document contains the following attributes:
<ul>
  <li>id</li>
  <li>userId</li>
  <li>sessionTitle</li>
  <li>documentType: "session"</li>
  <li>createdAt</li>
</ul>

A message document contains the following attributes:
<ul>
  <li>id</li>
  <li>userId</li>
  <li>sessionId</li>
  <li>documentType: "message"</li>
  <li>role</li>
  <li>content</li>
  <li>sentAt</li>
</ul>

The userId was selected as the partition key.


### Basic Chatbot Architecture
<p align="center">
  <img src="Chatbot Architecture v1.2.png" alt="Description" width="500"/>
</p>

### Function App Chatbot Architecture
<p align="center">
  <img src="Function App Chatbot Architecture v1.2.png" alt="Description" width="500"/>
</p>