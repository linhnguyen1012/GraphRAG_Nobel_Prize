import os, json
from typing import Any
from pydantic import BaseModel, Field


class Property(BaseModel):
    name: str
    type: str = Field(description="Data type of the property")


class Node(BaseModel):
    label: str
    properties: list[Property] | None = None


class Edge(BaseModel):
    label: str = Field(description="Relationship label")
    from_: str = Field(alias="from", description="Source node label")
    to: str = Field(description="Target node label")
    properties: list[Property] | None = None


class GraphSchema(BaseModel):
    nodes: list[Node]
    edges: list[Edge]


class Query(BaseModel):
    query: str = Field(description="Valid Cypher query with no newlines")


class Answer(BaseModel):
    response: str = Field(description="Natural language answer to the question")

