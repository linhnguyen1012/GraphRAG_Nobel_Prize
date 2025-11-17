import json 

def mini_check(text1, text2): 
    if not text1 or not text2: return False
    text1 = str(text1).lower()
    text2 = str(text2).lower()
    if text1 in text2 or text2 in text1: 
        return True
    return False

def valid_query(query_context, gold_context):
    if not query_context: return False
    if not gold_context and query_context: return False
    for item in gold_context: 
        if not any([mini_check(item, ct_item) for ct_item in query_context]): return False
    return True


def analyse(answer):
    true = sum(a is True for a in answer)
    false = sum(a is False for a in answer)
    no_attempt = sum(a is None for a in answer)

    pre = true / (true + false) if (true + false) > 0 else 0
    acc = true / (true + false + no_attempt) if len(answer) > 0 else 0

    return {
        "true": true,
        "false": false,
        "no_attempt": no_attempt,
        "accuracy": acc,
        "precision": pre
    }



def main(file): 
    data = [json.loads(line) for line in open(file).readlines()]
    answer_results = []
    query_results = []

    for line in data: 

        if line['model_answer']['context']: 
            answer_results.append(line['judge_result'])
        else: 
            answer_results.append(None)

        if valid_query(line['model_answer']['context'], line['metadata']['gold_context']): 
            query_results.append(True)
        else: 
            print(line['model_answer']['context'], line['metadata']['gold_context'])
            query_results.append(False)
    
    return {
        "query_analyse": analyse(query_results), 
        "overall_analyse": analyse(answer_results)
    }

        
if __name__ == "__main__": 
    print(main("/data2/linhnguyen/CComputing/graphRAG/CS-E4780-project2/_log/gpt-4.1-mini.jsonl"))