# Graph RAG with Kuzu, DSPy and marimo

Source code for course project to build a Graph RAG with Kuzu, [DSPy](https://dspy.ai/) and [marimo](https://docs.marimo.io/) (open source, reactive notebooks for Python).

📄 **[Read the full project report (PDF)](./GraphRAG_Nobel_Prize-3.pdf)** for detailed system architecture, evaluation results, and analysis.

## Setup

We recommend using the `uv` package manager
to manage dependencies.

```bash
# Uses the local pyproject.toml to add dependencies
uv sync
# Or, add them manually
uv add marimo dspy kuzu polars pyarrow pydantic-ai functools python-dotenv
# Don't forget to source virtual env
source .venv/bin/activate
```

### Required Dependencies

This project requires the following key packages:
- **marimo**: Interactive Python notebooks
- **dspy** or **pydantic-ai**: LLM framework (this project uses pydantic-ai)
- **kuzu**: Graph database Python bindings
- **polars**, **pyarrow**: Data processing
- **functools**: Built-in Python module for LRU caching
- **python-dotenv**: Environment variable management for API keys

### Start Kuzu Database
```bash
docker compose up
```
Go to `localhost:8000` you can check the UI of the database

### Create basic graph
marimo simultaneously serves three functions. You can run Python code as a script, a notebook, or as an app!

#### Run as a notebook

You can manually activate the local uv virtual environment and run marimo as follows:
```bash
# Open a marimo notebook in edit mode
marimo edit eda.py
```
Or, you can simply use uv to run marimo:
```bash
uv run marimo edit eda.py
```

#### Run as an app

To run marimo in app mode, use the `run` command.

```bash
uv run marimo run eda.py
```

#### Run as a script

Each cell block in a marimo notebook is encapsulated into functions, so you can reuse them in other
parts of your codebase. You can also run the marimo file (which is a `*.py` Python file) as you
would any other script:

```bash
uv run eda.py
```
Returns:
```
726 laureate nodes ingested
399 prize nodes ingested
739 laureate prize awards ingested
```

Depending on the stage of your project and who is consuming your code and data, each mode can be
useful in its own right. Have fun using marimo and Kuzu!

### Enrich the graph 
Create the required graph in Kuzu using the following script:

```bash
uv run create_nobel_api_graph.py
```

Alternatively, you can open/edit the script as a marimo notebook and run each cell individually to
go through the entire workflow step by step.

```bash
uv run marimo edit create_nobel_api_graph.py
```

### Run the Graph RAG pipeline as a notebook

To iterate on your ideas and experiment with your approach, you can work through the Graph RAG
notebook in the following marimo file:

```bash
uv run marimo run demo_workflow.py
```

The purpose of this file is to demonstrate the workflow in distinct stages, making it easier to
understand and modify each part of the process in marimo.

### Run the Graph RAG app

A demo app is provided in `graph_rag.py` for reference. It's very basic (just question-answering), but the
idea is general and this can be extended to include advanced retrieval workflows (vector + graph),
interactive graph visualizations via anywidget, and more. More on this in future tutorials!

```bash
uv run marimo run graph_rag.py
```

## Running the Evaluation Pipeline

### Prerequisites

Before running the evaluation, ensure you have:
1. Completed the setup steps above (dependencies, Kuzu database, and graph creation)
2. Created the output directory for logs:
   ```bash
   mkdir -p _log
   ```
3. Configured your LLM API credentials (OpenAI, Gemini) in a `.env` file

### Prepare Your Evaluation Data

The evaluation pipeline uses benchmark data from the `data/` directory. To customize:

1. **Edit the benchmark questions**: Modify `data/_eval_data.json` with your own questions and expected answers
2. **Format structure**: Each entry should include:
   ```json
   {
     "typeOfQuestion": "category description",
     "answer": "expected gold answer",
     "expected_query": "optional expected Cypher query",
     "context": ["expected context triples"],
     "questions": ["main question", "paraphrase 1", "paraphrase 2", ...]
   }
   ```
3. The system will automatically expand each question group with its paraphrases

### Option 1: Run Single Model Evaluation

To run the evaluation for a single model configuration, use `run.py` directly:

```bash
# Set environment variables and run
model="gpt-4.1-mini" max_retries=3 python run.py
```

Parameters:
- `model`: Model name (e.g., `gpt-4.1-mini`, `gpt-4.1`, `gpt-5-mini`, `gpt-5`, `gemini-2.5-flash`)
- `max_retries`: Maximum number of Text2Cypher repair attempts (typically `1` or `3`)

The output will be logged to `_log/{model}_attempt_{max_retries}.jsonl`

### Option 2: Batch Evaluation Across Models

To systematically evaluate multiple models and retry budgets, use the provided shell script:

```bash
bash main.sh
```

This will:
1. Loop through all configured models: `gpt-4.1-mini`, `gpt-4.1`, `gpt-5-mini`, `gpt-5`
2. Test each with retry budgets of 1 and 3
3. Save execution logs to `_log/running_log_{model}_{retries}`
4. Save detailed evaluation results to `_log/{model}_attempt_{retries}.jsonl`

**Note**: To test Gemini models, uncomment the Gemini line and comment the OpenAI models in `main.sh`:
```bash
# models=("gpt-4.1-mini" "gpt-4.1" "gpt-5-mini" "gpt-5")
models=("gemini-2.5-flash")
```

### Understanding the Output

Each evaluation run produces two types of output:

1. **Execution log** (`_log/running_log_*`): Real-time pipeline execution details
2. **Evaluation results** (`_log/{model}_attempt_{retries}.jsonl`): Structured JSON lines with:
   - Input question
   - Generated Cypher query
   - Retrieved context
   - Model answer
   - LLM judge verdict and reasoning
   - Query grounding and answer correctness metrics

