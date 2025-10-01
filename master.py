import os
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


class MissingAPIKeyError(RuntimeError):
    """Raised when the OpenAI API key is not available."""


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """Return a cached ChatOpenAI client.

    The original implementation eagerly instantiated the client at import time
    which made the module fail fast even when the master agent was not used.
    By lazily constructing the client we provide clearer error messaging and
    avoid unnecessary API calls during unit tests.
    """

    if not OPENAI_API_KEY:
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is not set. Please create a .env file with the key "
            "or export it before running the master agent."
        )

    return ChatOpenAI(model="gpt-4o", temperature=0.5, api_key=OPENAI_API_KEY)

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
def run_servant(input_query: str) -> str:
    """Execute the servant script and capture its output.

    A non-zero exit code previously went unnoticed. Capturing stderr and
    surfacing it makes debugging easier when the servant crashes.
    """

    result = subprocess.run(
        ["python", "servant.py"],
        input=input_query,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(
            "Servant execution failed with exit code "
            f"{result.returncode}: {stderr or 'No error output captured.'}"
        )

    return result.stdout.strip()

# Run the master agent
def run_master_agent(servant_input: str, servant_output: str, servant_code: str) -> str:
    master_input = {
        "servant_input": servant_input,
        "servant_output": servant_output,
        "servant_code": servant_code
    }
    master_response = get_llm().invoke(
        master_prompt.format(**master_input)
        + f"\nServant Source Code:\n```\n{servant_code}\n```"
    )
    return master_response.content


def extract_json_block(response: str) -> Optional[Dict[str, Any]]:
    """Extract the first valid JSON object from an LLM response."""

    decoder = json.JSONDecoder()
    stripped_response = response.strip()

    for index, char in enumerate(stripped_response):
        if char != "{":
            continue

        try:
            obj, _ = decoder.raw_decode(stripped_response[index:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue

    return None


@dataclass
class TestCase:
    input: str
    expected_output: Optional[str] = None
    validation: Optional[str] = None

    def validate(self, servant_output: str) -> bool:
        if self.expected_output is not None:
            return servant_output == self.expected_output

        if self.validation is not None:
            return self.validation in servant_output

        raise ValueError("Test case must define either expected_output or validation.")

def main() -> None:
    test_cases: List[TestCase] = [
        TestCase(input="What is 2 + 2?", expected_output="4"),
        TestCase(input="what is 10 divided by 2?", expected_output="5.0"),
        TestCase(input="what time is it?", validation="The current time is"),
        TestCase(input="where are we?", validation="Based on your IP, you appear to be in"),
        TestCase(input="what is my ip address?", validation="Your public IP address is:"),
    ]

    for index, test_case in enumerate(test_cases, start=1):
        print(f"--- Running Test Case #{index} ---")
        print(f"Input: {test_case.input}")

        try:
            servant_output = run_servant(test_case.input)
        except RuntimeError as exc:
            print(f"Servant failed to run: {exc}\n")
            continue

        print(f"Servant Output: {servant_output}")

        try:
            if test_case.validate(servant_output):
                print("Output is correct. No improvement needed.\n")
                continue
        except ValueError as exc:
            print(f"Invalid test case configuration: {exc}\n")
            continue

        print("Output is incorrect or needs improvement.")
        servant_code = read_servant_code()
        print("Running Master Agent...")

        try:
            master_response = run_master_agent(test_case.input, servant_output, servant_code)
        except MissingAPIKeyError as exc:
            print(f"Cannot contact master agent: {exc}\n")
            break

        print(f"Master Response:\n{master_response}\n")

        response_json = extract_json_block(master_response)
        if not response_json:
            print("No JSON object found in the master response.\n")
            continue

        reasoning = response_json.get("reasoning", "")
        new_code = response_json.get("new_code", "")
        print(f"Master Reasoning: {reasoning}")

        if not new_code or new_code == "No improvement needed":
            print("No improvement needed per Master Agent.\n")
            continue

        code_pattern = r"```python\s*(.*?)\s*```"
        match = re.search(code_pattern, new_code, re.DOTALL)
        if not match:
            print("No valid Python code block found in the master response. No update performed.\n")
            continue

        pure_python_code = match.group(1).strip()
        print("Updating Servant Code...")
        write_servant_code(pure_python_code)
        print("Running Servant (Improved Run)...")

        try:
            improved_output = run_servant(test_case.input)
        except RuntimeError as exc:
            print(f"Improved servant failed to run: {exc}\n")
            continue

        print(f"Improved Servant Output: {improved_output}\n")

if __name__ == "__main__":
    main()
