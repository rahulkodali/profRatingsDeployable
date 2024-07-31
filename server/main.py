from flask import Flask, request, jsonify
from flask_cors import CORS
import asyncio
from playwright.async_api import async_playwright
import google.generativeai as genai
import os
import config
import logging
import nest_asyncio

nest_asyncio.apply()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})  # Enable CORS for all routes

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levellevel)s - %(message)s')

os.environ['GRPC_VERBOSITY'] = 'ERROR'
os.environ['GRPC_TRACE'] = ''
api_key = os.getenv(API_KEY)
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')

async def urlBuilder(name):
    logging.debug(f"Started urlBuilder for professor: {name}")
    try:
        curr = f"https://www.ratemyprofessors.com/search/professors/1255?q={name}"
        logging.debug(f"Navigating to URL: {curr}")
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 800, "height": 3200})
            await page.goto(curr, timeout=80000)  # Increased timeout
            logging.debug(f"Page loaded: {curr}")
            
            try:
                await page.wait_for_selector(".dLJIlx", timeout=20000)  # Increased timeout
                logging.debug("Selector .dLJIlx found")
            except Exception as e:
                logging.error(f"Error in urlBuilder (waiting for selector): {e}")
                await browser.close()
                return "timeout"

            profNames = await page.query_selector_all(".dLJIlx")
            if profNames:
                logging.debug(f"Found {len(profNames)} professor(s) on the page")
                for profs in profNames:
                    await page.wait_for_selector(".cJdVEK")
                    snippet = await profs.query_selector(".cJdVEK")
                    text = await snippet.text_content()
                    if text.lower() == name.lower():
                        href = await profs.get_attribute('href')
                        await browser.close()
                        href = "https://www.ratemyprofessors.com" + href
                        logging.debug(f"Found professor URL: {href}")
                        return href

                await browser.close()
                logging.debug("Professor not found on the page")
                return "timeout"
            else:
                await browser.close()
                logging.debug("No professors found on the page")
                return "timeout"
    except Exception as e:
        logging.error(f"Exception in urlBuilder: {e}")
        return "timeout"

async def close_overlays(page):
    logging.debug("Checking for overlays to close")
    try:
        overlays = await page.query_selector_all('.ReactModal__Overlay, .CCPAModal__CCPAPromptBody-sc-10x9kq-1')
        for overlay in overlays:
            if overlay:
                close_button = await overlay.query_selector('button, .close-button')
                if close_button:
                    await close_button.click()
                    logging.debug("Closed an overlay")
        await page.wait_for_timeout(1000)  # Wait a moment for overlays to close
    except Exception as e:
        logging.error(f"Error closing overlays: {e}")

async def scrape_reviews(url):
    logging.debug(f"Started scrape_reviews for URL: {url}")
    try:
        if url == "timeout":
            return "timeout"
        revs = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 800, "height": 3200})
            await page.goto(url, timeout=60000)  # Increased timeout
            logging.debug(f"Page loaded: {url}")

            await close_overlays(page)  # Close any overlay modals

            while True:
                try:
                    await page.wait_for_selector(".glImpo", timeout=10000)
                    more = await page.query_selector(".glImpo")
                    if more is None:
                        logging.debug("No 'more' button found")
                        break
                    logging.debug("Found 'more' button")
                    await more.scroll_into_view_if_needed()
                    await more.hover()
                    await page.wait_for_timeout(500)  # Small wait before clicking
                    await more.click()
                    logging.debug("Clicked 'more' button to load additional reviews")
                    await page.wait_for_timeout(750)  # Wait for reviews to load
                except Exception as e:
                    logging.error(f"Error in scrape_reviews (more button): {e}")
                    break

            try:
                await page.wait_for_selector('.jcIQzP', timeout=10000)
                comments = await page.query_selector_all('.jcIQzP')
                logging.debug(f"Found {len(comments)} reviews on the page")
                for comms in comments:
                    await page.wait_for_selector(".gRjWel", timeout=2500)
                    snippet = await comms.query_selector(".gRjWel")
                    text = await snippet.text_content()
                    revs.append(text)
            except Exception as e:
                logging.error(f"Error in scrape_reviews (comments): {e}")

            await browser.close()
            logging.debug(f"Scraped reviews: {revs}")
            return revs
    except Exception as e:
        logging.error(f"Exception in scrape_reviews: {e}")
        return []

def run_async_task(coroutine):
    logging.debug(f"Running async task: {coroutine}")
    try:
        loop = asyncio.get_event_loop()
        logging.debug("Event loop obtained")
        if loop.is_running():
            logging.debug("Event loop is already running")
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
            result = future.result()
        else:
            logging.debug("Starting new event loop")
            result = asyncio.run(coroutine)
        logging.debug(f"Async task result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error running async task: {e}")
        raise

@app.route('/api/reviews', methods=['POST'])
def get_reviews():
    try:
        logging.debug("Received /api/reviews request")
        data = request.json
        name = data['name']
        logging.debug(f"Received professor name: {name}")
        url = run_async_task(urlBuilder(name))
        logging.debug(f"URL from urlBuilder: {url}")
        if url == "timeout":
            logging.debug("URL builder timed out")
            return jsonify({"reviews": [], "error": "timeout"})
        reviews = run_async_task(scrape_reviews(url))
        logging.debug(f"Reviews from scrape_reviews: {reviews}")
        return jsonify({"reviews": reviews})
    except Exception as e:
        logging.error(f"Error in /api/reviews: {e}")
        return jsonify({"error": str(e)}), 500

import re

import re

@app.route('/api/summary', methods=['POST'])
def get_summary():
    try:
        logging.debug("Received /api/summary request")
        data = request.json
        reviews = data['reviews']
        logging.debug(f"Received reviews: {reviews}")
        if reviews == "timeout":
            logging.debug("Scrape reviews timed out")
            return jsonify({"summary": "This professor does not exist at this university."})

        prompt = "I am a college student looking for a good professor - based on the reviews given give me all the necessary details/pros and cons as well as a rating out of 10. Also only include these categories: rating, pros, cons, specific feedback, recommendations, overall summary, and, if the rating is less than or equal to 5, an alternative professor - if the rating is higher put not needed for the alternative professor category"
        for rev in reviews:
            prompt += "\n" + rev

        response = model.generate_content(prompt)
        summary_text = response.text
        logging.debug(f"Generated summary: {summary_text}")

        # Split the summary text into sections
        sections = {
            "Overall Rating": "N/A",
            "Pros": [],
            "Cons": [],
            "Specific Feedback": [],
            "Recommendations": [],
            "Overall Summary": "",
            "Alternative Professor": ""
        }

        current_section = None
        for line in summary_text.split('\n'):
            line = line.strip()
            if line.startswith("**Rating:**"):
                sections["Overall Rating"] = " " + line.split("**Rating:**")[1].strip()
            elif line.startswith("**Pros:**"):
                current_section = "Pros"
            elif line.startswith("**Cons:**"):
                current_section = "Cons"
            elif line.startswith("**Specific Feedback:**"):
                current_section = "Specific Feedback"
            elif line.startswith("**Recommendations:**"):
                current_section = "Recommendations"
            elif line.startswith("**Overall Summary:**"):
                current_section = "Overall Summary"
                sections[current_section] += line.split("**Overall Summary:**")[1].strip()
            elif line.startswith("**Alternative Professor:**"):
                current_section = "Alternative Professor"
                sections[current_section] += line.split("**Alternative Professor:**")[1].strip()
            elif current_section:
                if current_section in ["Overall Summary", "Alternative Professor"]:
                    sections[current_section] += " " + line
                else:
                    sections[current_section].append(line)

        # Clean up any leading and trailing asterisks from Pros, Cons, etc.
        for key in ["Pros", "Cons", "Specific Feedback", "Recommendations"]:
            cleaned_list = []
            for item in sections[key]:
                # Remove leading and trailing asterisks and extra spaces using regex
                cleaned_item = re.sub(r'^\*+\s*|\s*\*+$', '', item).strip()
                # Remove asterisks within the content
                cleaned_item = cleaned_item.replace('**', '')
                cleaned_list.append(cleaned_item)
            sections[key] = cleaned_list

        return jsonify(sections)

    except Exception as e:
        logging.error(f"Error in /api/summary: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    logging.debug("Starting Flask app")
    app.run(debug=True, port=5001)


if __name__ == '__main__':
    logging.debug("Starting Flask app")
    app.run(debug=True, port=5001)
