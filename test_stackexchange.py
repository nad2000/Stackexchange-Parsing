#!/usr/bin/env python3

# -------------------------------------------------------------------------
# Name:     test_stackexchange.py
#
# Author:   Radomirs Cirskis
#
# Created:  2016-10-06
# Licence:  WTFPL
# -------------------------------------------------------------------------

import requests
import responses
import re
from datetime import date, datetime

import stackexchange
from config import API_BASE_URL

def test_to_epoch():
    assert stackexchange.to_epoch(datetime.utcfromtimestamp(55555)) == 55555
    assert stackexchange.to_epoch(date(1970, 1, 1)) == 0
    assert stackexchange.to_epoch(55555) == 55555

@responses.activate
def test_sites():
    ## a workaround to make mocking working
    #stackexchange.config.API_BASE_URL = "http://test.test/" 
    responses.add(
        responses.GET,
        url = re.compile(API_BASE_URL + "sites\\?pagesize=10000&filter=.*"),
        json={"items": [{
            "site_state": "normal",
            "site_url": "http://test.test",
            "api_site_parameter": "test",
            "name": "TEST STACK",
            "site_type": "main_site"
        }]},
        content_type='application/json',
        match_querystring=True)

    scraper = stackexchange.Scraper()
    res = scraper.sites
    assert "test" in res
    assert res["test"]["name"] == "TEST STACK"

