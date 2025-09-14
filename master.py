import os
import json
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
    4. If the output is spot-on, indicate that no changes are needed.
    5. Respond with a JSON object containing your reasoning and the new code (if any).

    The servant got this input: "{servant_input}"
    It gave this output: "{servant_output}"
    Its current code will follow separately.

    Respond with a JSON object in the following format:
    {{
        "reasoning": "Your reasoning here",
        "new_code": "```python\\n[New servant.py code here]\\n```"
    }}
    If no improvement is needed, `new_code` should be "No improvement needed".
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
    test_cases = [
        {"input": "What is 2 + 2?", "expected_output": "4"},
        {"input": "what is 10 divided by 2?", "expected_output": "5.0"},
        {"input": "what time is it?", "validation": "The current time is"},
        {"input": "where are we?", "validation": "Based on your IP, you appear to be in"},
        {"input": "what is my ip address?", "validation": "Your public IP address is:"}
    ]

    for i, test_case in enumerate(test_cases):
        print(f"--- Running Test Case #{i+1} ---")
        test_input = test_case["input"]
        print(f"Input: {test_input}")

        servant_output = run_servant(test_input)
        print(f"Servant Output: {servant_output}")

        # Validate output
        output_is_correct = False
        if "expected_output" in test_case:
            if servant_output == test_case["expected_output"]:
                output_is_correct = True
        elif "validation" in test_case:
            if test_case["validation"] in servant_output:
                output_is_correct = True

        if output_is_correct:
            print("Output is correct. No improvement needed.\n")
            continue

        print("Output is incorrect or needs improvement.")
        servant_code = read_servant_code()
        print("Running Master Agent...")
        master_response = run_master_agent(test_input, servant_output, servant_code)
        print(f"Master Response:\n{master_response}\n")

        try:
            # Extract the JSON part of the response
            json_match = re.search(r'\{.*\}', master_response, re.DOTALL)
            if not json_match:
                print("No JSON object found in the master response.")
                continue

            response_json = json.loads(json_match.group(0))
            reasoning = response_json.get("reasoning", "")
            new_code = response_json.get("new_code", "")

            print(f"Master Reasoning: {reasoning}")

            if new_code and new_code != "No improvement needed":
                # Attempt to extract only the Python code fenced by ```python ... ```
                code_pattern = r"```python\s*(.*?)\s*```"
                match = re.search(code_pattern, new_code, re.DOTALL)

                if match:
                    pure_python_code = match.group(1).strip()
                    print("Updating Servant Code...")
                    write_servant_code(pure_python_code)
                    print("Running Servant (Improved Run)...")
                    improved_output = run_servant(test_input)
                    print(f"Improved Servant Output: {improved_output}\n")
                else:
                    print("No valid Python code block found in the master response. No update performed.\n")
            else:
                print("No improvement needed per Master Agent.\n")
        except json.JSONDecodeError:
            print("Master agent response is not valid JSON.\n")
        except Exception as e:
            print(f"An error occurred: {e}\n")

if __name__ == "__main__":
    main()