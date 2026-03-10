import os
import tqdm
from bs4 import BeautifulSoup as bs
import urllib.request
import urllib.parse
import json
from datetime import datetime
import pytz

def get_papers_by_date(field_abbr, start_date, end_date=None, max_results=200):
    start_str = start_date.strftime('%Y%m%d%H%M%S')
    if end_date:
        end_str = end_date.strftime('%Y%m%d235959')
        query = f"(cat:cs.RO)+AND+lastUpdatedDate:[{start_str}+TO+{end_str}]"
    else:
        now_str = datetime.now(tz=pytz.timezone("America/New_York")).strftime('%Y%m%d235959')
        query = f"(cat:cs.RO)+AND+lastUpdatedDate:[{start_str}+TO+{now_str}]"
    
    url = f"http://export.arxiv.org/api/query?search_query={query}&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    page = urllib.request.urlopen(url)
    soup = bs(page, features="xml")
    
    entries = soup.find_all("entry")
    new_paper_list = []
    for entry in entries:
        paper = {}
        paper['main_page'] = entry.id.text
        paper['pdf'] = paper['main_page'].replace("abs", "pdf")
        paper['title'] = entry.title.text.replace("\n", " ").strip()
        
        authors = [a.find("name").text for a in entry.find_all("author")]
        paper['authors'] = ", ".join(authors)
        
        subjects = [c.get("term") for c in entry.find_all("category", recursive=False)]
        paper['subjects'] = "; ".join(subjects)
        
        paper['abstract'] = entry.summary.text.replace("\n", " ").strip()
        new_paper_list.append(paper)
        
    if not os.path.exists("./data"):
        os.makedirs("./data")
        
    date_str = datetime.now(tz=pytz.timezone("America/New_York")).strftime("%a, %d %b %y")
    filename = f"./data/{field_abbr}_{date_str}_local.jsonl"
    with open(filename, "w", encoding="utf-8") as f:
        for paper in new_paper_list:
            f.write(json.dumps(paper, ensure_ascii=False) + "\n")
            
    return new_paper_list


def _download_new_papers(field_abbr):
    NEW_SUB_URL = f'https://arxiv.org/list/{field_abbr}/new'  # https://arxiv.org/list/cs/new
    page = urllib.request.urlopen(NEW_SUB_URL)
    soup = bs(page)
    content = soup.body.find("div", {'id': 'content'})

    # find the first h3 element in content
    h3 = content.find("h3").text   # e.g: New submissions for Wed, 10 May 23
    date = h3.replace("New submissions for", "").strip()

    dt_list = content.dl.find_all("dt")
    dd_list = content.dl.find_all("dd")
    arxiv_base = "https://arxiv.org/abs/"

    assert len(dt_list) == len(dd_list)
    new_paper_list = []
    for i in tqdm.tqdm(range(len(dt_list))):
        paper = {}
        paper_number = dt_list[i].text.strip().split(" ")[2].split(":")[-1]
        paper['main_page'] = arxiv_base + paper_number
        paper['pdf'] = arxiv_base.replace('abs', 'pdf') + paper_number

        paper['title'] = dd_list[i].find("div", {"class": "list-title mathjax"}).text.replace("Title: ", "").strip()
        paper['authors'] = dd_list[i].find("div", {"class": "list-authors"}).text \
                            .replace("Authors:\n", "").replace("\n", "").strip()
        paper['subjects'] = dd_list[i].find("div", {"class": "list-subjects"}).text.replace("Subjects: ", "").strip()
        paper['abstract'] = dd_list[i].find("p", {"class": "mathjax"}).text.replace("\n", " ").strip()
        new_paper_list.append(paper)


    #  check if ./data exist, if not, create it
    if not os.path.exists("./data"):
        os.makedirs("./data")

    # save new_paper_list to a jsonl file, with each line as the element of a dictionary
    date_val = datetime.now(tz=pytz.timezone("America/New_York")).date()
    date_str = date_val.strftime("%a, %d %b %y")
    with open(f"./data/{field_abbr}_{date_str}.jsonl", "w") as f:
        for paper in new_paper_list:
            f.write(json.dumps(paper) + "\n")


def get_papers(field_abbr, limit=None):
    date_val = datetime.now(tz=pytz.timezone("America/New_York")).date()
    date_str = date_val.strftime("%a, %d %b %y")
    if not os.path.exists(f"./data/{field_abbr}_{date_str}.jsonl"):
        _download_new_papers(field_abbr)
    results = []
    with open(f"./data/{field_abbr}_{date_str}.jsonl", "r") as f:
        for i, line in enumerate(f.readlines()):
            if limit and i == limit:
                return results
            results.append(json.loads(line))
    return results
