# azure-ai-chatbot
## Project Scope

The main goal of this project is to implement an AI chatbot, powered by Microsoft Azure resources. The chatbot has been instructed to act as a friendly salesperson for a vehicle dealership. It's meant to serve customers inquiring about vehicles provided by the dealership or requesting assistance with previously purchased vehicles. However, the implementation may receive different instructions depending on client requirements.

## Setup Instructions

### Prerequisites

Prerequisites to run the webapp locally:

<ul>
  <li>Node Js</li>
  <li>Python</li>
</ul>

### Installation Steps

1. **Clone the Repository**: Clone the project repository from GitHub to your local machine.
   
#### Running the Backend

All backend functionalities are hosted on an Azure Function App and are already functional; However, the Speech-To-Speech feature is hosted on a separate FastAPI server. To run this server locally, please follow these steps:

1. **Install Dependencies**: Navigate to the backend directory and install dependencies listed in <i>requirements_sts.txt</i>.

```
cd Backend
pip install -r requirements_sts.txt
```

2. **Set Environment Variables**: Create a .env file in the Backend directory and set the required environment variables as listed in <i>.env_template</i>.

3. **Run the FastAPI Server**: Start the FastAPI server to run the Speech-To-Speech feature locally.

```
uvicorn SpeechToSpeechServer:app --reload --host 0.0.0.0 --port 8000
```

#### Running the Frontend

To set up and run the web application locally, please follow these steps:


1. **Install Dependencies**: Navigate to ./Frontend/azure-chatbot and install the required frontend dependencies.

```
cd Frontend/azure-chatbot
npm install
```

2. **Start the Frontend Server**: Start the React development server to run the frontend locally.

```
npm run dev
```
