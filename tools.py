from typing import List, Annotated
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_community.docstore.document import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.docstore import InMemoryDocstore
from search import search_github
from download import load_readme, clone_github_repo
from assistant import check_local
import faiss

embeddings = OpenAIEmbeddings()

def download_readme_to_db(keywords: List[str]) -> Annotated[str, "path of vector database"]:
    keywords = [keyword.lower().strip() for keyword in keywords]
    db_path = check_local(keywords)
    vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    if not db_path:
        repos = search_github(keywords, 1)
        vector_store = FAISS(
                        embedding_function=embeddings,
                        index=faiss.IndexFlatL2(len(embeddings.embed_query("hello world"))),
                        docstore=InMemoryDocstore(),
                        index_to_docstore_id={},
                    )
        load_readme(repos, vector_store)
        db_file_name = '-'.join(keywords).lower()
        db_path = f'./db/{db_file_name}'
        vector_store.save_local(db_path)
    return db_path

def search_db(db_path: str, text: str) -> List[str]:
    vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    bm25_retriever = BM25Retriever.from_documents(vector_store.docstore._dict.values())
    faiss_retriever = vector_store.as_retriever()
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.8, 0.2]
    )
    similar_repos = ensemble_retriever.invoke(text)
    return [{"repo_name": repo.metadata["repo_name"], "repo_readme": repo.page_content} for repo in similar_repos]