import os
import requests
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv
from search import search_github
from langchain_community.vectorstores import FAISS
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from search import make_request
lock = threading.Lock()

load_dotenv()
openai_key = os.getenv('OPENAI_API_KEY')
deepseek_key = os.getenv('DEEPSEEK_API_KEY')
gh_token = os.getenv('GH_TOKEN')

headers = {
            'Authorization': f'token {gh_token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Mozilla/5.0'
        }
embeddings = OpenAIEmbeddings()

def download_process(repo, db: FAISS):
    repo_name = repo['repo_name']
    readme_name = repo['readme_name']
    print(repo_name)
    print(readme_name)
    url = f'https://api.github.com/repos/{repo_name}/contents/{readme_name}'
    response = make_request(url)
    if response.status_code == 200:
        content = response.json().get('content', None)
        if content:
            decoded_content = base64.b64decode(content).decode('utf-8')
            with lock:
                print(decoded_content)
                db.add_texts([decoded_content], [repo])
            

def load_readme(repos, db: FAISS):
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(download_process, repo, db): repo for repo in repos}
        
        for future in as_completed(futures):
            repo = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"{repo['repo_name']} download error: {e}")

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