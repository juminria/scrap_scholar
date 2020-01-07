# scrap_scholar
Google Scholar scraper.

This tool uses automatically updated proxies in order to bypass Scholar's robots.txt.


## Requirements
- [Python](https://www.python.org/downloads/)
- Set Google Scholar's "Results per page" parameter to 10.


## Installation
1. ``git clone https://github.com/juminria/scrap_scholar``
2. ``cd scrap_scholar``
3. ``pip install -r requirements.txt``


## Usage
Simply run :
``python scrap_scholar "[your query]"``

By default, it fetches the first 1000 papers without date constraints.

Optional arguments are as follow:
- ``-y``/``--yearlow`` : Sets earliest date.
- ``-o``/``--output`` : Name given to output files.
- ``-n``/``--number`` : Number of papers to fetch. Must be a multiple of 10.


## DISCLAIMER

This tool does not respect Google Scholar terms of usage and should therefore be used carefully.
We do not take responbilities for the anything you do with the software.
