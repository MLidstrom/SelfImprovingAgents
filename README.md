# Self-Improving Agent System

This project implements a self-improving AI system consisting of a master agent that evaluates and improves a servant agent's code.

## Overview

The system has two main components:

1. **Master Agent**: Uses GPT-4o to analyze the servant's code and output, then generates improvements.
2. **Servant Agent**: A Python script that performs tasks based on standard input.

The master agent can evaluate the servant's performance against expected outputs and rewrite its code to improve functionality.

## How It Works

1. The servant agent receives an input query via standard input
2. The master agent evaluates the servant's output and code
3. If necessary, the master agent rewrites the servant's code to improve it
4. The system tests the improved servant with the same input

## Requirements

- Python 3.x
- OpenAI API key (set in .env file)
- Required packages:
  - dotenv
  - langchain
  - langchain_openai

## Setup

1. Clone this repository
2. Create a `.env` file with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. Install required packages:
   ```
   pip install python-dotenv langchain langchain-openai
   ```
4. Create a simple `servant.py` file if not already present

## Usage

Run the system with:

```
python master.py
```

The process will:
1. Run the servant with a test input
2. Analyze the servant's performance
3. Update the servant's code if improvements are identified
4. Test the improved servant

## Files

- `master.py`: Contains the master agent logic
- `servant.py`: The servant agent that gets improved
- `.env`: Environment variables including API key 