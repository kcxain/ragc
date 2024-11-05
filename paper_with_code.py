import requests
from bs4 import BeautifulSoup
import json
import time
import os
from github import Github
from search import check_readme
from dotenv import load_dotenv
load_dotenv()
gh_token = os.getenv('GH_TOKEN')
g = Github(gh_token)

paper_code = './links-between-papers-and-code.json'
paper_abstract = './papers-with-abstracts.json'
data_path = './papers.json'

def construct_data(paper_code, paper_abstract):
    paper_dict = {}
    with open(paper_abstract, 'r') as f:
        papers = json.load(f)
    for paper in papers:
        paper_dict[paper['arxiv_id']] = {
            'title': paper['title'],
            'proceeding': paper['proceeding'],
            'paper_url': paper['url_abs'],
            'repo_info': {},
            'abstract': paper['abstract']
        }
    with open(paper_code, 'r') as f:
        papers = json.load(f)
    for paper in papers:
        paper_key = paper['paper_arxiv_id']
        if paper_key not in paper_dict:
            continue
        paper_dict[paper_key]['repo_info'] = {
            'github_url': paper['repo_url'],
            "mentioned_in_paper": paper['mentioned_in_paper'],
            "mentioned_in_github": paper['mentioned_in_github'],
            'is_official': paper['is_official']
        }
    paper_info = []
    for key in paper_dict:
        if paper_dict[key]['repo_info'] != {}:
            paper_info.append(paper_dict[key])
    with open('papers.json', 'w') as f:
        json.dump(paper_info, f, indent=4)
    
def check_data(data_path):
    with open(data_path, 'r') as f:
        papers = json.load(f)
    papers_cleaned = []
    for paper in papers:
        if len(papers_cleaned) == 50:
            break
        repo_url = paper['repo_info']['github_url']
        if 'github' not in repo_url:
            continue
        repo_name = '/'.join(repo_url.split('/')[-2:])
        try:
            repo = g.get_repo(repo_name)
            _, __ = check_readme(repo, least_star=50)
            if _:
                print(repo_name)
                papers_cleaned.append(paper)
        except:
            continue
    with open('papers_cleaned.json', 'w') as f:
        json.dump(papers_cleaned, f, indent=4)

if __name__ == "__main__":
    check_data(data_path)