# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# mypy: disable-error-code="union-attr"
import subprocess
import re
import os
from typing import List, Optional, Dict, Any, Union
import json

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

LOCATION = "europe-west8"
LLM = "gemini-2.0-flash-001"

# Safety configurations for each tool
ALLOWED_GCLOUD_COMMANDS = [
    "compute", "storage", "run", "functions", "config", "projects", 
    "auth", "iam", "services", "container", "ai", "ml"
]

ALLOWED_GSUTIL_COMMANDS = [
    "ls", "cp", "mv", "rm", "cat", "stat", "acl", "cors", "web", 
    "iam", "kms", "label", "logging", "notification", "versioning"
]

ALLOWED_BQ_COMMANDS = [
    "query", "ls", "mk", "rm", "cp", "extract", "load", "update", 
    "show", "head", "insert", "wait", "cancel"
]

ALLOWED_KUBECTL_COMMANDS = [
    "get", "describe", "logs", "exec", "apply", "create", "delete", 
    "scale", "rollout", "expose", "set", "explain", "config"
]

# Potentially destructive commands that require confirmation
DESTRUCTIVE_COMMANDS = ["delete", "remove", "reset", "unset", "clear", "rm", "drop"]

# Tool implementations
@tool
def run_gcloud_command(command: str) -> str:
    """
    Run a Google Cloud (gcloud) command.
    
    Args:
        command: The gcloud command to run, e.g., "gcloud compute instances list"
    
    Returns:
        The output of the command or an error message
    """
    # Validate that it's a gcloud command
    if not command.strip().startswith("gcloud "):
        return "Error: Only gcloud commands are supported. Command must start with 'gcloud'."
    
    # Extract the main command components
    components = command.strip().split()
    if len(components) < 2:
        return "Error: Invalid gcloud command format."
    
    # Check if the command category is allowed
    command_category = components[1]
    if command_category not in ALLOWED_GCLOUD_COMMANDS:
        return f"Error: The gcloud command category '{command_category}' is not allowed for security reasons."
    
    # Check for potentially destructive operations
    for destructive_cmd in DESTRUCTIVE_COMMANDS:
        if destructive_cmd in components:
            return f"Warning: The command contains '{destructive_cmd}' which could be destructive. Please confirm if you want to proceed with this operation."
    
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        return result.stdout if result.stdout else "Command executed successfully (no output)"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@tool
def run_gsutil_command(command: str) -> str:
    """
    Run a Google Cloud Storage (gsutil) command.
    
    Args:
        command: The gsutil command to run, e.g., "gsutil ls gs://my-bucket"
    
    Returns:
        The output of the command or an error message
    """
    # Validate that it's a gsutil command
    if not command.strip().startswith("gsutil "):
        return "Error: Only gsutil commands are supported. Command must start with 'gsutil'."
    
    # Extract the main command components
    components = command.strip().split()
    if len(components) < 2:
        return "Error: Invalid gsutil command format."
    
    # Check if the command category is allowed
    command_category = components[1]
    if command_category not in ALLOWED_GSUTIL_COMMANDS:
        return f"Error: The gsutil command '{command_category}' is not allowed for security reasons."
    
    # Check for potentially destructive operations
    for destructive_cmd in DESTRUCTIVE_COMMANDS:
        if destructive_cmd in components:
            return f"Warning: The command contains '{destructive_cmd}' which could be destructive. Please confirm if you want to proceed with this operation."
    
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        return result.stdout if result.stdout else "Command executed successfully (no output)"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@tool
def run_bq_command(command: str) -> str:
    """
    Run a BigQuery (bq) command.
    
    Args:
        command: The bq command to run, e.g., "bq query --use_legacy_sql=false 'SELECT * FROM dataset.table LIMIT 10'"
    
    Returns:
        The output of the command or an error message
    """
    # Validate that it's a bq command
    if not command.strip().startswith("bq "):
        return "Error: Only bq commands are supported. Command must start with 'bq'."
    
    # Extract the main command components
    components = command.strip().split()
    if len(components) < 2:
        return "Error: Invalid bq command format."
    
    # Check if the command category is allowed
    command_category = components[1]
    if command_category not in ALLOWED_BQ_COMMANDS:
        return f"Error: The bq command '{command_category}' is not allowed for security reasons."
    
    # Check for potentially destructive operations
    for destructive_cmd in DESTRUCTIVE_COMMANDS:
        if destructive_cmd in components:
            return f"Warning: The command contains '{destructive_cmd}' which could be destructive. Please confirm if you want to proceed with this operation."
    
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        return result.stdout if result.stdout else "Command executed successfully (no output)"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@tool
def run_kubectl_command(command: str) -> str:
    """
    Run a Kubernetes (kubectl) command.
    
    Args:
        command: The kubectl command to run, e.g., "kubectl get pods"
    
    Returns:
        The output of the command or an error message
    """
    # Validate that it's a kubectl command
    if not command.strip().startswith("kubectl "):
        return "Error: Only kubectl commands are supported. Command must start with 'kubectl'."
    
    # Extract the main command components
    components = command.strip().split()
    if len(components) < 2:
        return "Error: Invalid kubectl command format."
    
    # Check if the command category is allowed
    command_category = components[1]
    if command_category not in ALLOWED_KUBECTL_COMMANDS:
        return f"Error: The kubectl command '{command_category}' is not allowed for security reasons."
    
    # Check for potentially destructive operations
    for destructive_cmd in DESTRUCTIVE_COMMANDS:
        if destructive_cmd in components:
            return f"Warning: The command contains '{destructive_cmd}' which could be destructive. Please confirm if you want to proceed with this operation."
    
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        return result.stdout if result.stdout else "Command executed successfully (no output)"
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr if e.stderr else str(e)}"
    except Exception as e:
        return f"Unexpected error: {str(e)}"

@tool
def get_tool_help(tool: str, topic: str = "") -> str:
    """
    Get help for any supported GCP tool.
    
    Args:
        tool: The tool to get help for ("gcloud", "gsutil", "bq", or "kubectl")
        topic: The specific topic or command to get help for
        
    Returns:
        Help information for the specified tool and topic
    """
    valid_tools = ["gcloud", "gsutil", "bq", "kubectl"]
    if tool not in valid_tools:
        return f"Error: Invalid tool '{tool}'. Valid tools are: {', '.join(valid_tools)}"
    
    command = f"{tool} {topic} --help"
    
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True, 
            text=True, 
            capture_output=True
        )
        # Trim output if it's too long
        output = result.stdout
        if len(output) > 2000:
            output = output[:2000] + "...\n(Output truncated for brevity)"
        return output
    except subprocess.CalledProcessError as e:
        return f"Error getting help: {e.stderr if e.stderr else str(e)}"

@tool
def list_available_commands(tool: str = "") -> str:
    """
    List the available categories of commands for a specific tool or all tools.
    
    Args:
        tool: The tool to list commands for ("gcloud", "gsutil", "bq", "kubectl"), or empty for all tools
    
    Returns:
        A list of allowed command categories with examples
    """
    tool_commands = {
        "gcloud": {
            "commands": ALLOWED_GCLOUD_COMMANDS,
            "examples": {
                "compute": "gcloud compute instances list",
                "storage": "gcloud storage ls",
                "run": "gcloud run services list",
                "functions": "gcloud functions list",
                "config": "gcloud config list",
                "projects": "gcloud projects list",
                "auth": "gcloud auth list",
                "iam": "gcloud iam roles list",
                "services": "gcloud services list",
                "container": "gcloud container clusters list",
                "ai": "gcloud ai models list",
            }
        },
        "gsutil": {
            "commands": ALLOWED_GSUTIL_COMMANDS,
            "examples": {
                "ls": "gsutil ls gs://my-bucket",
                "cp": "gsutil cp file.txt gs://my-bucket/",
                "mv": "gsutil mv gs://my-bucket/file.txt gs://my-bucket/folder/",
                "rm": "gsutil rm gs://my-bucket/file.txt",
                "acl": "gsutil acl get gs://my-bucket/file.txt",
                "iam": "gsutil iam get gs://my-bucket",
            }
        },
        "bq": {
            "commands": ALLOWED_BQ_COMMANDS,
            "examples": {
                "query": "bq query --use_legacy_sql=false 'SELECT * FROM dataset.table LIMIT 10'",
                "ls": "bq ls",
                "mk": "bq mk new_dataset",
                "rm": "bq rm dataset.table",
                "show": "bq show dataset.table",
                "head": "bq head dataset.table",
            }
        },
        "kubectl": {
            "commands": ALLOWED_KUBECTL_COMMANDS,
            "examples": {
                "get": "kubectl get pods",
                "describe": "kubectl describe pod my-pod",
                "logs": "kubectl logs my-pod",
                "apply": "kubectl apply -f deployment.yaml",
                "create": "kubectl create deployment my-app --image=my-image:tag",
                "delete": "kubectl delete pod my-pod",
            }
        }
    }
    
    if tool and tool not in tool_commands:
        return f"Error: Invalid tool '{tool}'. Valid tools are: {', '.join(tool_commands.keys())}"
    
    result = ""
    
    if tool:
        # List commands for a specific tool
        tool_info = tool_commands[tool]
        result = f"Available {tool} commands:\n\n"
        for category in tool_info["commands"]:
            result += f"- {category}"
            if category in tool_info["examples"]:
                result += f" (Example: {tool_info['examples'][category]})"
            result += "\n"
    else:
        # List all tools and some example commands
        result = "Available GCP tools and example commands:\n\n"
        for tool_name, tool_info in tool_commands.items():
            result += f"## {tool_name.upper()}\n"
            # Show a few examples for each tool
            examples = list(tool_info["examples"].items())[:3]  # Limit to 3 examples
            for category, example in examples:
                result += f"- {category}: {example}\n"
            result += "\n"
    
    result += "\nTo get help on any tool or command, use the get_tool_help tool."
    return result

# Collect all tools
tools = [
    run_gcloud_command, 
    run_gsutil_command, 
    run_bq_command, 
    run_kubectl_command,
    get_tool_help, 
    list_available_commands
]

# Set up the language model
llm = ChatVertexAI(
    model=LLM, location=LOCATION, temperature=0, max_tokens=8192, streaming=True
).bind_tools(tools)

# Define workflow components
def should_continue(state: MessagesState) -> str:
    """Determines whether to use tools or end the conversation."""
    last_message = state["messages"][-1]
    return "tools" if last_message.tool_calls else END

def call_model(state: MessagesState, config: RunnableConfig) -> dict[str, BaseMessage]:
    """Calls the language model and returns the response."""
    system_message = """You are a Google Cloud Assistant that helps users interact with Google Cloud via natural language.

You can:
1. Run gcloud, gsutil, bq, and kubectl commands on behalf of the user
2. Provide help and guidance on all supported commands
3. Explain Google Cloud concepts
4. List available command categories for each tool

When users ask to perform actions on Google Cloud:
- Translate their natural language requests into appropriate commands
- For safety, when destructive operations (delete, remove, etc.) are requested, ask the user to confirm before executing
- Always explain what each command does before running it
- If a command might not be what the user intended, suggest alternatives

For security reasons, you can only run commands from approved categories.

When presenting command output, format it nicely for readability.

Examples of what you can help with:
- "List all my GCS buckets" → gsutil ls
- "Show my running VMs" → gcloud compute instances list --filter="status=RUNNING"
- "Query my BigQuery table" → bq query with appropriate SQL
- "Show pods in my Kubernetes cluster" → kubectl get pods

For complex operations, break them down into steps and explain each step.
"""
    messages_with_system = [{"type": "system", "content": system_message}] + state["messages"]
    # Forward the RunnableConfig object to ensure the agent is capable of streaming the response.
    response = llm.invoke(messages_with_system, config)
    return {"messages": response}

# Create the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))
workflow.set_entry_point("agent")

# Define graph edges
workflow.add_conditional_edges("agent", should_continue)
workflow.add_edge("tools", "agent")

# Compile the workflow
agent = workflow.compile()
"""
# Testing utilities
def test_agent(query: str) -> None:
    
    Test the agent with a sample query.
    
    Args:
        query: The natural language query to test

    print(f"Testing query: {query}")
    print("-" * 50)
    
    # Initialize the agent state
    state = {"messages": [{"type": "human", "content": query}]}
    
    # Run the agent
    for chunk in agent.stream(state):
        if "messages" in chunk and chunk["messages"]:
            message = chunk["messages"][-1]
            if hasattr(message, "content") and message.content:
                print(message.content)
    
    print("-" * 50)
    print("Test complete")

# Sample test queries
SAMPLE_QUERIES = [
    # Basic gcloud commands
    "List all my running VMs",
    "Show me all my GCP projects",
    
    # Basic gsutil commands
    "List all my GCS buckets",
    "Show the contents of my bucket named 'my-important-data'",
    
    # Basic BigQuery (bq) commands
    "Run a BigQuery query to count rows in my dataset.table",
    "Show me all datasets in my BigQuery project",
    "Get the schema of my BigQuery table 'mydataset.customers'",
    
    # Basic kubectl commands
    "Get all pods in my Kubernetes cluster",
    "Show the logs for the pod named 'frontend-app'",
    "Describe the deployment named 'backend-service'",
    
    # Multi-tool scenarios
    "Export data from my BigQuery table to a GCS bucket",
    "Create a VM and then copy files from a bucket to it",
    "Get logs from my Kubernetes pods and save them to a GCS bucket",
    
    # Help commands
    "Help me understand gsutil commands",
    "Explain the difference between kubectl apply and kubectl create",
    "Show me how to use BigQuery for data analysis",
]

# Main execution
if __name__ == "__main__":
    print("Google Cloud Console Agent")
    print("=" * 50)
    print("Available for testing with sample queries:")
    for i, query in enumerate(SAMPLE_QUERIES, 1):
        print(f"{i}. {query}")
    
    choice = input("\nEnter a number to test a sample query, or type your own query: ")
    
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(SAMPLE_QUERIES):
            query = SAMPLE_QUERIES[idx]
        else:
            query = choice
    except ValueError:
        query = choice
    
    test_agent(query)
"""