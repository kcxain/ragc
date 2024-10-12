import os
import subprocess
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from search import search_github
from langchain_community.vectorstores import FAISS
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from search import make_request
from github import Github
import time
gh_token = os.getenv('GH_TOKEN')
g = Github(gh_token)

lock = threading.Lock()
load_dotenv()

headers = {
            'Authorization': f'token {gh_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0'
        }
embeddings = OpenAIEmbeddings()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=150,
    chunk_overlap=30,
    length_function=len,
    is_separator_regex=False,
)

def download_process(repo, db: FAISS):
    rate_limit = g.get_rate_limit().core
    if rate_limit.remaining == 0:
        wait_time = rate_limit.reset.timestamp() - time.time()
        print(f"Rate limit exceeded, sleeping for {wait_time} seconds")
        time.sleep(wait_time+1)
    try:
        readme_content = repo.get_readme().decoded_content.decode("utf-8")
    except Exception as e:
        print(f"Error fetching README: {e}")
    if readme_content:
        docu = Document(
            page_content=readme_content,
            metadata={
                'repo_name' : repo.full_name,
                'repo_desc' : repo.description,
                'star': repo.stargazers_count,
            }
        )
        split_docu = text_splitter.split_documents([docu])
        with lock:
            db.add_documents(split_docu)
            

def load_readme(repos, db: FAISS):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_process, repo, db): repo for repo in repos}
        
        for future in as_completed(futures):
            repo = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"{repo.full_name} download error: {e}")

def clone_github_repo(repo_name, destination=None):
    repo_url = f"https://github.com/{repo_name}.git"
    
    if destination is None:
        destination = repo_name.split('/')[-1]
    
    try:
        result = subprocess.run(["git", "clone", repo_url, destination], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Clone: {repo_name} to {destination}")
    except subprocess.CalledProcessError as e:
        print(f"Clone error: {e.stderr.decode()}")

if __name__ == '__main__':
    vector_store = FAISS(
                    embedding_function=embeddings,
                    index=faiss.IndexFlatL2(len(embeddings.embed_query("hello world"))),
                    docstore=InMemoryDocstore(),
                    index_to_docstore_id={},
                )
    repos = search_github('gaussian-splatting', 100)
    load_readme(repos, vector_store)
    vector_store.save_local("faiss_index")
    print(vector_store.similarity_search("3D Gaussian Splatting with C kernel", k=1))