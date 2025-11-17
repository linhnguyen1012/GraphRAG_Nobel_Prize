from typing import Any
from functools import lru_cache
from src.schema import *
from src.agents import *
from db_interaction import KuzuDatabaseManager
import time


class GraphRAG:

    
    def __init__(self, db_manager: KuzuDatabaseManager):
        self.db_manager = db_manager
        self.schema = str(db_manager.get_schema_dict)
    
    def prune_schema(self, question: str) -> GraphSchema:
        result = prune_schema_agent.run_sync(
            f"Question: {question}\n\nInput Schema: {self.schema}"
        )
        output_str = result.output
        if output_str.startswith('```'):
            output_str = output_str.split('```')[1]
            if output_str.startswith('json'):
                output_str = output_str[4:]
            output_str = output_str.strip()


        import json
        data = json.loads(output_str)
        
        if 'nodes' in data:
            for node in data['nodes']:
                if 'properties' in node and node['properties']:
                    fixed_props = []
                    for prop in node['properties']:
                        if isinstance(prop, str):
                            fixed_props.append({'name': prop, 'type': 'string'})
                        elif isinstance(prop, dict):
                            fixed_props.append(prop)
                    node['properties'] = fixed_props
        
        if 'edges' in data:
            for edge in data['edges']:
                if 'properties' in edge and edge['properties']:
                    fixed_props = []
                    for prop in edge['properties']:
                        if isinstance(prop, str):
                            fixed_props.append({'name': prop, 'type': 'string'})
                        elif isinstance(prop, dict):
                            fixed_props.append(prop)
                    edge['properties'] = fixed_props
        
        return GraphSchema(**data)
    
    def validate_query_with_explain(self, cypher_query: str) -> tuple[bool, str]:
        """
        Validate query with EXPLAIN.
        
        Args:
            cypher_query: The Cypher query to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            explain_query = f"EXPLAIN {cypher_query}"
            self.db_manager.execute_query(explain_query)
            return True, ""
        except Exception as e:
            error_msg = str(e)
            print(f"Query validation failed: {error_msg}")
            return False, error_msg
    
    @lru_cache(maxsize=128)
    def generate_cypher(self, question: str, pruned_schema: GraphSchema, 
                       previous_attempts: list[dict] = None) -> str:
        """
        Generate Cypher query from question and schema.
        Cached to avoid regenerating queries for identical inputs.
        
        Args:
            question: The natural language question
            pruned_schema: The pruned graph schema
            previous_attempts: List of previous failed attempts with queries and errors
            
        Returns:
            Generated Cypher query string
        """
        prompt = f"Question: {question}\n\nInput Schema: {pruned_schema.model_dump_json()}"
        
        if previous_attempts:
            prompt += "\n\n### Previous Failed Attempts ###"
            for i, attempt in enumerate(previous_attempts):
                prompt += f"\n\nAttempt {i}:"
                prompt += f"\nGenerated Query: {attempt['query']}"
                prompt += f"\nError/Issue: {attempt['error']}"
            prompt += "\n\nPlease learn from these failures and generate a corrected query that addresses all the issues above."
        
        print("Attempt Prompt", prompt)
        result = text2cypher_agent.run_sync(prompt)
        
        # The output is a string, need to parse it
        output_str = result.output
        # Remove markdown code blocks if present
        if output_str.startswith('```'):
            output_str = output_str.split('```')[1]
            if output_str.startswith('json'):
                output_str = output_str[4:]
            output_str = output_str.strip()
            print(output_str)
        # Parse JSON and get query
        import json
        data = json.loads(output_str)
        return data['query']
    
    @lru_cache(maxsize=128)
    def generate_answer(self, question: str, cypher_query: str, context: str) -> str:
        """
        Generate natural language answer from context.
        Cached to avoid regenerating answers for identical inputs.
        """
        result = answer_agent.run_sync(
            f"Question: {question}\n\nCypher Query: {cypher_query}\n\nContext: {context}"
        )
        # The output is a string, need to parse it
        output_str = result.output
        # Remove markdown code blocks if present
        if output_str.startswith('```'):
            output_str = output_str.split('```')[1]
            if output_str.startswith('json'):
                output_str = output_str[4:]
            output_str = output_str.strip()
        # Parse JSON and get response
        import json
        data = json.loads(output_str)
        return data['response']
    
    def run(self, question: str, max_retries: int = 1) -> dict[str, Any]:
        """
        Full pipeline..
        
        Args:
            question: Natural language question
            max_retries: Maximum number of query generation attempts
            
        Returns:
            Dictionary with question, query, and answer
        """
        print(f"\nQuestion: {question}")
        
        print("Pruning schema...")
        pruned_schema = self.prune_schema(question)
        
        cypher_query = None
        results = None
        previous_attempts = []
        
        # Retry loop for query generation and execution
        for attempt in range(max_retries):
            print(f"\nAttempt {attempt + 1}/{max_retries}: Generating Cypher query...")
            print("Previous fail cases", previous_attempts)
            
            try:
                
                cypher_query = self.generate_cypher(question, pruned_schema, previous_attempts)
                print(f"Generated query: {cypher_query}")
                
                # Validate query with EXPLAIN
                print("Validating query with EXPLAIN...")
                is_valid, error_msg = self.validate_query_with_explain(cypher_query)
                
                if not is_valid:
                    print(f"Query validation failed: {error_msg}")
                    previous_attempts.append({
                        'query': cypher_query,
                        'error': f"Validation Error (EXPLAIN): {error_msg}"
                    })
                    continue
                
                print("Query validation passed. Executing query on database...")
                results = self.db_manager.execute_query(cypher_query)
                
                if results is None or len(results) == 0:
                    print("Query returned empty results.")
                    previous_attempts.append({
                        'query': cypher_query,
                        'error': "Query executed successfully but returned no results. The query may need to be adjusted to find matching data in the graph."
                    })
                    continue
                
                print(f"Query succeeded with {len(results)} results")
                break
                
            except Exception as e:
                error_msg = str(e)
                print(f"Query execution failed: {error_msg}")
                previous_attempts.append({
                    'query': cypher_query if cypher_query else "Failed to generate query",
                    'error': f"Execution Error: {error_msg}"
                })
                continue
        
        if results is None or len(results) == 0:
            print(f"\nAll {max_retries} attempts failed or returned empty results.")
            return {
                "question": question,
                "query": cypher_query if cypher_query else "Failed to generate valid query",
                "answer": "I don't have enough information to answer this question.",
                "context": None
            }
        
        print("Generating natural language answer...")
        context = str(results)
        answer = self.generate_answer(question, cypher_query, context)
        
        response = {
            "question": question,
            "query": cypher_query,
            "answer": answer,
            "context": results
        }
        time.sleep(1)#Prevent the API Connection Error due to calling too much time (We will auto minus in the report)
        return response


    # ##Detail Evaluation##

    # def valid_query(self, labeled_query='', expected_query=''):
    #     context = self.db_manager.execute_query(cypher_query)
    #     query_context = self.db_manager.execute_query(cypher_query)
    #     ...
    # return True


    # def analyse(self, answer):
    #     true = sum(a is True for a in answer)
    #     false = sum(a is False for a in answer)
    #     no_attempt = sum(a is None for a in answer)

    #     pre = true / (true + false) if (true + false) > 0 else 0
    #     acc = true / (true + false + no_attempt) if len(answer) > 0 else 0

    #     return {
    #         "true": true,
    #         "false": false,
    #         "no_attempt": no_attempt,
    #         "accuracy": acc,
    #         "precision": pre
    #     }



    # def main(self, file): 
    #     data = [json.loads(line) for line in open(file).readlines()]
    #     answer_results = []
    #     query_results = []

    #     for line in data: 

    #         if line['model_answer']['context']: 
    #             answer_results.append(line['judge_result'])
    #         else: 
    #             answer_results.append(None)

    #         if self.valid_query(): 
    #             query_results.append(True)
    #         else: 
    #             query_results.append(False)
        
    #     return {
    #         "query_analyse": self.analyse(query_results), 
    #         "overall_analyse": self.analyse(answer_results)
    #     }