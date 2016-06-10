#!/usr/bin/env python3

# -------------------------------------------------------------------------
# Name:     test_stackexchange.py
#
# Author:   Radomirs Cirskis
#
# Created:  2016-10-06
# Licence:  WTFPL
# -------------------------------------------------------------------------

import responses
import re
import os
import json
from datetime import date, datetime
from urllib.parse import parse_qsl, urlparse

import stackexchange
from config import API_BASE_URL, API_VERSION


def request_callback(request):
    """
    Simulates Stackexchange API server
    """
    url = urlparse(request.url)
    verb = url.path.replace("/%s/" % API_VERSION, '')
    query = dict(parse_qsl(url.query))

    print("****", verb)
    print("****", query)
    headers = {
        'X-Request-ID': '728d329e-0e86-11e4-a748-0c84dc037c13',
        'Content-Type': 'application/json'}

    if verb == "sites":
        body_json = {"items": [
            {
                "headers": "normal",
                "site_url": "http://TEST_TEST_TEST.stackexchange.com",
                "api_site_parameter": "test",
                "name": "TEST STACK",
                "site_type": "main_site"
            },
            {
                "headers": "normal",
                "site_url": "http://tor.stackexchange.com",
                "api_site_parameter": "tor",
                "name": "Tor",
                "site_type": "main_site"
            },
            {
                "headers": "normal",
                "site_url": "http://law.stackexchange.com",
                "api_site_parameter": "law",
                "name": "Law",
                "site_type": "main_site"
            }
        ]}
        return (200, headers, json.dumps(body_json))
    elif verb == "questions":

        site = query["site"]
        body = {"items": [
            {
                "answers": [{"body_markdown": "ANSWER #%d: %s" % (idx, site)}],
                "is_answered": True,
                "creation_date": 1111 * idx,
                "question_id": 11111 * idx,
                "body_markdown": "QUESTION #%d: %s" % (idx, site),
                "link": "http://%s.stackexchange.com/question%d" % (site, idx),
                "title": "Question #%d (%s)" % (idx, site)
            }
            for idx in range(1, 10)] + [{
                "is_answered": False,
                "creation_date": 3333333,
                "question_id": 33333333,
                "body_markdown": "QUESTION #3333: %s NO 'answers'" % site,
                "link": "http://%s.stackexchange.com/question3333" % site,
                "title": "Question #3333 (%s)" % site
            }]}
        return (200, headers, json.dumps(body))
    else:
        return (404, headers, '{error: "Wrong Request"}')


def test_to_epoch():
    assert stackexchange.to_epoch(datetime.utcfromtimestamp(55555)) == 55555
    assert stackexchange.to_epoch(date(1970, 1, 1)) == 0
    assert stackexchange.to_epoch(55555) == 55555


@responses.activate
def test_sites():

    responses.add_callback(
        responses.GET,
        url=re.compile(API_BASE_URL + "sites\\?pagesize=10000&filter=.*"),
        callback=request_callback)

    scraper = stackexchange.Scraper()
    res = scraper.sites
    assert "test" in res
    assert res["test"]["name"] == "TEST STACK"


@responses.activate
def test_questions():

    responses.add_callback(
        responses.GET,
        url=re.compile(API_BASE_URL + "questions\\?filter=.*"
                       "&order=desc&sort=creation&site=.*"),
        callback=request_callback)

    scraper = stackexchange.Scraper()
    res = list(scraper.questions(site="TEST_TEST_TEST"))
    assert len(responses.calls) == 1
    assert len(res) == 10
    assert "TEST_TEST_TEST" in res[0]["title"]


@responses.activate
def test_process_site():

    responses.add_callback(
        responses.GET,
        url=re.compile(API_BASE_URL + ".*"),
        callback=request_callback)

    scraper = stackexchange.Scraper()
    scraper.process_site(site="TEST_TEST_TEST")
    assert len(responses.calls) == 2


@responses.activate
def test_process_xls():

    responses.add_callback(
        responses.GET,
        url=re.compile(API_BASE_URL + ".*"),
        callback=request_callback,
        content_type='application/json')

    scraper = stackexchange.Scraper()
    scraper.process_xls(file_name=os.path.join(
        "tests", "stackexchange_forums.xlsx"))
    assert len(responses.calls) == 3
