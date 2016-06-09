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

from config import API_BASE_URL
import stackexchange


@responses.activate
def test_sites():
    responses.add(
        responses.GET,
        API_BASE_URL + "sites?pagesize=10000&filter=!SmNnbu6IrvLP5nC(hk",
        json={"items": [{
            "site_state": "normal",
            "site_url": "http://test.test",
            "api_site_parameter": "test",
            "name": "TEST STACK",
            "site_type": "main_site"
        }]},
        status=200, content_type='application/json')

    scraper = stackexchange.Scraper()
    res = scraper.sites
    assert "test" in res
    assert res["name"] == "TEST STACK"
