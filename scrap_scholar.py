import argparse
import signal
import sys
from collections import deque
import json
from lxml import html
import requests
from fake_useragent import UserAgent

import pandas as pd
import itertools as it

import re
import time
import random


LANG = 'fr' # Language
AS_SDT = '0,5' # Unknown
ITEMS_PER_PAGE = 10
BASE_URL = 'https://scholar.google.fr/scholar?'

# Fetched results
values = []
query = ""

# Used to drop outdated proxies
class ModifiableCycle(object):
    def __init__(self, items=()):
        self.deque = deque(items)

    def __iter__(self):
        return self

    def __next__(self):
        if not self.deque:
            raise StopIteration
        item = self.deque.popleft()
        self.deque.append(item)
        return item

    next = __next__

    def delete_previous(self):
        # Deletes the item just returned.
        self.deque.pop()


def signal_handler(sig, frame):
    global values

    write_values_to_html()
    sys.exit(0)


def get_proxy_pool(path='Proxy List.txt'):
    # Either manually fetched from https://www.proxy-list.download/HTTPS
    try:
        proxies = pd.read_csv(path, header = None)
        proxies = proxies.values.tolist()
        proxies = list(it.chain.from_iterable(proxies))
    except Exception:
        # Or automatically from
        proxies = requests.get("https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt").text.split('\n')
    
    #proxy_pool = it.cycle(proxies)
    proxy_pool = ModifiableCycle(proxies)

    return proxy_pool


def get_urls(query, nItems, yearlow):
    url = BASE_URL + f'hl={LANG}&as_sdt={AS_SDT}&q={query}'

    if yearlow:
        url += f'&ylo={yearlow}'
        
    urls = []
    for i in range(0, nItems, ITEMS_PER_PAGE):
        start = '' if i == 0 else f'&start={i}'
        urls.append(url + start)

    return urls


def parse_from_page(page):
    # Transform it into a html tree
    tree = html.fromstring(page.content) 

    items = tree.xpath('//div[@class="gs_r gs_or gs_scl"]')

    results = []

    for item in items:
        value = dict()

        # This can be just a citation
        try:
            value['title'] = item.xpath('.//h3[@class="gs_rt"]/a')[0].text_content()
        except IndexError:
            value['title'] = item.xpath('.//h3[@class="gs_rt"]')[0].getchildren()[1].text_content()
            
        try:
            value['link'] = item.xpath('.//h3[@class="gs_rt"]/a')[0].get('href')
        except IndexError:
            value['link'] = '#'

        try:
            value['citations'] = [int(re.sub('[^0-9]+', '', i.text_content().replace('\xa0', ''))) for i in item.xpath('.//div[@class="gs_fl"]/a') if 'Cité' in i.text_content()][0]
        except IndexError:
            value['citations'] = 0

        try:
            value['document'] = item.xpath('.//div[@class="gs_or_ggsm"]/a')[0].get('href')
        except IndexError:
            value['document'] = '#'

        try:
            value['date'] = int(item.xpath('.//div[@class="gs_a"]')[0].text_content().split(',')[-1].split('-')[0].strip())
        except ValueError:
            value['date'] = '?' 

        results.append(value)

    return results


def write_values_to_html(path='scraping_results.html'):
    global values
    global query

    output = """
    <!DOCTYPE html>
    <html>
    <head>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.3.1/css/bootstrap.min.css" integrity="sha384-ggOyR0iXCbMQv3Xipma34MD+dH/1fQ784/j6cY/iJTQUOhcWr7x9JvoRxT2MZw1T" crossorigin="anonymous">
    <style>
    table {
    font-family: arial, sans-serif;
    border-collapse: collapse;
    width: 100%;
    }

    td, th {
    border: 1px solid #dddddd;
    text-align: left;
    padding: 8px;
    }

    tr:nth-child(even) {
    background-color: #dddddd;
    }
    </style>
    </head>
    <body>

    <div class="container" style="max-width:none;">
    <h2>Results for: """+ query + """</h2>

    <table id="paperTable" style="width:100vw;table-layout:fixed">
    <thead>
    <tr class="d-flex">
        <th scope="col">#</th>
        <th scope="col" class="col">Titre</th>
        <th scope="col" class="col-1">Date <a href="#" onclick="sortTable(1)">&uarr; &darr;</a> </th>
        <th scope="col" class="col-1">Citations <a href="#" onclick="sortTable(2)">&uarr; &darr;</a></th>
        <th scope="col" class="col-2">Document</th>
    </tr>
	</thead>
    <tbody>
    """

    for (i, v) in enumerate(sorted(values, key = lambda x: -x['citations']), start=1):
        output += f"""
        <tr class="d-flex">
            <th scope="row"><b>{i}</b></th>
            <td class="col"><a href="{v['link']}">{v['title']}</a></th>
            <td class="col-1">{v['date']}</th>
            <td class="col-1">{v['citations']}</th>
            <td class="col-2"><a class="d-block text-truncate" href="{v['document']}">{v['document']}</a></th>
        </tr>
        """
        
    output += """
    </tbody>
    </table>
    </div>

    <script>
    function sortTable(n) {
        var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
        table = document.getElementById("paperTable");
        switching = true;
        dir = "asc";
        while (switching) {
            switching = false;
            rows = table.rows;
            for (i = 1; i < (rows.length - 1); i++) {
                shouldSwitch = false;
                x = Number(rows[i].getElementsByTagName("TD")[n].innerHTML.toLowerCase().trim()) || 0;
                y = Number(rows[i + 1].getElementsByTagName("TD")[n].innerHTML.toLowerCase().trim()) || 0;
                if (dir == "asc") {
                    if (x < y) {
                        shouldSwitch = true;
                        break;
                    }
                } else if (dir == "desc") {
                    if (x > y) {
                        shouldSwitch = true;
                        break;
                    }
                }
            }

            if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
                switchcount ++;
            } else {
                console.log("Table was sorted in ascending order")
                if (switchcount == 0 && dir == "asc") {
                    dir = "desc";
                    switching = true;
                }
            }
        }
    }
    </script>

    </body>
    </html>
    """

    with open(path, 'w', encoding="utf-8") as file:
        file.write(output)

    # Save a JSON copy as well
    with open(path.split('.')[0]+'.json', 'w') as fp:
        json.dump(values, fp)


def main():
    global values
    global query

    # Define SIGINT handler
    signal.signal(signal.SIGINT, signal_handler)

    parser = argparse.ArgumentParser()

    parser.add_argument('query', help='Main argument. Use quotes to input several words.')
    parser.add_argument('-y', '--yearlow', help='Lower year bound. None equals no year bound')
    parser.add_argument('-o', '--output', help='Output name.', default='scraping_results.html')
    parser.add_argument('-n', '--number', help='Number of items to fetch. Defaults to 1000.', type=int, default=1000)

    args = parser.parse_args()

    query = args.query

    print('Press CTRL + C anytime to interrupt and save current results.')

    urls = get_urls(query, args.number, args.yearlow)
    proxy_pool = get_proxy_pool()

    # Fake UserAgent
    ua = UserAgent()

    start_len = len(urls)

    # Making sure every url will be fetched
    while len(urls) > 0:
        for url in urls:
            # Pick one proxy in the pool
            proxy = next(proxy_pool)
            
            print(f'Status : {start_len-len(urls)}/{start_len}', end='\r')
            
            try:
                # Fetch page
                page = requests.get(url, proxies={"http": proxy, "https": proxy}, headers={'User-Agent': ua.random}, timeout=5)
                # High sleep for more sneak
                time.sleep(random.randrange(1, 5))
                
                # Add new results to existing ones
                values = values + parse_from_page(page)
                
                # Remove this url if it was successfull
                urls.remove(url)
            except requests.exceptions.ConnectTimeout as e:
                # Connection timed out
                pass
            except requests.exceptions.ProxyError as e:
                # Connection closed by the host
                proxy_pool.delete_previous()
                pass
            except requests.exceptions.ConnectionError as e:
                print('ConnectionError:', e)
                pass
            except Exception as e:
                print(type(e), str(e))
                pass

    # Save the items in a readable format, by descending order
    write_values_to_html(args.output)

    print('\nDone!')

if __name__ == '__main__':
    main()