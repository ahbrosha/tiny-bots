#!/usr/bin/env python3

import argparse
import random
import re
import time
import os

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium import webdriver
from telegram.error import TelegramError
import telegram.bot


ALTERNATE_URL_5600x = 'https://www.alternate.de/AMD/Ryzen-5-5600X-Prozessor/html/product/1685588'  # noqa
MINDFACTORY_URL_5600x = 'https://www.mindfactory.de/product_info.php/AMD-Ryzen-5-5600X-6x-3-70GHz-So-AM4-BOX_1380726.html'  # noqa
NBB_URL_5600x = 'https://www.notebooksbilliger.de/amd+ryzen+5+5600x+cpu'

USER_AGENT_STRING = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'  # noqa

SCRIPT_DESCRIPTION = '''
Checks if the AMD Ryzen 5600x is in stock on Alternate, Mindfactoy or NBB.

The script adds some random delay to the scan interval.
If the CPU is found, a Telegram notification is send.
'''


parser = argparse.ArgumentParser(description=SCRIPT_DESCRIPTION)
parser.add_argument(
    '-i', '--interval', type=int, default=60,
    help='The default interval to check for in minutes (default: 20)')
parser.add_argument(
    '--min-delay', type=int, default=3,
    help='Number of minutes to delay the interval at minimum (default: 3)')
parser.add_argument(
    '--max-delay', type=int, default=7,
    help='Number of minutes to delay the interval at maximum (default: 7)')

telegram_parser_group = parser.add_argument_group('Telegram settings')
telegram_parser_group.add_argument(
    '-t', '--token', type=str,
    help='Telegram bot token')
telegram_parser_group.add_argument(
    '-c', '--chat-id', type=int,
    help='Telegram chat id')


opi3_parser_group = parser.add_argument_group('Orange Pi 3 settings')
opi3_parser_group.add_argument(
    '--use-opi3-leds',
    action='store_true',
    help='Uses the build-in leds of the Orange Pi 3 for visual feedback')


def check_alternate_stock(driver):
    driver.get(ALTERNATE_URL_5600x)
    try:
        driver.find_element_by_class_name('available_stock')
        return True
    except NoSuchElementException:
        return False


def check_mindfactory_stock(driver):
    driver.get(MINDFACTORY_URL_5600x)
    price = 1_000
    try:
        price_container = driver.find_element_by_class_name('pprice')
        price_matches = re.search(r'nur\s€\s(?P<price>\d+)',
                                  price_container.text)
        price = int(price_matches.group('price'))
    except Exception:
        return False
    if price < 340:
        return True
    return False


def check_nbb_stock(driver):
    driver.get(NBB_URL_5600x)
    if 'sofort ab Lager' in driver.page_source:
        return True
    return False


def get_available_vendor_name(driver):
    if check_alternate_stock(driver):
        return 'Alternate'
    if check_mindfactory_stock(driver):
        return 'Mindfactory'
    if check_nbb_stock(driver):
        return 'NBB'
    return ''


def send_telegram_notification(token, chat_id, message):
    try:
        bot = telegram.bot.Bot(token=token)
        bot.send_message(chat_id=chat_id,
                         text=message)
    except TelegramError as e:
        print(e)


def turn_orange_pi_3_leds_off():
    os.system('echo 0 > /sys/class/leds/orangepi:red:power/brightness')
    os.system('echo 0 > /sys/class/leds/orangepi:green:status/brightness ')


def turn_orange_pi_3_leds_on():
    os.system('echo 1 > /sys/class/leds/orangepi:red:power/brightness')
    os.system('echo 1 > /sys/class/leds/orangepi:green:status/brightness ')


def get_firefox_webdriver():
    profile = webdriver.FirefoxProfile()
    profile.set_preference('general.useragent.override', USER_AGENT_STRING)
    options = webdriver.firefox.options.Options()
    options.headless = True
    return webdriver.Firefox(firefox_profile=profile, options=options)


if __name__ == '__main__':
    args = parser.parse_args()
    telegram_args = [args.token, args.chat_id]

    if any(arg is None for arg in telegram_args):
        parser.error('You must specify a Telegram token and a chat id!')

    driver = get_firefox_webdriver()
    success_message = 'Hooray! Found CPU at {}; time to waste money!'
    while True:
        if args.use_opi3_leds:
            turn_orange_pi_3_leds_on()
        if vendor := get_available_vendor_name(driver):
            send_telegram_notification(args.token,
                                       args.chat_id,
                                       success_message.format(vendor))
            break
        else:
            print('Nah, CPU is out of stock, still need to wait...')

        if args.use_opi3_leds:
            turn_orange_pi_3_leds_off()
        delay = random.randint(args.min_delay, args.max_delay)
        sleep_time = (args.interval + delay) * 60
        time.sleep(sleep_time)

    if args.use_opi3_leds:
        turn_orange_pi_3_leds_off()
