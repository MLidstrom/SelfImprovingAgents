import os
import re
import shutil
import subprocess

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Set up the LLM for the master
llm = ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=OPENAI_API_KEY)

# Master agent prompt
master_prompt = PromptTemplate(
    input_variables=["servant_input", "servant_output", "servant_code"],
    template="""
    You are a master agent tasked with improving a servant agent's performance.
    The servant reads input from standard input, not command-line arguments.
    Here's what to do:
    1. Read the servant's current source code provided below.
    2. Check the servant's output against its input.
    3. If the output is wrong or could be better, rewrite the servant's entire code to improve it, keeping input from standard input.
    4. If the output is spot-on, say no changes are needed.
    5. Save your new code or decision for the next step.

    The servant got this input: "{servant_input}"
    It gave this output: "{servant_output}"
    Its current code will follow separately.

    Give your reasoning and, if needed, new code. Use this format:
    Reasoning: [Your reasoning here]
    New Code:
    ```python
    [New servant.py code here]
    ```
    or "No improvement needed".
    """
)

# Read servant code
def read_servant_code(file_path="servant.py"):
    with open(file_path, "r") as f:
        return f.read()

# Write new servant code
def write_servant_code(new_code, file_path="servant.py"):
    # Make a backup of the existing file before overwriting
    if os.path.exists(file_path):
        backup_path = f"{file_path}.bak"
        shutil.copyfile(file_path, backup_path)

    with open(file_path, "w") as f:
        f.write(new_code)

# Run the servant with input via standard input
def run_servant(input_query):
    result = subprocess.run(
        ["python", "servant.py"],
        input=input_query,
        capture_output=True,
        text=True
    )
    return result.stdout.strip()

# Run the master agent
def run_master_agent(servant_input, servant_output, servant_code):
    master_input = {
        "servant_input": servant_input,
        "servant_output": servant_output,
        "servant_code": servant_code
    }
    master_response = llm.invoke(
        master_prompt.format(**master_input)
        + f"\nServant Source Code:\n```\n{servant_code}\n```"
    )
    return master_response.content

def main():
    # Use a location-related query instead of a math problem
    test_input = "Where are we in the world?"
    print("Running Servant (Initial Run)...")
    initial_output = run_servant(test_input)
    print(f"Servant Output: {initial_output}\n")

    servant_code = read_servant_code()
    print("Running Master Agent...")
    master_response = run_master_agent(test_input, initial_output, servant_code)
    print(f"Master Response:\n{master_response}\n")

    if "New Code:" in master_response:
        reasoning, new_code_section = master_response.split("New Code:", 1)
        new_code = new_code_section.strip()

        if new_code != "No improvement needed":
            # Attempt to extract only the Python code fenced by ```python ... ```
            code_pattern = r"```python\s*(.*?)\s*```"
            match = re.search(code_pattern, new_code, re.DOTALL)

            if match:
                pure_python_code = match.group(1).strip()
                print("Updating Servant Code with code between ```python and ```...")
                write_servant_code(pure_python_code)
                print("Running Servant (Improved Run)...")
                improved_output = run_servant(test_input)
                print(f"Improved Servant Output: {improved_output}")
            else:
                print("No valid Python code block found in the master response. No update performed.")
        else:
            print("No improvement needed per Master Agent.")
    else:
        print("Master agent response format invalid.")

if __name__ == "__main__":
    main()