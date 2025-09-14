import sys
import json
import requests
from datetime import datetime
import socket
import re
from asteval import Interpreter
class ServantAgent:
    def __init__(self):
        self.capabilities = {
            "math": self.handle_math_query,
            "time": self.handle_time_query,
            "location": self.handle_location_query,
            "ip": self.handle_ip_query,
            "general": self.handle_general_query
        }

    def process_query(self, query):
        """Main method to process user queries"""
        query_type = self.classify_query(query)
        handler = self.capabilities.get(query_type, self.handle_general_query)
        return handler(query)

    def classify_query(self, query):
        """Determine the type of query"""
        query = query.lower()
        
        if any(term in query for term in ['+', '-', '*', '/', 'plus', 'minus', 'times', 'divided', 'calculate']):
            return "math"
        elif any(term in query for term in ['time', 'date', 'day', 'month', 'year']):
            return "time"
        elif any(term in query for term in ['location', 'where am i', 'country', 'city', 'where are we']):
            return "location"
        elif any(term in query for term in ['ip', 'ip address']):
            return "ip"
        else:
            return "general"

    def handle_math_query(self, query):
        """Handle mathematical expressions"""
        expression = self.extract_math_expression(query)
        return self.evaluate_expression(expression)

    def extract_math_expression(self, question):
        """Extracts and converts a mathematical expression from a question."""
        # Remove the question part and extract the math expression
        question = question.lower().replace('what is', '').strip('?').strip()
        # Replace common math words with symbols
        question = question.replace('plus', '+').replace('minus', '-')
        question = question.replace('times', '*').replace('divided by', '/')
        return question

    def evaluate_expression(self, expression):
        """Evaluates a mathematical expression safely."""
        try:
            # Evaluate the expression and return the result
            aeval = Interpreter()
            return str(aeval.eval(expression))
        except Exception as e:
            return f"Error: {str(e)}"

    def handle_time_query(self, query):
        """Handle time and date queries"""
        now = datetime.now()
        if 'time' in query.lower():
            return f"The current time is {now.strftime('%H:%M:%S')}"
        else:
            return f"Today's date is {now.strftime('%A, %B %d, %Y')}"

    def handle_location_query(self, query):
        """Attempt to determine the location based on IP"""
        try:
            response = requests.get('https://ipinfo.io/json', timeout=5)
            if response.status_code == 200:
                data = response.json()
                location_info = {
                    "city": data.get("city", "Unknown"),
                    "region": data.get("region", "Unknown"),
                    "country": data.get("country", "Unknown"),
                    "location": data.get("loc", "Unknown")
                }
                return f"Based on your IP, you appear to be in {location_info['city']}, {location_info['region']}, {location_info['country']}."
            else:
                return "Unable to determine location information. API request failed."
        except Exception as e:
            return f"Error getting location information: {str(e)}"

    def handle_ip_query(self, query):
        """Get the user's public IP address"""
        try:
            # Try to get public IP
            response = requests.get('https://api.ipify.org?format=json', timeout=5)
            if response.status_code == 200:
                public_ip = response.json()['ip']
                return f"Your public IP address is: {public_ip}"
            else:
                # Fallback to local IP if public IP cannot be determined
                hostname = socket.gethostname()
                local_ip = socket.gethostbyname(hostname)
                return f"Could not determine public IP. Your local IP address is: {local_ip}"
        except Exception as e:
            return f"Error retrieving IP information: {str(e)}"

    def handle_general_query(self, query):
        """Handle general or unclassified queries"""
        return f"I'm not sure how to answer the query: '{query}'. I can handle math calculations, provide time/date information, determine your approximate location, or give your IP address."

if __name__ == "__main__":
    # Create an instance of the ServantAgent
    agent = ServantAgent()
    
    # Read input from stdin
    input_query = sys.stdin.read().strip()
    
    # Fallback if nothing was provided
    if not input_query:
        input_query = "What is 2 + 2?"
    
    # Process the query and print the result
    result = agent.process_query(input_query)
    print(result)