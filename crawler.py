from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from time import sleep
from Database.controller import db
import Database
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from bs4 import BeautifulSoup
from datetime import datetime
import sys
import json
import os

executor = ThreadPoolExecutor(10)
"""
FOR LINUX, FIREFOX:
    -download geckodriver
    -place in bin (preferably /usr/local/bin)
FOR WINDOWS, FIREFOX:
    - add geckodriver executable to PATH
"""


class Scraper:
    def __init__(self):
        """Login/authentication attributes"""
        self.username = db["username"]
        self.password = db["password"]
        self.submit_button = "/html/body/div/div/div/div[1]/form/div[3]/div/button"

        """Initalizing driver"""
        self.driver = webdriver.Firefox()

        if not self.get_login():
            print("Error logging in. Trying again in 30 seconds...")
            sleep(30)

    def get_login(self):
        """Handles login function. Returns boolean based on if login was sucessful"""
        self.driver.get("https://learn.sait.ca")
        if "Login" not in self.driver.title:
            return True

        # adding in username and password
        self.driver.find_element("id", "username").send_keys(self.username)
        self.driver.find_element("id", "password").send_keys(self.password)
        # finding submit button, clicking
        self.driver.find_element("xpath", self.submit_button).click()

        if "Homepage" in self.driver.title:
            return True
        else:
            return False

    def get_assignment_data(self, class_id):
        self.driver.get(
            f"https://learn.sait.ca/d2l/lms/dropbox/user/folders_list.d2l?ou={class_id}")
        page_source = self.driver.page_source

        soup = BeautifulSoup(page_source, 'html.parser')

        table = soup.find("table").find("tbody")
        assignments = {}
        for row in table:
            # eliminate table titles
            try:
                if 'd_ggl2' in row.get('class'):
                    continue
                elif 'd_gh' in row.get('class'):
                    continue
            except TypeError as e:
                pass

            ## find name ##
            # look if there are attachments, then drill down ass name
            if row.find('table'):
                ass_name = row.find('a').text
            else:
                ass_name = row.find_all('div', class_="dco_c")[0].text

            ## assignment closed? (T/F) ##
            # check if there is a "Closed" marked under the assignment name
            if row.find_all('div', class_="dco_c")[2].text:
                ass_closed = True
            else:
                ass_closed = False

            ## PERSONAL: completion status ##
            if row.find_all('td')[0].text.startswith('Not'):
                ass_completed = False
            else:
                ass_completed = True

            ## determine if it is a group project ##
            if row.find_all('span', class_="di_s"):
                group_ass = True
            else:
                group_ass = False
            ## feedback (read? unread?) ##
            if row.find_all('td', class_="d_gc")[2].text.endswith("Read"):
                ass_feedback = "Read"
            elif row.find_all('td', class_="d_gc")[2].text.endswith("Unread"):
                ass_feedback = "Unread"
            else:
                ass_feedback = None

            ## due date ##
            # if there is a due date discovered, convert it to epoch time
            ass_due = row.find_all('td', class_="d_gc")[3].text
            # if it is not a blank space
            if len(ass_due) > 1:
                ass_due = datetime.strptime(
                    ass_due, "%b %d, %Y %I:%M %p").timestamp()
            else:
                ass_due = None

            ass_info = {
                "Name": ass_name,
                "Closed": ass_closed,
                "Group": group_ass,
                "Completed": ass_completed,
                "Feedback": ass_feedback,
                "Due": ass_due
            }
            assignments.update({ass_name: ass_info})

        #db[f"{class_id}_assignments","crawl_data"] = assignments
        return assignments

    def get_test_data(self, class_id):
        self.driver.get(
            f"https://learn.sait.ca/d2l/lms/quizzing/user/quizzes_list.d2l?ou={class_id}")
        page_source = self.driver.page_source

        soup = BeautifulSoup(page_source, 'html.parser')

        table = soup.find("table").find("tbody")

        # it is an empty table, there are no quizzes available.
        # return!
        if len(table) == 1:
            return
        tests = {}

        for row in table:
            # eliminate table titles
            try:
                if 'd_ggl2' in row.get('class'):
                    continue
                elif 'd_gh' in row.get('class'):
                    continue
            except TypeError as e:
                pass

            ## find name ##
            test_name = row.find_all('div', class_="dco")[
                0].text.splitlines()[0]

            ## find date range ##

            # print(row.find_all('span',class_="ds_b")[0].text)

            # if there is a "Due" notice found, we split by "Available" and "Until"
            if 'Due' in row.find_all('span', class_="ds_b")[0].text:
                test_range = row.find_all('span', class_="ds_b")[
                    0].text.split("Available")[1].split("until")
                # do some funky join/splitting to parse out the dates, then convert to a unix timestamp
                test_start = " ".join(test_range[0].split("on")[1].split())
                test_start = datetime.strptime(
                    test_start, "%b %d, %Y %I:%M %p").timestamp()

                test_end = " ".join(test_range[1].split())
                test_end = datetime.strptime(
                    test_end, "%b %d, %Y %I:%M %p").timestamp()
            # if there isn't, we split by "until" only
            else:
                test_range = row.find_all('span', class_="ds_b")[
                    0].text.split("until")

                test_start = " ".join(
                    test_range[0].split("Available on")[1].split())
                test_start = datetime.strptime(
                    test_start, "%b %d, %Y %I:%M %p").timestamp()

                test_end = " ".join(test_range[1].split())
                test_end = datetime.strptime(
                    test_end, "%b %d, %Y %I:%M %p").timestamp()

            ## find max number of attempts ##
            max_attempts = row.find_all('td', class_="d_gn")[1].text
            max_attempts = " ".join(max_attempts.split("/")[1].split())

            test_info = {
                "Name": test_name,
                "Starts": test_start,
                "Ends": test_end,
                "Attempts": max_attempts
            }
            tests.update({test_name: test_info})

        #db[f"{class_id}_tests", "crawl_data"] = tests
        return tests


def main(crawler):
    crawl_dump_file = os.path.join(
        os.path.dirname(__file__), "rawcrawldump.json")
    os.path.join(os.path.dirname(__file__), '', "Collections")

    raw_data = dict({})
    print("Starting crawl")
    for class_id in db["class_id_list"]:
        # pass over "000000" (OTHER)
        if isinstance(class_id, str):
            continue
        # get assignment information
        assignments = crawler.get_assignment_data(class_id)
        if assignments:
            raw_data.update({f"{class_id}_assignments": assignments})

        # get test information
        tests = crawler.get_test_data(class_id)
        if tests:
            raw_data.update({f"{class_id}_tests": tests})

    # dump the file data, if
    if not os.path.isfile(crawl_dump_file):
        with open(crawl_dump_file, 'w') as file:
            json.dump(raw_data, file)
    else:
        print("ISSUE DETECTED - CRAWL DUMP FILE EXISTS BUT IT SHOULDN'T BE THERE!")

    # now return back to home page
    crawler.driver.get("https://learn.sait.ca")


if __name__ == "__main__":
    #crawl_dump_file = sys.argv[1]
    crawler = Scraper()
    print("Crawl succeeded")

    # start up an infinite loop, re-run crawl every 300 seconds (5 min)
    while 1:
        crawler.get_login()
        main(crawler)
        sleep(300)
