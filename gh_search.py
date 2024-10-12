import requests
import os
import subprocess
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
import os
load_dotenv()
openai_key = os.getenv('OPENAI_API_KEY')
deepseek_key = os.getenv('DEEPSEEK_API_KEY')
gh_token = os.getenv('GH_TOKEN')

headers = {
            'Authorization': gh_token,
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0'
        }

class GitHubSearcher:
    def __init__(self, keywords, top_n=50):
        self.keywords = keywords
        self.top_n = top_n
        self.repos = []

    def search_repositories(self, total_repos=25):
        repositories = []
        
        page = 1
        per_page = 50
        
        while len(repositories) < total_repos:
            url = 'https://api.github.com/search/repositories'
            params = {
                'q': f'{self.keywords} fork:false',  # 过滤掉 fork 的项目
                'sort': 'best match',
                'order': 'desc',
                'per_page': per_page,
                'page': page
            }
            
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status() 
            data = response.json()
            
            if not data['items']:
                break
            
            for item in data['items']:
                repo_name = item['full_name']
                repo_size_mb = item['size'] / 1024  # 转换为 MB
                if item['stargazers_count'] > 50 and repo_size_mb <= 100:
                    contains_source, readme_path = self.check_readme(repo_name)
                    if contains_source:
                        item['readme_path'] = readme_path
                        repositories.append(item)
                        
                if len(repositories) >= total_repos:
                    break
            
            page += 1

        return repositories
    def check_readme(self, repo_name):
        print(repo_name)
        contents_url = f'https://api.github.com/repos/{repo_name}/contents'
        response = requests.get(contents_url, headers=headers)
        
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
    @staticmethod
    def download_readme(repo_full_name):
        readme_filenames = ['README.md', 'readme.md', 'Readme.md', 'README', 'readme', 'Readme']
        for filename in readme_filenames:
            url = f'https://api.github.com/repos/{repo_full_name}/contents/{filename}'
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                content = response.json().get('content', None)
                if content:
                    return requests.utils.unquote(content)
        return None

class RepositoryMatcher:
    def __init__(self, repos, user_input):
        self.repos = repos
        self.user_input = user_input

    def match_repository(self):
        embeddings = OpenAIEmbeddings()
        texts = []
        repo_names = []

        for repo in self.repos:
            readme = GitHubSearcher.download_readme(repo_full_name=repo['full_name'])
            if readme:
                texts.append(readme)
                repo_names.append(repo['full_name'])

        vector_store = FAISS.from_texts(texts, embeddings)
        docs = vector_store.similarity_search(self.user_input, k=1)
        matched_repo_name = repo_names[texts.index(docs[0].page_content)]
        return matched_repo_name

class CodeCloner:
    def __init__(self, repo_url, local_path):
        self.repo_url = repo_url
        self.local_path = local_path

    def clone(self):
        if not os.path.exists(self.local_path):
            os.makedirs(self.local_path)
        subprocess.run(['git', 'clone', self.repo_url, self.local_path], check=True)
        print(f"Cloned to: {self.local_path}")

class CodeReader:
    def __init__(self, repo_path, extensions=None):
        self.repo_path = repo_path
        self.extensions = extensions or ['.py', '.js', '.cpp', '.cu', '.java', '.c', '.ts', '.rb', '.go']

    def read_code(self):
        code_content = ""
        
        for root, _, files in os.walk(self.repo_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.extensions):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            code_content += f"\n# File: {file_path}\n"
                            code_content += f.read()
                    except Exception as e:
                        print(f"Unable to read file {file_path}: {e}")
        
        return code_content