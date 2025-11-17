import asyncio, json, os
from dotenv import load_dotenv
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_evals import Case, Dataset
from pydantic_evals.evaluators import LLMJudge
from src.graph_rag_compute import GraphRAG
import src.detail_eval as detail_eval
from db_interaction import KuzuDatabaseManager
import copy 

load_dotenv()

LOG_PATH = f"_log/{os.environ['model']}_attempt_{os.environ['max_retries']}.jsonl"

judge = LLMJudge(
    rubric=(
        "You are a strict evaluator. Compare the model's answer (ctx.output.answer) "
        "with the expected ouptut (ctx.expected_output). "
        "Return JSON: {match: bool, reasoning: str}. "
        "Mark as match if they mean the same thing, even if phrased differently.", 
        "If answer is 'lack of information' but the expected output is not None, auto return False"
    ),
    model=OpenAIChatModel("gpt-4o-mini"),
)



async def answer_question(inputs: dict):
    """Wraps GraphRAG.run in async form for Dataset.evaluate()."""
    question = inputs["question"]
    max_retries = int(os.environ['max_retries'])
    result = await asyncio.to_thread(graph_rag.run, question, max_retries)
    if isinstance(result, dict) and "answer" in result:
        return result
    return (result)


def log_case(data: dict):
    os.makedirs(os.path.dirname(LOG_PATH) or ".", exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


async def main():
    db_name = "nobel.kuzu"
    print(f"Connecting to database: {db_name}")
    db_manager = KuzuDatabaseManager(db_name)
    global graph_rag
    graph_rag = GraphRAG(db_manager)

    # Load evaluation data
    # distill_eval_set = json.load(open("data/_distill_data.json"))
    full_eval_set = json.load(open("data/_eval_data.json"))
    benchmarking_evalset = []
    for eval_set_ in full_eval_set: 
        for question in eval_set_["questions"]: 
            item = copy.deepcopy(eval_set_)
            item['question'] = question 
            benchmarking_evalset.append(item) 

    dataset = Dataset(
        cases=[
            Case(
                name=f"case_{idx}",
                inputs={"question": item["question"]},
                expected_output=item["answer"],
                metadata={
                    "expected_query": item.get("expected_query"),
                    "gold_context": item.get("context")
                }            )
            for idx, item in enumerate(benchmarking_evalset)
        ],
        evaluators=[judge],
    )

    print("Graph RAG Evaluation with LLM-Judge")
    report = await dataset.evaluate(answer_question)
    report.print()


    with open(LOG_PATH, "w", encoding="utf-8") as f:
        pass  # clear file at start


    for case in report.cases:
        eval_result = case.assertions.get("LLMJudge")

        record = {
            "case_id": case.name,
            "question": case.inputs.get("question"),
            "gold_answer": case.expected_output,
            "model_answer": case.output,
            "metadata": case.metadata,
            "judge_result": getattr(eval_result, "value", None),
            "judge_reasoning": getattr(eval_result, "reason", None),
        }

        log_case(record)
        print(f"Logged {case.name}: match={record['judge_result']}")

    print(detail_eval.main(LOG_PATH))

    db_manager.close()



if __name__ == "__main__":
    asyncio.run(main())
