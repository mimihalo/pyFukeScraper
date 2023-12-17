import urllib.request
import sys
import json
import csv
import re
import glob
import os
import requests
import io

from fractions import Fraction
from datetime import datetime
from bs4 import BeautifulSoup
from google.cloud import bigquery
from selenium import webdriver
from selenium.webdriver.common.by import By

DEBUG = True
ROOT_URL = 'https://www.post.japanpost.jp/kitte_hagaki/stamp/fuke/'
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "bq_key.json"

def fetch(url):
    HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)',
           'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja-JP;q=0.6,ja;q=0.5',
            }
    print("fetching url: " + url)
    req = urllib.request.Request(url=url, headers=HEADERS)
    content = urllib.request.urlopen(req).read()
    return content

def fetch_sel(url):
    # Initialize a new browser
    driver = webdriver.Chrome()
    driver.implicitly_wait(1)
    driver.get(url)

    # Get button and click it
    while True:
        try:
            python_button = driver.find_element(By.PARTIAL_LINK_TEXT, "さらに表示する")
            python_button.click()
        except:
            break

    return driver.page_source

def get_and_parse_root_content(url):
    item_list = []
    content = fetch(url)
    soup = BeautifulSoup(content, "html5lib")
    res = soup.find("div", class_="listObject")
    hrefs = res.find_all("a")
    for node in hrefs:
        tmp_item = {
            'text': node.get_text(),
            'url': url + node['href']
        }
        item_list.append(tmp_item)
    return item_list

def fetch_ken_content(url):
    content = fetch_sel(url)
    soup = BeautifulSoup(content, "html5lib")
    posts = soup.find_all("div", class_="post")
    posts_list = []

    for post in posts:
        name = post.find("dd", class_="title").get_text()
        ken = post.find("li", class_="pre").get_text()
        try:
            post.find("dd", class_="abolition").get_text()
            abolition = True
        except:
            abolition = False
        url_span = post.find("span", class_="link")
        url = url_span.find("a")['href']
        tmp_item = {
            'name': name,
            'ken': ken,
            'abolited': abolition,
            'url': ROOT_URL + url
        }
        posts_list.append(tmp_item)
    return posts_list

def get_start_date_from_node(input_node):
    for node in input_node.find_all("dl"):
        if node.find("dt").get_text() == "使用開始日":
            return node.find("dd").get_text().replace("年", "-").replace("月", "-").replace("日", "")
    return None

def get_abolited_date_from_node(input_node):
    for node in input_node.find_all("dl"):
        if node.find("dt").get_text() == "廃止年月日":
            return node.find("dd").get_text().replace("年", "-").replace("月", "-").replace("日", "")
    return None

def get_post_address_from_node(input_node):
    regex = re.compile(r'〒[0-9]{3}-[0-9]{4}')
    item = {
        'post_code': '',
        'address': ''
    }

    for node in input_node.find_all("dl"):
        if node.find("dt").get_text() == "開設場所":
            address = node.find("dd").get_text()
            post_code = regex.search(address)group(0)
            address = address.replace(post_code, '')
            item = {
                'post_code': post_code,
                'address': address
            }
            return item
    return item

def get_detail_content(url):
    content = fetch(url)
    soup = BeautifulSoup(content, "html5lib")
    res = soup.find_all("div", class_="stampdata")
    
    address_item = get_post_address_from_node(res[1])
    item = {
        'start_date': get_start_date_from_node(res[0]),
        'abolited_date': get_abolited_date_from_node(res[0]),
        'post_code': address_item['post_code'],
        'address': address_item['address']
    }
        
    return item

def main():
    global DEBUG
    global ROOT_URL
    ken_items = get_and_parse_root_content(ROOT_URL)
    results = []
    
    for item in ken_items:
        ken_results = fetch_ken_content(item['url'])
        for post_item in ken_results:
            detail = get_detail_content(post_item['url'])
            tmp_item = {
                'name': post_item['name'],
                'ken': post_item['ken'],
                'start_date': detail['start_date'],
                'abolited': post_item['abolited'],
                'abolited_date': detail['abolited_date'],
                'post_code': detail['post_code'],
                'address': detail['address'],
                'url': post_item['url']
            }
            results.append(tmp_item)
    
    # write to csv
    with open('output.csv', 'w', newline='', encoding='UTF-8') as csvfile:
        fieldnames = ['name', 'ken', 'start_date', 'abolited_date', 'abolited', 'post_code', 'address', 'url']
        writer = csv.writer(csvfile)
        writer.writerow(fieldnames)
        for item in results:
            row = [item['name'], item['ken'], item['start_date'], item['abolited_date'], item['abolited'], item['post_code'], item['address'], item['url']]
            writer.writerow(row)

    # write to json
    with open('output.json', 'w', encoding='UTF-8') as outfile:
        json.dump(results, outfile, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()