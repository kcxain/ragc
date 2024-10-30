from autogen import (
    AssistantAgent,
    UserProxyAgent,
)

user_proxy = UserProxyAgent(
    name="User",
    system_message="A human admin. Give the task.",
    code_execution_config=False,
    human_input_mode="NEVER",
    description="""Never select me as a speaker.
    """,
)
import os
from dotenv import load_dotenv
load_dotenv()

config_list = [
    {"model": "gpt-4-1106-preview", "api_key": os.environ["OPENAI_API_KEY"]},
    {"model": "gpt-3.5-turbo", "api_key": os.environ["OPENAI_API_KEY"]},
]

reviewer = AssistantAgent(
    name="Reviewer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""You are a Reviewer. You should review the top 5 related repos provided by `Writer` and select the one that best matches the user's algorithm requirements. 
    If any repo matches the task, return the repository name, analyse why it matches the requirements, and output `TERMINATE` to signal the completion of the task.
    If none of the repos matches the task, analyse why, ouput `WRITER REWRITE` and transfer to `Writer` to generate a more accurate README text.
    """,
    # description="""Reviewer. Can review the top related repos provided by Writer and select the one that best matches the user's algorithm requirements. 
    # If any repo matches the task, return the repository name and output `TERMINATE` to signal the completion of the task.
    # If none of the repos matches the task, ouput `None` and transfer to `Writer` to generate a more accurate README text.
    # """,
    description="""I am **ONLY** allowed to speak **immediately** after `Writer`.
    """,
)

searcher = AssistantAgent(
    name="Searcher",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""You are a Searcher. You need to understand the algorithm requirements provided by the user, interpreting the task code needed, 
    and determining the requirements for the code (such as the programming language, whether it can run on CPU/GPU, etc.). 
    Then you should generate 2 or 3 keywords to search the related repos from GitHub.
    """,
    # description="""Searcher. Can generate 2 or 3 keywords to search the related repos from GitHub, download the readme of them into a vector database and return the path of database.
    # """,
    description="""I am **ONLY** allowed to speak **immediately** after `User`.
    """,
)

writer = AssistantAgent(
    name="Writer",
    llm_config={"config_list": config_list, "cache_seed": None},
    system_message="""You are a Writer. Your task is to generate a README text that aligns as closely as possible with the user's specified algorithm requirements and search the top related repos. 
    The README must highlight and prioritize the user's specific needs, such as programming language, hardware compatibility (CPU/GPU), performance optimization, and any other explicit details provided in the algorithm description.
    And then, you should search the top related repos from the vector database and transfer to `Reviewer` to select the best one.
    If `Reviewer` thinks none of the repos is related to user's requirements, you should generate a new README text and search the repos again.
    """,
    # description="""Writer. Can generate a README text that aligns as closely as possible with the user's specified algorithm requirements and search the top 5 related repos from the vector database.
    # If `Reviewer` thinks none of the repos matches user's requirements, can generate a new README text and search the repos again.
    # """,
    description="""I am **ONLY** allowed to speak **immediately** after `Searcher` or `Reviewer`. If `Reviewer` says `WRITER REWRITE`, the next speaker must be `Writer`.
    """,
)