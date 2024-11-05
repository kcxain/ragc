import requests
from bs4 import BeautifulSoup
import json
import time

class PapersWithCodeScraper:
    def __init__(self, max_papers=10000):
        self.base_url = "https://paperswithcode.com"
        self.headers = {"User-Agent": "Mozilla/5.0"}
        self.max_papers = max_papers
        self.papers = []

    def fetch_paper_list(self, page):
        """获取指定页面的论文列表"""
        url = f"{self.base_url}/latest?page={page}"
        response = requests.get(url, headers=self.headers, timeout=10)
        if response.status_code == 200:
            return response.text
        return None

    def parse_paper_list(self, html_content):
        """解析页面中的论文列表并筛选出带有代码的论文"""
        soup = BeautifulSoup(html_content, "html.parser")
        papers = []
        
        for item in soup.select(".infinite-item"):
            title_element = item.select_one(".item-title a")
            code_link = item.select_one(".badge-primary[href*='github.com']")

            if title_element and code_link:
                paper = {
                    "title": title_element.text.strip(),
                    "paper_url": self.base_url + title_element['href'],
                    "github_url": code_link['href']
                }
                papers.append(paper)

        return papers

    def fetch_abstract(self, paper_url):
        """访问论文详情页面并提取摘要信息"""
        try:
            response = requests.get(paper_url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                abstract = soup.select_one(".paper-abstract")
                return abstract.text.strip() if abstract else "No abstract available"
        except requests.exceptions.RequestException as e:
            print(f"Failed to fetch abstract from {paper_url}: {e}")
        return "No abstract available"

    def scrape(self):
        """循环爬取论文直到达到目标数量"""
        page = 1
        while len(self.papers) < self.max_papers:
            print(f"Fetching page {page}...")
            html_content = self.fetch_paper_list(page)
            if html_content:
                new_papers = self.parse_paper_list(html_content)
                
                for paper in new_papers:
                    if len(self.papers) >= self.max_papers:
                        break
                    # 获取论文的摘要信息
                    paper['abstract'] = self.fetch_abstract(paper["paper_url"])
                    self.papers.append(paper)
                    print(f"Collected {len(self.papers)} papers")

            if not new_papers:
                print("No more papers found.")
                break

            page += 1
            time.sleep(1)  # 添加延迟以防止请求过于频繁

        self.papers = self.papers[:self.max_papers]

    def save_to_jsonl(self, filename="papers_with_code.jsonl"):
        """将结果保存到 JSON Lines 文件中"""
        with open(filename, "w") as f:
            for paper in self.papers:
                json.dump({
                    "title": paper["title"],
                    "abstract": paper["abstract"],
                    "github_url": paper["github_url"]
                }, f)
                f.write("\n")

paper_code = './links-between-papers-and-code.json'
paper_abstract = './papers-with-abstracts.json'


def main():
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
    


if __name__ == "__main__":
    with open('papers.json', 'r') as f:
        papers = json.load(f)
        print(len(papers))