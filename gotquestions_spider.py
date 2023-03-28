import scrapy
import enum

class PageCategory(enum.Enum):
    THEME = 1
    QUESTION = 2
    
class GotQuestionsSpider(scrapy.Spider):
    name = "gotquestions"
    start_urls = ["https://www.gotquestions.org/content.html"]
    
    def identify_page_type(self, response):
        """Identifies the type of page via the label at the top of the page."""
        
        label_div = response.css("div.label.gradient-to-tr::text").get()
        if label_div is None:
            return None

        if "Theme" in label_div:
            return PageCategory.THEME
        if "Question" in label_div:
            return PageCategory.QUESTION
        
    def sanitize_text(self, text):
        """Cleans up the text"""

        # unicode to ascii
        text = text.encode("ascii", "ignore").decode("ascii")
        text = text.strip()
        
        return text

    def parse_question(self, response):
        """Parses a question page and extracts the question and answer."""
    
        question_text = response.css("span[itemprop='name headline'][property='og:title']::text").get()
        # answer css: div[itemprop='articleBody'], skip the first div
        answer_text = response.css("div[itemprop='articleBody']::text").getall()[1]
        answer_text = "".join(answer_text)

        if question_text is None or answer_text is None:
            return None, None
        
        # clean up the question and answer
        question_text = self.sanitize_text(question_text)
        answer_text = self.sanitize_text(answer_text)

        return question_text, answer_text

    def parse(self, response):
        """Parses the page and extracts the sublinks."""
        
        page_category = self.identify_page_type(response)
        
        if page_category == PageCategory.THEME:
            self.log(f"Discovered theme page: {response.url}")
            sublinks = response.css("div.content a::attr(href)").getall()
            for sublink in sublinks:
                if not sublink.startswith("http"):
                    yield response.follow(sublink, callback=self.parse)

        elif page_category == PageCategory.QUESTION:
            self.log(f"Discovered question page: {response.url}")
            question_text, answer_text = self.parse_question(response)

            if question_text is not None and answer_text is not None:
                yield {
                    "question": question_text,
                    "answer": answer_text
                }
                
