#!/usr/bin/env python3

import email
import imaplib
import json
import os
import re
import time

from selenium import webdriver

SMTP_SERVER = 'posteo.de'
USERNAME = 'ahbrosha@posteo.de'
PASSWORD = 'ixc1R3QAhF3Rp3HLP43t94tna5U5dBdB'

UNSUBSCRIBE_REGEX = re.compile(r'List-Unsubscribe:\s+<(?P<link>\S+)>')
USER_AGENT_STRING = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'  # noqa

CACHE_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'links.json')


def get_unsubcribe_links():
    links = []
    mail = imaplib.IMAP4_SSL(SMTP_SERVER)
    mail.login(USERNAME, PASSWORD)
    mail.select('Chickenwings')
    _status, messages = mail.search(None, 'ALL')
    email_ids = messages[0].split()
    for mail_id in email_ids:
        _, msg = mail.fetch(mail_id, '(RFC822)')
        for response in msg:
            if not isinstance(response, tuple):
                continue
            regex_matches = UNSUBSCRIBE_REGEX.search(str(response))
            unsubscribe_link = regex_matches.group('link')
            if unsubscribe_link:
                links.append(unsubscribe_link)
    return links


def get_firefox_webdriver():
    profile = webdriver.FirefoxProfile()
    profile.set_preference('general.useragent.override', USER_AGENT_STRING)
    options = webdriver.firefox.options.Options()
    #options.headless = True
    return webdriver.Firefox(firefox_profile=profile, options=options)


if __name__ == '__main__':
    driver = get_firefox_webdriver()
    links = []
    if os.path.exists(CACHE_FILENAME):
        with open(CACHE_FILENAME, 'r') as json_file:
            links = json.load(json_file)
    else:
        links = get_unsubcribe_links()
        with open(CACHE_FILENAME, 'w') as json_file:
            json_file.write(json.dumps(links, indent=4, sort_keys=True))
    for link in links:
        driver.get(link)
