import json
results_path = './papers_cleaned_results.json'
golden_path = './papers_cleaned.json'
repo_dump_dir = './1105_test'

def get_repos(keywords):
    repos = []
    for keyword in keywords:
        with open(repo_dump_dir + '/' + keyword + '.json') as f:
            repos += json.load(f)
    return [repo['repo_name'] for repo in repos]

def get_predict(result):
    try:
        result_json = json.loads(result)
    except:
        return result
    key_name = ['repo_name', 'selected_repo']
    for key in key_name:
        if key in result_json:
            return result_json[key]


def process_result(path=results_path):
    gt = {}
    with open(golden_path) as f:
        golden_results = json.load(f)
    for g_result in golden_results:
        gt[g_result['title']] = g_result['repo_info']['github_url']
    
    with open(path) as f:
        lines = f.readlines()
    hit = 0
    recall_1 = 0
    recall_5 = 0
    search_recall = 0
    search_right_recall_5_false = 0
    recall_5_right_hit_false = 0
    recall_1_right_hit_false = 0
    for line in lines:
        data_line = json.loads(line)
        title = data_line['title']
        predict = get_predict(data_line['result']['result'])
        label = gt[title]
        searcher_right = False
        reviewer_right = False
        writer_right = False
        writer_5_right = False
        if predict in label:
            reviewer_right = True
        
        writer_5 = data_line['result']['top5']
        for repo in writer_5:
            if repo in label:
                writer_5_right = True
                break
        if writer_5[0] in label:
            writer_right = True

        search_repos = get_repos(data_line['result']['keywords'])
        for repo in search_repos:
            if repo in label:
                searcher_right = True
                break

        if reviewer_right:
            hit += 1
        if writer_right:
            recall_1 += 1
        if writer_5_right:
            recall_5 += 1
        if searcher_right:
            search_recall += 1
        if searcher_right and not writer_5_right:
            search_right_recall_5_false += 1
        if writer_5_right and not reviewer_right:
            recall_5_right_hit_false += 1
        if writer_right and not reviewer_right:
            recall_1_right_hit_false += 1
    
    print(search_right_recall_5_false)
    print(recall_5_right_hit_false)
    print(recall_1_right_hit_false)
    print(hit)
    print(recall_5)
    print(recall_1)
    print(search_recall)



def main():
    process_result()

if __name__ == '__main__':
    main()