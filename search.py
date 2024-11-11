import requests
import os
import time
import openai
from dotenv import load_dotenv
load_dotenv()
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from github import Github
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from tenacity import (
    retry,
    retry_if_exception_type,
    wait_random_exponential,
)  # for exponential backoff
import json
gh_token = os.getenv('GH_TOKEN')
g = Github(gh_token)

def make_request(url, params=None):
    """Make a request with rate limit handling."""
    headers = {
            'Authorization': gh_token,
            'Content-Type':'application/json',
            'Accept':'application/json',
            'User-Agent': 'Mozilla/5.0'
        }
    while True:
        try:
            response = requests.get(url, headers=headers, params=params, verify=False, timeout=10, proxies={})
            if response.status_code == 403 and 'X-RateLimit-Remaining' in response.headers and response.headers['X-RateLimit-Remaining'] == '0':
                # We hit the rate limit, wait and try again
                reset_time = int(response.headers['X-RateLimit-Reset'])
                sleep_time = max(reset_time - time.time(), 0)
                print(f"Rate limit hit. Sleeping for {sleep_time} seconds.")
                time.sleep(sleep_time + 1)  # Adding 1 second just to be safe
            else:
                return response
        except Exception as e:
            print(f"An error occurred: {e}")
            time.sleep(5)  # Wait for some time before retrying

def save_json(data, file_path):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"save repos to {file_path}")

def check_readme(repo, least_star=0):
    while True:
        cnt = 0
        try:
            contents = repo.get_contents("")
            star_count = repo.stargazers_count
            break
        except Exception as e:
            cnt += 1
            if cnt > 3:
                print(f"Error: {e}")
                return False
            time.sleep(5)
            continue
    
    source_file_extensions = [
        '.py', '.js', '.ts', '.cpp', '.c', '.java', '.rb', 
        '.go', '.php', '.html', '.css', '.swift', '.kt', 
        '.rs', '.cu', 
        # 模拟器
        '.hpp', '.h'
    ]
    
    contains_readme = False
    contains_source = False
    star_satify = star_count >= least_star

    for file in contents:
        if file.type == 'file':
            if any(file.path.endswith(ext) for ext in source_file_extensions):
                contains_source = True
            if 'readme' in file.path.lower():
                contains_readme = True

    return all((contains_source, contains_readme, star_satify))


def search_github(keywords: list, pages):
    cnt = 0
    if isinstance(keywords, str):
        keywords = [keywords]

    repos = []
    repos_set = set()
    for keyword in keywords:
        meta_json = []
        repositories = g.search_repositories(query=keyword,sort='stars',order='desc')
        print(f'Totle repo: {repositories.totalCount}')
        for repo in repositories:
            rate_limit = g.get_rate_limit().core
            if rate_limit.remaining == 0:
                wait_time = rate_limit.reset.timestamp() - time.time()
                print(f"Rate limit exceeded, sleeping for {wait_time} seconds")
                time.sleep(wait_time+1)
            repo_name = repo.full_name
            if repo_name in repos_set:
                continue
            else:
                repos_set.add(repo_name)
            # if not check_readme(repo):
            #     continue
            meta_data = {
                'repo_name' : repo.full_name,
                'repo_desc' : repo.description,
                'star': repo.stargazers_count,
            }
            repos.append(repo)
            cnt += 1
            meta_json.append(meta_data)
            print(f'{cnt}:  {repo.full_name}')
        save_json(meta_json, f'./1105_test/{keyword}.json')
        time.sleep(10)
    print(f'Total {cnt} valid repos!')
    return repos

@retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)))
def search_db(db, query):
    bm25_retriever = BM25Retriever.from_documents(db.docstore._dict.values())
    faiss_retriever = db.as_retriever()
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.6, 0.4]
    )
    similar_repo = ensemble_retriever.invoke(query)
    return similar_repo

if __name__ == '__main__':
    search_github('diff-gaussian', 2)
    