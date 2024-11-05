from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
import os
from langchain_community.vectorstores import FAISS
import faiss
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_openai import OpenAIEmbeddings
from search import search_github
from download import load_readme, clone_github_repo
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
load_dotenv()

openai_key = os.getenv('OPENAI_API_KEY')

embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(
        api_key=openai_key,
        model='gpt-3.5-turbo-0125',
        max_tokens='512'
    )

def run(code_description):
    print("Generating query keywords...")
    # 1. LLM 生成关键词
    keywords = get_query_keywords(code_description).split(',')
    keywords = [keyword.lower().strip() for keyword in keywords][:1]
    print(keywords)

    # 2. 判断有无缓存
    db_path = check_local(keywords)
    if db_path:
        vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    else:
    # 3. 返回仓库列表
        repos = search_github(keywords, 1)
    # 4. 下载所有仓库readme到数据库
        vector_store = FAISS(
                        embedding_function=embeddings,
                        index=faiss.IndexFlatL2(len(embeddings.embed_query("hello world"))),
                        docstore=InMemoryDocstore(),
                        index_to_docstore_id={},
                    )
        load_readme(repos, vector_store)
        db_file_name = '-'.join(keywords).lower()
        vector_store.save_local(f'./db/{db_file_name}')
    # 5. 检索最相似的仓库
    bm25_retriever = BM25Retriever.from_documents(vector_store.docstore._dict.values())
    faiss_retriever = vector_store.as_retriever()
    ensemble_retriever = EnsembleRetriever(
        retrievers=[bm25_retriever, faiss_retriever], weights=[0.8, 0.2]
    )
    similar_repo = ensemble_retriever.invoke(code_description)
    print(similar_repo)

    # 6. 组合起来
    prompt = '\n\n'.join([f'repo_name_{i}: {repo.metadata["repo_name"]}, repo_readme{i}: {repo.page_content}' for i, repo in enumerate(similar_repo)])
    # print(f"Best matching repository: {similar_repo}")
    print(review_query_text(code_description, prompt))
    # 6. 下载到本地
    # repo_name = similar_repo.metadata['repo_name']
    # clone_github_repo(repo_name)

def check_local(keywords):
    folder_path = './db'
    keywords = set(keywords)
    for item in os.listdir(folder_path):
        store_keywords = set(item.split('-'))
        if store_keywords == keywords:
            return os.path.join(folder_path, item)
    return None

def get_query_keywords(function_description):
    prompt_template = PromptTemplate(
        input_variables=["function_description"],
        template="""
        You are an AI assistant tasked with generating keywords for searching GitHub repositories.

        User Requirement:
        {function_description}

        Your goal is to produce a concise list of 2 relevant keywords that can be used to effectively search for repositories on GitHub. The keywords should:
        1. Be relevant to the user's requirement.
        2. Include both technical terms and common phrases related to the functionality described.
        3. Avoid unnecessary words or overly generic terms.
        4. Each keyword covers all user requirements as much as possible
        5. To minimize the search results, avoid using overly broad terms, such as 'cpp' or 'algorithm'

        Please return the keywords as a comma-separated list without any additional commentary.
        """
    )
    prompt = prompt_template.format(function_description=function_description)
    return llm.invoke(prompt).content

def get_query_text(function_description):
    prompt_template = PromptTemplate(
        input_variables=["function_description"],
        template="""
        You are an AI assistant tasked with generating text for searching README from a vector database.

        User Requirement:
        {function_description}

        Your task is to generate a README text that aligns as closely as possible with the user's specified algorithm requirements and search the top related repos. 
        The README must highlight and prioritize the user's specific needs, such as programming language, hardware compatibility (CPU/GPU), performance optimization, and any other explicit details provided in the algorithm description.

        Please return the text only.
        """
    )
    prompt = prompt_template.format(function_description=function_description)
    return llm.invoke(prompt).content

def review_query_text(function_description, repos):
    prompt_template = PromptTemplate(
        input_variables=["function_description"],
        template="""
        You are an AI assistant tasked with reviewing the 5 repo README and selecting the best match for the user's algorithm requirements.

        User Requirement:
        {function_description}

        5 repos with README:
        {repos}

        Please return the name of one repo only with json format.
        """
    )
    prompt = prompt_template.format(function_description=function_description, repos=repos)
    return llm.invoke(prompt, response_format={"type": "json_object"}).content
    
if __name__ == '__main__':
    user_input = "Gaussian Splatting with C kernel on the CPU"
    run(user_input)