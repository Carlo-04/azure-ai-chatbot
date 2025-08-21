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
</ul>

### OpenAI Model
Within the AI Foundry project, a GPT-4o model was deployed using a global deployment. 

The model is to be used as a personal assistant. Considering the broad scope of 
this assignment, the default content filters were kept. Later on if a more 
specific use case is considered (eg: customer support for a car dealership), 
extra content filtering settings may be set in the AI Foundry Portal or through
System Messages from the script.

### Code Details
A simple text-based chatbot was implemented using the Azure AI Inference SDK. 

Once the script is run, a chat completion client is initiated and its
behaviour is defined through an initial system message. Since the chatbot 
is constrained to text dialogue, a chat completion client was chosen without an agent.
If more features and tools are needed later, we may utilize an agent.

A simple conversation loop was implemented in which the user may send input and receive replies
from the model though the terminal. Prompts were sent using API calls to the OpenAI model in the 
AI Foundry project.

Furthermore, since chat completion clients are essentially stateless, the code also manually
the messaging history and passes it within each request to the model.

### Architecture Summary
<p align="center">
  <img src="Chatbot Architecture.png" alt="Description" width="500"/>
</p>
