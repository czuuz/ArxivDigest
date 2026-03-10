import os
import argparse
import yaml
import openai
from datetime import datetime, timedelta
import sys

from download_new_papers import get_papers_by_date
from relevancy import generate_relevance_score, process_subject_fields
from action import category_map, physics_topics, topics, generate_body

def local_run(config_path, start_date, end_date):
    if not os.path.exists(config_path):
        print(f"Config file not found: {config_path}")
        print("Please copy local_config.yaml.template to local_config.yaml and configure your keys.")
        sys.exit(1)
        
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    api_key = os.environ.get("NEWAPI_API_KEY") or os.environ.get("OPENAI_API_KEY") or config.get("NEWAPI_API_KEY") or config.get("OPENAI_API_KEY")
    if not api_key:
        print("No API Key found. Set NEWAPI_API_KEY in environment or in local_config.yaml")
        sys.exit(1)
    
    openai.api_key = api_key
    
    if config.get("model"):
        os.environ["OPENAI_MODEL_NAME"] = config["model"]

    topic = config.get("topic")
    categories = config.get("categories", [])
    threshold = config.get("threshold", 7)
    interest = config.get("interest", "")
    
    if topic == "Physics":
        raise RuntimeError("You must choose a physics subtopic.")
    elif topic in physics_topics:
        abbr = physics_topics[topic]
    elif topic in topics:
        abbr = topics[topic]
    else:
        raise RuntimeError(f"Invalid topic {topic}")
        
    for category in categories:
        if category not in category_map[topic]:
            raise RuntimeError(f"{category} is not a category of {topic}")

    print(f"Fetching papers from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}...")
    papers = get_papers_by_date(abbr, start_date, end_date, max_results=1000)
    # # Filter by subjects
    # if categories:
    #     papers = [
    #         t for t in papers
    #         if bool(set(process_subject_fields(t["subjects"])) & set(categories))
    #     ]
        
    print(f"Found {len(papers)} matched papers.")
    if interest and papers:
        print("Generating relevancy scores...")
        relevancy_kwargs = {
            "query": {"interest": interest},
            "threshold_score": threshold,
            "num_paper_in_prompt": 16,
        }
        if os.environ.get("OPENAI_MODEL_NAME"):
            relevancy_kwargs["model_name"] = os.environ["OPENAI_MODEL_NAME"]
            
        relevancy, hallucination = generate_relevance_score(
            papers,
            **relevancy_kwargs
        )
        body = "<br><br>".join(
            [
                f'Title: <a href="{paper["main_page"]}">{paper["title"]}</a><br>Authors: {paper["authors"]}<br>Score: {paper.get("Relevancy score", "N/A")}<br>Reason: {paper.get("Reasons for match", "")}'
                for paper in papers
            ]
        )
        if hallucination:
            body = (
                "Warning: the model hallucinated some papers. We have tried to remove them, but the scores may not be accurate.<br><br>"
                + body
            )
    else:
        body = "<br><br>".join(
            [
                f'Title: <a href="{paper["main_page"]}">{paper["title"]}</a><br>Authors: {paper["authors"]}'
                for paper in papers
            ]
        )
        
    with open("local_digest.html", "w", encoding="utf-8") as f:
        f.write("<html><body><h1>Local ArXiv Digest</h1>")
        f.write(f"<p>Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}</p>")
        f.write(body)
        f.write("</body></html>")
    print(f"Successfully generated digest with {len(relevancy if interest else papers)} papers at local_digest.html")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run ArxivDigest locally over a date range.")
    parser.add_argument("--config", default="local_config.yaml", help="Path to local config file")
    parser.add_argument("--start-date", help="Start date (YYYY-MM-DD)", default="(today-7days)")
    parser.add_argument("--end-date", help="End date (YYYY-MM-DD)", default="(today)")
    
    args = parser.parse_args()
    
    end_date = datetime.now() if args.end_date == "(today)" else datetime.strptime(args.end_date, "%Y-%m-%d")
    start_date = end_date - timedelta(days=7) if args.start_date == "(today-7days)" else datetime.strptime(args.start_date, "%Y-%m-%d")
    
    local_run(args.config, start_date, end_date)
