from src.schema import *
from pydantic_ai import Agent
import os, json
from typing import Any
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.models.gemini import GeminiModel
from dotenv import load_dotenv
load_dotenv("your_path/.env")

if "gpt" in os.environ['model']:    
    model = OpenAIChatModel(os.environ['model'])
elif "gemini" in os.environ['model']:
    model = GeminiModel(os.environ['model'])
    print(model)
else: 
    raise "Choose Openai model or Gemini Model only or Config Others in this Scripts"


# Create typed agents
prune_schema_agent = Agent[None, GraphSchema](
    model,
    system_prompt="""
    Understand the given labelled property graph schema and the given user question. Your task
    is to return ONLY the subset of the schema (node labels, edge labels and properties) that is
    relevant to the question.
        - The schema is a list of nodes and edges in a property graph.
        - The nodes are the entities in the graph.
        - The edges are the relationships between the nodes.
        - Properties of nodes and edges are their attributes, which helps answer the question.
    
    Return a JSON object with 'nodes' and 'edges' arrays matching the GraphSchema structure.
    """
)


text2cypher_agent = Agent[None, Query](
    model,
    system_prompt="""
    Translate the question into a valid Cypher query that respects the graph schema.

    <SYNTAX>
    - When matching on Scholar names, ALWAYS match on the `knownName` property
    - For countries, cities, continents and institutions, you can match on the `name` property
    - Use short, concise alphanumeric strings as names of variable bindings (e.g., `a1`, `r1`, etc.)
    - Always strive to respect the relationship direction (FROM/TO) using the schema information.
    - When comparing string properties, ALWAYS do the following:
        - Lowercase the property values before comparison
        - Use the WHERE clause
        - Use the CONTAINS operator to check for presence of one substring in the other
    - DO NOT use APOC as the database does not support it.
    </SYNTAX>

    <RETURN_RESULTS>
    - If the result is an integer, return it as an integer (not a string).
    - When returning results, return property values rather than the entire node or relationship.
    - Do not attempt to coerce data types to number formats (e.g., integer, float) in your results.
    - NO Cypher keywords should be returned by your query.
    </RETURN_RESULTS>
    
    Return a JSON object with a 'query' field containing the Cypher query as a single line string.
    """
)


answer_agent = Agent[None, Answer](
    model,
    system_prompt="""
    - Use the provided question, the generated Cypher query and the context to answer the question.
    - If the context is empty, state that you don't have enough information to answer the question.
    - When dealing with dates, mention the month in full.
    
    Return a JSON object with a 'response' field containing your answer.
    """
)

