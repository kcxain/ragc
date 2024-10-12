import requests
import os
import time
from dotenv import load_dotenv
load_dotenv()
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from github import Github
gh_token = os.getenv('GH_TOKEN')

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


def check_readme(repo_name):
    contents_url = f'https://api.github.com/repos/{repo_name}/contents'
    response = make_request(contents_url)
    
    if response.status_code != 200:
        return False, None

    files = response.json()
    
    source_file_extensions = [
        '.py', '.js', '.ts', '.cpp', '.c', '.java', '.rb', 
        '.go', '.php', '.html', '.css', '.swift', '.kt', 
        '.rs', '.cu'
    ]
    
    readme_path = None
    contains_source_file = False

    for file in files:
        if file['type'] == 'file':
            if any(file['name'].endswith(ext) for ext in source_file_extensions):
                contains_source_file = True
            if file['name'].lower().startswith('readme'):
                readme_path = file['name']

    if contains_source_file and readme_path:
        return True, readme_path
    return False, None


def search_github(keywords: list, pages):
    cnt = 0
    if isinstance(keywords, str):
        keywords = [keywords]
        
    url = 'https://api.github.com/search/repositories'
    repos = []
    repos_set = set()
    for keyword in keywords:
        for i in range(1, pages+1):
            params = {
                'q': f'{keyword}',
                'sort': 'updated',
                'order': 'desc',
                'page': i
            }
            response = make_request(url, params=params)
            data = response.json()
            if 'items' not in data:
                break
            if not data['items']:
                break
            for repo in data['items']:
                repo_name = repo['full_name']
                if repo_name in repos_set:
                    continue
                else:
                    repos_set.add(repo_name)

                contains_source, readme_path = check_readme(repo_name)
                if not contains_source:
                    continue
                meta_data = {
                    'repo_name' : repo['full_name'],
                    'repo_desc' : repo['description'],
                    'readme_name': readme_path,
                    'star': repo['stargazers_count'],
                }
                repos.append(meta_data)
                cnt += 1
                print(f'{cnt}:  {meta_data}')
        time.sleep(10)
    print(f'\nTotal {cnt} repos!\n')
    return repos
            

if __name__ == '__main__':
    search_github('diff-gaussian', 2)
    