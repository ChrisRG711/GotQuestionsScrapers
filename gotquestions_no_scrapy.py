import os
import requests
from bs4 import BeautifulSoup
import json
import concurrent.futures
import logging
from enum import Enum
from tqdm import tqdm
import argparse
import threading

class PageClassification(Enum):
    THEME = 1
    QUESTION = 2

question_links = set()
theme_links = set()

lock = threading.Lock()

questions_answers = {}
previous_queue = []
url_queue = []

def identify_page_type(soup):
    label_div = soup.find("div", {"class": "label gradient-to-tr"})
    if label_div is None:
        return None

    if label_div.text == "Theme":
        return PageClassification.THEME
    if label_div.text == "Question":
        return PageClassification.QUESTION

def extract_sublinks(soup):
    main_content = soup.find("div", {"class": "content"})
    if main_content is None:
        return None

    link_elements = main_content.find_all("a")
    if link_elements is None:
        return None

    return ["https://www.gotquestions.org/" + link["href"] for link in link_elements if not link["href"].startswith("http")]

def crawl_page(url):
    try:
        page_response = requests.get(url, proxies=PROXY)
        page_response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"Failed to crawl page {url}: {e}")
        
        if page_response.status_code == 429:
            # rate limited, try again
            return [url]
        return

    parsed_html = BeautifulSoup(page_response.text, "html.parser")
    page_classification = identify_page_type(parsed_html)

    if page_classification == PageClassification.THEME:
        logging.debug(f"Discovered theme page: {url}")
        if url not in theme_links:
            theme_links.add(url)

            sublinks = extract_sublinks(parsed_html)
            if sublinks is None:
                return

            found_links = []
            for sublink in sublinks:
                if sublink not in theme_links and sublink not in question_links:
                    
                    found_links.append(sublink)
                
            return found_links
    
    elif page_classification == PageClassification.QUESTION:
        logging.debug(f"Discovered question page: {url}")
        if url not in question_links:
            question_links.add(url)
            
            # fetch question and answer
            question_text, answer_text = parse_question(parsed_html)
            
            if question_text is None or answer_text is None:
                return 
        
            with lock:
                questions_answers[url] = (question_text, answer_text)

def parse_question(soup):
    question_element = soup.find("span", {"itemprop": "name headline", "property": "og:title"})
    answer_element = soup.find("div", {"itemprop": "articleBody"})

    if question_element is None or answer_element is None:
        return None, None

    question_text = question_element.text
    answer_text = answer_element.text

    # cleanup
    question_text = question_text.strip()
    answer_text = answer_text.replace("Answer", "").strip()

    return question_text, answer_text

def write_questions():
    with open("questions.json", "w") as f:
        json.dump(questions_answers, f)
    
def load_questions():
    with open("questions.json", "r") as f:
        questions_answers.update(json.load(f))

def write_checkpoint():
    logging.info(f"Checkpoint: {len(questions_answers)} questions found")
    checkpoint = {
        "question_count": len(questions_answers),
        "question_links": list(question_links),
        "theme_links": list(theme_links),
        "url_queue": list(previous_queue)
    }
    
    with open("checkpoint.json", "w") as f:
        json.dump(checkpoint, f)
        
def load_checkpoint():
    with open("checkpoint.json", "r") as f:
        checkpoint = json.load(f)
        
    question_links.update(checkpoint["question_links"])
    theme_links.update(checkpoint["theme_links"])
    url_queue.extend(checkpoint["url_queue"])
    
    logging.info(f"Loaded checkpoint: {checkpoint['question_count']} questions found")


def main(args):
    # attempt to load checkpoint
    try:
        load_checkpoint()
        logging.info("Loaded checkpoint")
        load_questions()
        logging.info("Loaded questions")
    except FileNotFoundError:
        pass



    i = 0
    url_queue = ["https://www.gotquestions.org/content.html"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        while len(url_queue) > 0:
            logging.debug(f"Crawling {len(url_queue)} pages")
            futures = [executor.submit(crawl_page, link) for link in url_queue]
            previous_queue = url_queue.copy()
            url_queue = []
        
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Crawling pages", leave=False):
                new_links = future.result()
                if new_links is not None:
                    url_queue.extend(new_links)
                
                i += 1
                
                if i % args.checkpoint == 0:
                    with lock:
                        logging.info(f"Checkpoint: {i} pages crawled, {len(questions_answers)} questions found")
                        write_checkpoint()
                        write_questions()

    logging.info("Finished crawling pages")

    write_questions()

    # remove checkpoint
    os.remove("checkpoint.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawl gotquestions.org")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("-t", "--threads", type=int, default=50, help="Number of threads to use for crawling pages. >10 introduces rate limiting")
    parser.add_argument("-c", "--checkpoint", type=int, default=100, help="Checkpoint interval in pages")
    args = parser.parse_args()

    log_level = logging.INFO if not args.debug else logging.DEBUG
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # hide requests logging
    logging.getLogger("urllib3").setLevel(logging.WARNING)


    main(args)