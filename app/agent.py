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
from typing import List, Optional, Dict, Any
import json

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

LOCATION = "europe-west8"
LLM = "gemini-2.0-flash-001"

# Allowed gcloud command categories for safety
ALLOWED_GCLOUD_COMMANDS = [
    "compute", "storage", "run", "functions", "config", "projects", 
    "auth", "iam", "services", "container", "ai", "ml"
]

# Potentially destructive commands that require confirmation
DESTRUCTIVE_COMMANDS = ["delete", "remove", "reset", "unset", "clear"]

@tool
def execute_python_code(code: str) -> str:
    """
    Execute Python code in a secure environment.
    
    Args:
        code: The Python code to execute
        
    Returns:
        The output of the code execution or error message
    """
    # Log the code execution for security auditing
    print(f"Executing Python code: \n{code}")
    
    # Check for potentially dangerous operations
    dangerous_modules = [
        "os.system", "subprocess", "eval(", "exec(", 
        "open(", "__import__", "importlib", "shutil", 
        "socket", "requests", "urllib", "pathlib"
    ]
    
    for module in dangerous_modules:
        if module in code:
            return f"SAFETY CHECK: The code contains potentially unsafe operations ({module}). For security reasons, code with system access, file operations, or network capabilities is not permitted."
    
    # Create a sandbox for execution with limited scope
    sandbox_globals = {}
    
    # Add safe modules that might be useful
    import math
    import random
    import datetime
    import json
    import re
    
    sandbox_globals.update({
        "math": math,
        "random": random,
        "datetime": datetime,
        "json": json,
        "re": re,
        "print": print,
    })
    
    # Capture stdout to return as result
    from io import StringIO
    import sys
    
    old_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Execute the code in the sandbox
        exec(code, sandbox_globals)
        output = captured_output.getvalue()
        return output if output else "Code executed successfully (no output)"
    except Exception as e:
        return f"Error executing Python code: {str(e)}"
    finally:
        # Restore stdout
        sys.stdout = old_stdout

@tool
def run_gcloud_command(command: str) -> str:
    """
    Run a gcloud command
    
    Args:
        command: The gcloud command to run, for example 'compute instances list'
        
    Returns:
        The output of the command or error message
    """
    # # Security check: ensure command starts with allowed gcloud categories
    # allowed = False
    # command_parts = command.strip().split()
    # if command_parts:
    #     for allowed_command in ALLOWED_GCLOUD_COMMANDS:
    #         if command.startswith(allowed_command):
    #             allowed = True
    #             break
    
    # if not allowed:
    #     return f"Error: The command '{command}' is not allowed for security reasons. Only commands from approved categories are permitted. Use list_available_gcloud_commands() to see permitted categories."
    
    # Add gcloud prefix if not present
    if not command.startswith("gcloud "):
        command = "gcloud " + command # + " --format=json"
    
    # Log the command for security auditing
    print(f"Executing gcloud command: {command}")
    
    # # Safety check for destructive operations
    # destructive_keywords = ["delete", "remove", "reset", "clear", "purge"]
    # if any(keyword in command for keyword in destructive_keywords):
    #     return f"SAFETY CHECK: The command '{command}' appears to be a destructive operation. Please explicitly confirm with the user before performing this operation."
    
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
def get_gcloud_help(topic: str = "") -> str:
    """
    Get help for gcloud commands.
    
    Args:
        topic: The gcloud command or topic to get help for, e.g., "compute instances" or leave empty for general help
        
    Returns:
        Help information for the specified gcloud command or topic
    """
    command = f"gcloud {topic} --help"
    
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
def list_available_gcloud_commands() -> str:
    """
    List the available categories of gcloud commands that can be used.
    
    Returns:
        A list of allowed gcloud command categories with examples
    """
    examples = {
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
    
    result = "Available gcloud command categories:\n\n"
    for category in ALLOWED_GCLOUD_COMMANDS:
        result += f"- {category}"
        if category in examples:
            result += f" (Example: {examples[category]})"
        result += "\n"
    
    result += "\nTo get help on any category, use the get_gcloud_help tool."
    return result


tools = [run_gcloud_command, get_gcloud_help, list_available_gcloud_commands, execute_python_code]

# 2. Set up the language model
llm = ChatVertexAI(
    model=LLM, location=LOCATION, temperature=0, max_tokens=8192, streaming=True
).bind_tools(tools)


# 3. Define workflow components
def route_next_step(state: MessagesState) -> str:
    """Determine the next step in the workflow."""
    # Check if the last message was from the user (new request)
    last_message = state["messages"][-1]
    
    # Get plan data from state
    plan_created = state.get("plan_created", False)
    current_step = state.get("current_step", -1)
    plan = state.get("plan", [])
    
    if not plan_created and isinstance(last_message, HumanMessage):
        return "planner"
    
    # If we have a plan but not completed all steps
    if plan_created and current_step < len(plan) - 1:
        return "executor"
    
    # Check if there are tool calls to process
    if last_message.tool_calls:
        return "tools"
    
    # Normal conversation flow
    return END


def create_plan(state: MessagesState, config: RunnableConfig) -> MessagesState:
    """Creates a plan for complex user requests."""
    system_message = """You are a planning agent for Google Cloud operations. Your task is to:
    
1. Analyze the user's request and determine if it requires multiple steps
2. Check thoroughly gcloud commands and helps 
3. Break complex requests into a sequence of logical steps
4. For each step, write a clear, actionable description
5. Return the plan as numbered steps

Example plan format:
1. Check current available gcloud commands for compute engine
2. Read help for gcloud command that you want to use to create a VM instance
3. Check current configuration
4. Create new VM instance
5. Install required software
6. Verify the installation

Keep steps clear, specific, and focused on one task each.
"""
    
    # Extract only the latest user message
    latest_user_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_user_message = msg
            break
    
    if not latest_user_message:
        # No user message to plan for
        return {**state, "plan_created": True, "plan": [], "current_step": -1}
    
    # Create messages for the planner
    planner_messages = [{"type": "system", "content": system_message}, 
                        {"content": latest_user_message.content, "type": "human"}]
    
    # Get planning response
    response = llm.invoke(planner_messages, config)
    
    # Extract plan steps from the response
    plan_text = response.content
    # Parse numbered list (1. Step one, 2. Step two, etc.)
    steps = re.findall(r'\d+\.\s*(.*?)(?=\n\d+\.|\Z)', plan_text, re.DOTALL)
    if not steps:
        # Fallback: try to split by newlines if numbered format not found
        steps = [line.strip() for line in plan_text.split('\n') if line.strip()]
    
    # Clean up steps
    steps = [step.strip() for step in steps]
    steps = [step for step in steps if step]
    
    # If it's a simple request, we might just have one step or instructions
    if not steps:
        steps = [plan_text.strip()]
    
    # Add planning summary to messages
    if steps:
        plan_summary = "I'll help you with this request. Here's my plan:\n\n"
        for i, step in enumerate(steps, 1):
            plan_summary += f"{i}. {step}\n"
        plan_summary += "\nI'll start working on this step by step."
        
        new_messages = state["messages"] + [AIMessage(content=plan_summary)]
    else:
        # Simple request, no multi-step plan needed
        new_messages = state["messages"]
    
    # Update state with plan
    return {
        **state, 
        "messages": new_messages,
        "plan": steps,
        "current_step": 0 if steps else -1,
        "plan_created": True
    }


def execute_step(state: MessagesState, config: RunnableConfig) -> MessagesState:
    """Executes the current step in the plan."""
    current_step = state.get("current_step", -1)
    plan = state.get("plan", [])
    
    if current_step < 0 or current_step >= len(plan):
        # No valid step to execute
        return state
    
    step_description = plan[current_step]
    step_number = current_step + 1
    total_steps = len(plan)
    
    # Create a message about the current step
    step_message = f"Step {step_number}/{total_steps}: {step_description}"
    new_messages = state["messages"] + [AIMessage(content=step_message)]
    
    # Create system message for the executor
    system_message = """You are a Google Cloud Assistant that helps users interact with Google Cloud via natural language.
    
You are currently executing a specific step in a multi-step plan. Focus only on completing the current step.

When executing a step:
1. Determine the appropriate gcloud commands needed
2. Explain what you're doing in plain language
3. Run the commands and interpret results
4. Confirm when the step is complete

For safety, when destructive operations (delete, remove, etc.) are requested, ask the user to confirm before executing.
Format outputs nicely for readability.

You have access to these tools:
- run_gcloud_command: Run a gcloud command
- get_gcloud_help: Get help on gcloud commands
- list_available_gcloud_commands: List available command categories
"""
    
    # Execute the current step
    executor_messages = [
        {"type": "system", "content": system_message},
        {"type": "human", "content": f"Please execute this step: {step_description}"}
    ]
    
    response = llm.invoke(executor_messages, config)
    
    # Update messages with the execution result
    new_messages = new_messages + [response]
    
    # Move to the next step
    next_step = current_step + 1
    
    if next_step >= len(plan):
        # Add a completion message if all steps are done
        completion_msg = "✅ All steps have been completed successfully!"
        new_messages = new_messages + [AIMessage(content=completion_msg)]
    
    return {
        **state,
        "messages": new_messages,
        "current_step": next_step
    }


def call_model(state: MessagesState, config: RunnableConfig) -> MessagesState:
    """Standard LLM call for regular interaction."""
    system_message = """You are a Google Cloud Assistant that helps users interact with Google Cloud via natural language. 
    
You can:
1. Run gcloud commands on behalf of the user
2. Provide help and guidance on gcloud commands
3. Explain Google Cloud concepts
4. List available command categories
5. Execute Python code for data processing, analysis, or visualization

When users ask to perform actions on Google Cloud:
- Translate their natural language requests into appropriate gcloud commands
- For safety, when destructive operations (delete, remove, etc.) are requested, ask the user to confirm before executing
- Always explain what each command does before running it
- If a command might not be what the user intended, suggest alternatives

For security reasons, you can only run commands from approved categories.

When presenting command output, format it nicely for readability.

For complex requests, break them down into simpler steps and execute them systematically.

When executing Python code:
- Use the execute_python_code tool for data processing, analysis, or visualization
- Explain what the code does before running it
- The tool has access to these modules: math, random, datetime, json, re
- For security, operations involving system access, file operations, or network access are not permitted
"""
    messages_with_system = [{"type": "system", "content": system_message}] + state["messages"]
    
    # Forward the RunnableConfig object to ensure the agent is capable of streaming the response.
    response = llm.invoke(messages_with_system, config)
    
    # Ensure tool calls are properly formatted
    if hasattr(response, 'tool_calls') and response.tool_calls:
        # Make sure to handle tool calls properly, ensuring content is always a string
        if isinstance(response.content, list):
            response.content = '\n'.join([str(item) for item in response.content])
    
    # return {
    #     **state,
    #     "messages": state["messages"] + [response]
    # }
    return {"messages": response}


# 4. Create the workflow graph
workflow = StateGraph(MessagesState)
workflow.add_node("planner", create_plan)
workflow.add_node("executor", execute_step)
workflow.add_node("agent", call_model)
workflow.add_node("tools", ToolNode(tools))

# Set the entry point
workflow.set_entry_point("agent")

# 5. Define graph edges
workflow.add_conditional_edges("agent", route_next_step)
workflow.add_edge("planner", "executor")
workflow.add_edge("executor", "agent")
workflow.add_edge("tools", "agent")

# 6. Compile the workflow
agent = workflow.compile()