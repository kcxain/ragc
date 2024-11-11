from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from tenacity import (
    retry,
    retry_if_exception_type,
    wait_random_exponential,
)  # for exponential backoff
import openai
from search import search_github, search_db
from download import load_vector_db
from dotenv import load_dotenv

import json
import os
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
    keywords = [keyword.lower().strip() for keyword in keywords]
    print(keywords)

    # 2. 判断有无缓存
    db_path = check_local(keywords)
    if db_path:
        vector_store = FAISS.load_local(db_path, embeddings, allow_dangerous_deserialization=True)
    else:
    # 3. 返回仓库列表
        repos = search_github(keywords, 1)
        if len(repos) == 0:
            return None
    # 4. 下载所有仓库readme到数据库
        vector_store = load_vector_db(repos)
        db_file_name = '-'.join(keywords).lower()
        vector_store.save_local(f'./db/{db_file_name}')
    # 5. 检索最相似的仓库
    query_readme = get_query_text(code_description)
    similar_repo = search_db(vector_store, query_readme)
    # print(similar_repo)

    # 6. 组合起来
    prompt = '\n\n'.join([f'repo_name_{i}: {repo.metadata["repo_name"]}, repo_readme{i}: {repo.page_content}' for i, repo in enumerate(similar_repo)])
    # print(f"Best matching repository: {similar_repo}")
    result = similar_repo[0].metadata["repo_name"]
    try: 
        result = review_query_text(code_description, prompt)
    except:
        pass
    return {
        'result': result,
        'top5': [repo.metadata["repo_name"] for repo in similar_repo],
        'keywords': keywords,
        'text': query_readme
    }
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

@retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)))
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
        5. To minimize the search results, avoid using overly broad terms, such as 'cpp' or 'algorithm' or 'rnn'.

        Please return the keywords as a comma-separated list without any additional commentary.
        """
    )
    prompt = prompt_template.format(function_description=function_description)
    return llm.invoke(prompt).content

@retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)))
def get_query_text(function_description):
    prompt_template = PromptTemplate(
        input_variables=["function_description"],
        template="""
        You are an AI assistant tasked with generating text for searching README from a vector database.

        User Requirement:
        {function_description}

        Your task is to generate a README text that aligns as closely as possible with the user's specified algorithm requirements and search the top related repos.
        The README must highlight and prioritize the user's specific needs, such as programming language, hardware compatibility (CPU/GPU), performance optimization, and any other explicit details provided in the algorithm description.
        You should focus on writing the function description and feature sections of the README with about 100 words, and avoid writing other content.
        Please return the text only.
        """
    )
    prompt = prompt_template.format(function_description=function_description)
    return llm.invoke(prompt).content

@retry(wait=wait_random_exponential(min=1, max=60), retry=retry_if_exception_type((openai.RateLimitError, openai.APIConnectionError)))
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
    

def eval_papers_with_code():
    with open('./papers_cleaned.json', 'r') as f:
        inputs = json.load(f)
    with open('./papers_cleaned_results.json', 'a') as f: 
        for input in inputs[16:]:
            code_description = f"""
            Provide the most relevant GitHub repository about the following title and abstract: {input['abstract']}
            """
            result = run(code_description)
            f.write(json.dumps({
                'title': input['title'],
                'result': result
            }) + '\n')
            f.flush()

if __name__ == '__main__':
    code_description = f"""
    Your task is to search a NPU simulator in github. There are some requirements:
    1. support cycle-level simulation.
    2. the main language is C++ or Python.
    3. The NPU should contains memory module, like a DRAM simulation part.
    4. The hardware should be configurable, by giving configuration files, such as .cfg/.yaml type files.
    5. The input file is about operations to be simulated. For example, describing the DNN topology/Instructions/Operation series.
    """
    result = run(code_description)
    with open('result.json', 'w') as f:
        f.write(json.dumps(result))