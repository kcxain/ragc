from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from gh_search import GitHubSearcher, RepositoryMatcher, CodeCloner, CodeReader
from dotenv import load_dotenv
import os
load_dotenv()
openai_key = os.getenv('OPENAI_API_KEY')
deepseek_key = os.getenv('DEEPSEEK_API_KEY')
gh_token = os.getenv('GH_TOKEN')

# class CodeGenerator:
#     def __init__(self):
#         self.llm = ChatOpenAI(
#             api_key=deepseek_key, 
#             base_url="https://api.deepseek.com",
#             model='deepseek-chat')

#     def generate_code(self, repo_path, user_input, code_content):
#         if not code_content:
#             print("No suitable code files found in the repository.")

#         code_generation_prompt = """
#         Here is the user's functional requirement: {function_description}.
#         This is the code content cloned from the GitHub repository {repo_path}:
#         {code_content}
#         Please generate the code that meets the user's requirement based on this information.
#         """
#         print(code_content)
#         prompt = code_generation_prompt.format(
#             function_description=user_input,
#             repo_path=repo_path,
#             code_content=code_content
#         )
#         generated_code = self.llm.invoke(prompt).content
#         return generated_code


class Assistant:
    def __init__(self):
        self.llm = ChatOpenAI(
            api_key=deepseek_key, 
            base_url="https://api.deepseek.com",
            model='deepseek-chat',
            max_tokens='32')

    def run(self, code_description):
        print("Generating query keywords...")
        keywords = self.get_query_keywords(code_description)
        print(keywords)
        all_repos = []
        for keyword in keywords.split(','):
            keyword = keyword.strip()
            print(f"Searching for relevant repositories for keyword: {keyword}...")
            searcher = GitHubSearcher(keyword)
            repos = searcher.search_repositories()
            all_repos.extend(repos)

        if not all_repos:
            print("No relevant repositories found.")
            generated_code = generator.generate_code(repo_path, code_description, None)
            
            print("Generated code:")
            print(generated_code)

        print("Matching README files...")
        matcher = RepositoryMatcher(all_repos, code_description)
        matched_repo_name = matcher.match_repository()
        print(f"Best matching repository: {matched_repo_name}")

        repo_url = next(repo['clone_url'] for repo in all_repos if repo['full_name'] == matched_repo_name)
        repo_path = "./cloned_repo"

        print("Cloning the repository...")
        cloner = CodeCloner(repo_url, repo_path)
        cloner.clone()

        print("Reading repository code...")
        reader = CodeReader(repo_path)
        code_content = reader.read_code()

        print("Generating final code...")

        generated_code = generator.generate_code(repo_path, code_description, code_content)

        print("Generated code:")
        print(generated_code)

    def get_query_keywords(self, function_description):
        prompt_template = PromptTemplate(
            input_variables=["function_description"],
            template="""
            You are an AI assistant tasked with generating keywords for searching GitHub repositories.

            User Requirement:
            {function_description}

            Your goal is to produce a concise list of 2 to 3 relevant keywords that can be used to effectively search for repositories on GitHub. The keywords should:
            1. Be relevant to the user's requirement.
            2. Include both technical terms and common phrases related to the functionality described.
            3. Avoid unnecessary words or overly generic terms.
            4. Each keyword covers all user requirements as much as possible

            Please return the keywords as a comma-separated list without any additional commentary.
            """
        )
        prompt = prompt_template.format(function_description=function_description)
        return self.llm.invoke(prompt).content
    
if __name__ == '__main__':
    user_input = "Generate code for algorithm of 3dgs with Cpp"
    assistant = Assistant()
    assistant.run(user_input)