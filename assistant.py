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
load_dotenv()

openai_key = os.getenv('OPENAI_API_KEY')

embeddings = OpenAIEmbeddings()
llm = ChatOpenAI(
        api_key=openai_key,
        model='gpt-3.5-turbo-0125',
        max_tokens='32'
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
        repos = search_github(keywords, 100)
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
    similar_repo = vector_store.similarity_search(code_description, k=1)
    print(f"Best matching repository: {similar_repo}")

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
    
if __name__ == '__main__':
    user_input = "Gaussian Splatting with C kernel"
    run(user_input)