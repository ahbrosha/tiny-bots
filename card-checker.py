#!/usr/bin/env python3

import argparse
import random
import requests
import smtplib
import time
import warnings

from email.mime.text import MIMEText
from requests.exceptions import HTTPError

CARD_QUERY_URL = 'https://api.nvidia.partners/edge/product/search'
SCRIPT_DESCRIPTION = '''
Periodically check the availibility of a NVIDIA RTX card and send an email.
Per default only founders edition cards are searched for.

The script adds some random delay to the scan interval (just to please NVIDIA).
Sending emails is optional and only triggered if all parameters are provided.
'''

SUCCESS_MESSAGE = 'Hooray! Card is in stock; time to waste money!'


parser = argparse.ArgumentParser(description=SCRIPT_DESCRIPTION)
parser.add_argument(
    '-c', '--card_name', type=str, default='RTX 3080',
    help='The card name to scan for (default: "RTX 3080")')
parser.add_argument(
    '-i', '--interval', type=int, default=20,
    help='The default interval to check for in minutes (default: 20)')
parser.add_argument(
    '--min-delay', type=int, default=3,
    help='Number of minutes to delay the interval at minimum (default: 3)')
parser.add_argument(
    '--max-delay', type=int, default=7,
    help='Number of minutes to delay the interval at maximum (default: 7)')

email_parser_group = parser.add_argument_group('email settings')
email_parser_group.add_argument(
    '-f', '--from-address', type=str,
    help='Sender email address')
email_parser_group.add_argument(
    '-t', '--to-address', type=str,
    help='Receiver email address')
email_parser_group.add_argument(
    '-s', '--server', type=str,
    help='SMTP server address (must support TLS)')
email_parser_group.add_argument(
    '-u', '--username', type=str,
    help='SMTP server username (usually email address)')
email_parser_group.add_argument(
    '-p', '--password', type=str,
    help='SMTP server password')
email_parser_group.add_argument(
    '--port', type=int, default=465,
    help='SMTP server port (default: 465)')


def get_card_from_api(card_name='RTX 3080'):
    payload = {
        'page': '1',
        'limit': '2',
        'locale': 'de-de',
        'category': 'GPU',
        'gpu': card_name,
        'manufacturer': 'NVIDIA'
    }
    response = requests.get(CARD_QUERY_URL, params=payload)
    response.raise_for_status()
    return response.json()


def card_in_stock(json_response, card_name='RTX 3080'):
    product_json = json_response['searchedProducts']['featuredProduct']

    if not product_json['isFounderEdition']:
        warnings.warn('Found card is not the founders edition!',
                      category=Warning)

    found_card_name = product_json['gpu']
    if found_card_name != card_name:
        warnings.warn(
            f'Found card is a {found_card_name}, not a {card_name}',
            category=Warning)
    return product_json['prdStatus'] != 'out_of_stock'


def send_availability_email(from_address,
                            to_address, server, port, username, password):
    message = MIMEText(SUCCESS_MESSAGE, 'plain')
    message['Subject'] = 'Card available!'
    message['From'] = from_address
    message['To'] = to_address

    with smtplib.SMTP_SSL(server, port, timeout=10) as smtp_connection:
        smtp_connection.set_debuglevel(False)
        smtp_connection.login(username, password)

        smtp_connection.send_message(message, from_address, [to_address])
    print('Email sent.')


if __name__ == '__main__':
    args = parser.parse_args()
    email_args = [args.from_address, args.to_address,
                  args.server, args.username, args.password]

    if not all(arg is None for arg in email_args) \
       and any(arg is None for arg in email_args):
        parser.error('You must either specify all email arguments or none!')

    # If email settings are specified, we are supposed to send an email.
    send_email = any(arg is not None for arg in email_args)

    while True:
        product_json = None
        try:
            product_json = get_card_from_api(args.card_name)
        except HTTPError as e:
            print('Got HTTP error: ', e)

        if card_in_stock(product_json, args.card_name):
            print(SUCCESS_MESSAGE)

            if send_email:
                send_availability_email(args.from_address,
                                        args.to_address,
                                        args.server,
                                        args.port,
                                        args.username,
                                        args.password)
            break
        else:
            print('Nah, card is out of stock, still need to wait...')

        delay = random.randint(args.min_delay, args.max_delay)
        sleep_time = (args.interval + delay) * 60
        time.sleep(sleep_time)
