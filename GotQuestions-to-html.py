import requests

from bs4 import BeautifulSoup

from urllib.parse import urljoin


def scrape_page(url):
    # Send a GET request to the URL and store the response object

    response = requests.get(url)

    # Parse the HTML content of the response using BeautifulSoup

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the articleBody class on the page and store its contents

    article_body = soup.find('div', {'itemprop': 'articleBody'})

    print(article_body)

    if article_body:
        text_content = article_body.get_text()

        # Define the filename and path for the output file

        filename = url.split('/')[-1] + '.txt'

        path = 'C:/temp/'

        print(filename)

        # Write the text content to the output file

        with open(path + filename, 'w', encoding='utf-8') as f:
            print('writing to text')

            f.write(text_content)


def get_targets_from_url(url, tag, target_set=set()):
    # Send a GET request to the URL and store the response object

    response = requests.get(url)

    # Parse the HTML content of the response using BeautifulSoup

    soup = BeautifulSoup(response.content, 'html.parser')

    # Find all values by tag specified

    if (len(target_set) == 0):

        targets = soup.find_all(tag)

    # Find values by tag and text

    else:

        targets = set()

        for item in target_set:

            target = soup.find(tag, text=item.text)

            if target is not None:
                link_url = target.get('href')

                targets.add(urljoin(base_url, link_url))

    return targets


def primary_crawl(url):
    # Create an empty dictionary to hold key/value pairs of links

    link_dict = {}

    # Call shared function to retrieve all links

    links = get_targets_from_url(url, 'a')

    # Loop through each link and scrape its contents

    for link in links:

        if link.text != 'Questions about GotQuestions.org' and link.text != 'Questions about the Books of the Bible' and (
                link.text.startswith('Questions about') or link.text.startswith('Topical')):
            link_url = link.get('href')

            absolute_url = urljoin(url, link_url)

            link_dict[link.text] = absolute_url

    # Return dictionary

    return link_dict


def second_crawl(link_dict):
    second_level_urls = list(link_dict.values())

    second_level_links = set()

    for url in second_level_urls:
        # Get all h2 tags and remove unwanted first element

        headerLinks = get_targets_from_url(url, 'h2')

        # Get all links based on text from previously retrieved values

        links = get_targets_from_url(url, 'a', headerLinks)

        second_level_links = second_level_links.union(links)

    return second_level_links


def third_crawl(second_level_links):
    third_level_links = set()

    for link in second_level_links:

        response = requests.get(link)

        soup = BeautifulSoup(response.content, 'html.parser')

        div = soup.find('div', {'class': 'content'})

        targets = div.find_all('a')

        for target in targets:

            if len(target.attrs.values()) == 1:
                link_url = target.get('href')

                third_level_links.add(urljoin(base_url, link_url))

    return third_level_links


# Define the starting URL

base_url = 'https://www.gotquestions.org/'

starting_url = 'https://www.gotquestions.org/content.html'

# Start crawling the site

link_dict = primary_crawl(starting_url)

second_level_links = second_crawl(link_dict)

third_level_links = third_crawl(second_level_links)

print('All Links retrieved...starting scrape')

for link in third_level_links:
    scrape_page(link)