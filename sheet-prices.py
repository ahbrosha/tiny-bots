#!/usr/bin/env python3

from urllib.error import HTTPError
from bs4 import BeautifulSoup
from apiclient import discovery, errors
from google.oauth2 import service_account

import argparse
import random
import requests
import time
import logging
import os


CARD_QUERY_URL = 'https://www.trader-online.de/index.php'

GOOGLE_SPREADSHEET_ID = '1s893t4SIaeWgk9XVvMwFKK6fkHctaRUcxLf4PZxfrQo'
GOOGLE_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
ALL_RARITIES = {
    'Common':      'Common',
    'Rare':        'Rare',
    'Secret Rare': 'Secret_Rare',
    'Starfoil':    'Starfoil',
    'Super Rare':  'Super_Rare',
    'Ultra Rare':  'Ultra_Rare'
}

parser = argparse.ArgumentParser()
parser.add_argument(
    '-s', '--secret-file', type=str, default='token.json',
    help='Path to the ')


def get_card_details(serial, rarity):
    payload = {
        'lang': '1',
        'lang': '1',
        'cl': 'alist',
        'searchparam': serial,
        'cnid': '13cb6f197d462358e248528973af6665',
        f'attrfilter[Rarity][{ALL_RARITIES[rarity]}]': '1',
        'fnc': 'executefilter'
    }
    response = requests.get(CARD_QUERY_URL, params=payload)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    product_boxes = soup.find_all(class_='product-box')
    if len(product_boxes) < 1:
        logging.warning(f'No product found for serial number: {serial}')
        return
    product_box = product_boxes[0]
    details = {
        'card_name': product_box.find(class_='title'),
        'rarity': product_box.find_all(class_='listattribut_left'),
        'price_pre': product_box.find(class_='price-pre'),
        'price_decimal': product_box.find(class_='price-decimal')
    }
    for k, v in details.items():
        if v is None or len(v) < 1:
            logging.warning(f'No {k} found for serial number: {serial}')
            return
    details['card_name'] = details['card_name'].span.string.strip()
    details['rarity'] = details['rarity'][1].text.replace('Rarity: ', '').strip()
    details['price_pre'] = details['price_pre'].string.strip()
    details['price_decimal'] = details['price_decimal'].string.replace(',', '').strip()
    details['price'] = int(details['price_pre']) + int(details['price_decimal']) / 100
    return details

if __name__ == '__main__':
    args = parser.parse_args()
    #details = get_card_details('BP01-DE003', 'Super Rare')
    #print(details)

    creds = None
    if os.path.exists('token.json'):
        creds = service_account.Credentials.from_service_account_file('token.json', scopes=GOOGLE_SCOPES)

    try:
        service = discovery.build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        sheet = service.spreadsheets()
        result = sheet.values().get(spreadsheetId=GOOGLE_SPREADSHEET_ID, range='Tabellenblatt1!A1:D5').execute()
        values = result.get('values', [])

        if not values:
            print('No data found.')

        print('Name, Major:')
        for row in values:
            # Print columns A and E, which correspond to indices 0 and 4.
            print('%s, %s' % (row[0], row[1]))
    except errors.HttpError as err:
        print(err)

