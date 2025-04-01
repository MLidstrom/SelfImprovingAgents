import os
import sys

from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up the LLM
llm = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=OPENAI_API_KEY)

# Define a calculator tool
def calculator(query: str) -> str:
    """Evaluates math expressions like '2 + 2'."""
    try:
        return str(eval(query))
    except Exception as e:
        return f"Error: {str(e)}"

tools = [
    Tool(
        name="Calculator",
        func=calculator,
        description="Evaluates mathematical expressions (e.g., '2 + 2')."
    )
]

# A simple ReAct prompt that references optional tools

#servant_prompt_template = """
#You are a helpful assistant that can use the provided tools when necessary.
#Question: {input}
#Scratchpad: {agent_scratchpad}
#"""

servant_prompt_template = """
You are a helpful assistant that can use the provided tools to answer math questions.
You have one tool available:
- Calculator: Evaluates mathematical expressions (e.g., '2 + 2'). It expects a valid Python expression as input.

Your task is to answer the user's math question by using the Calculator tool.
To use the Calculator tool, you need to:
1. Extract the math expression from the user's question.
2. Convert the expression into a valid Python expression that the Calculator tool can evaluate.
3. Pass that expression to the Calculator tool.
4. Use the tool's output as the answer to the question.

For example, if the question is "What is 2 plus 2?", you should extract "2 plus 2", convert "plus" to "+", and pass "2 + 2" to the Calculator tool.
Remember to always use the Calculator tool for math questions to ensure accuracy.

Question: {input}
Assistant's Thoughts: {agent_scratchpad}
"""

# Create the servant agent
prompt = PromptTemplate(
    input_variables=["input", "agent_scratchpad"],
    template=servant_prompt_template
)
servant_agent = create_react_agent(llm, tools, prompt)
servant_executor = AgentExecutor(agent=servant_agent, tools=tools, verbose=True)

def run_servant(input_query: str) -> str:
    """Runs the servant agent on the given input and returns the final answer."""
    # Using .run(...) ensures we get a string as the final output
    return servant_executor.run(input_query)

if __name__ == "__main__":
    # Read any input passed in via sys.stdin
    input_query = sys.stdin.read().strip()
    
    # Fallback if nothing was provided:
    if not input_query:
        input_query = "What is 2 + 2?"
    
    result = run_servant(input_query)
    print(result)
