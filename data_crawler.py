import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import streamlit as st

BASE_URL = "https://www.airlinequality.com/airline-reviews/british-airways/page/"

def scrape_data(max_pages=40, checkpoint_date=None):
    all_reviews = []
    found_stop_point = False
    progress_bar = st.progress(0)
    status_text = st.empty()
    headers = {"User-Agent": "Mozilla/5.0"}

    for page in range(1, max_pages + 1):
        if found_stop_point: break
        status_text.text(f" Đang quét trang {page}...")
        url = f"{BASE_URL}{page}/?sortby=post_date%3ADesc&pagesize=100"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article", {"itemprop": "review"})
            if not articles: break

            for item in articles:
                date_tag = item.find("time", {"itemprop": "datePublished"})
                if not date_tag: continue
                
                date_str = date_tag["datetime"]
                current_date = pd.to_datetime(date_str)

                if checkpoint_date and current_date <= pd.to_datetime(checkpoint_date):
                    found_stop_point = True
                    break

                review_dict = {
                    "Date": date_str,
                    "Overall_Rating": item.find("span", {"itemprop": "ratingValue"}).text if item.find("span", {"itemprop": "ratingValue"}) else None,
                    "Header": item.find("h2", {"class": "text_header"}).text.strip() if item.find("h2", {"class": "text_header"}) else None,
                    "Review_Body": item.find("div", {"class": "text_content"}).text.strip() if item.find("div", {"class": "text_content"}) else None
                }
                
                review_stats = item.find("table", {"class": "review-ratings"})
                if review_stats:
                    for row in review_stats.find_all("tr"):
                        header_node = row.find("td", {"class": "review-rating-header"})
                        if header_node:
                            key = header_node.text.strip()
                            value_cell = row.find("td", {"class": "review-value"})
                            stars_cell = row.find("td", {"class": "review-rating-stars"})
                            if value_cell:
                                review_dict[key] = value_cell.text.strip()
                            elif stars_cell:
                                review_dict[key] = len(stars_cell.find_all("span", {"class": "star fill"}))
                
                all_reviews.append(review_dict)

            progress_bar.progress(page / max_pages if not found_stop_point else 1.0)
            time.sleep(2)
        except Exception as e:
            st.error(f"Lỗi tại trang {page}: {e}")
            break
            
    return pd.DataFrame(all_reviews)