# Agentic AI

**Agentic AI** is a multi-agent orchestration system built using **Google Gemini** as its core brain. Unlike traditional implementations that rely on frameworks like LangChain, this system directly uses Gemini to control and coordinate AI agents, assigning tasks and arguments dynamically.  

## Key Features

- **Central Orchestrator**: Gemini acts as the brain, determining which AI agent handles a specific task or argument.  
- **No LangChain Required**: Fully functional without external orchestration frameworks.  
- **Dynamic Task Assignment**: Agents are assigned tasks based on context and requirements in real-time.  
- **Scalable Architecture**: Easily extendable with new AI agents as needed.  

## How It Works

1. **Input Processing**: The system receives a user query or task.  
2. **Agent Selection**: Gemini evaluates the input and decides which AI agent is best suited to handle it.  
3. **Task Execution**: The selected agent performs its function.  
4. **Response Aggregation**: Results from all relevant agents are collected and returned to the user.  
