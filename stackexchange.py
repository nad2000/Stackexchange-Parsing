#!/usr/bin/env python3

# -------------------------------------------------------------------------
# Name:     stackexchange.py
#
# Author:   Radomirs Cirskis
#
# Created:  2016-10-06
# Licence:  WTFPL
# -------------------------------------------------------------------------

import requests
from datetime import datetime, date
import os
import json

import config


def to_epoch(timestamp=None):
    """
    Converts datetime or date into Unix Epoch 
    """
    if timestamp is None:
        return None
    if isinstance(timestamp, date):
        return int(datetime.combine(
                    timestamp, 
                    datetime.min.time()).timestamp())
    elif isinstance(timestamp, datetime):
        return int(timestamp.timestamp())
    else:
        return int(timestamp)


def lazy_property(fn):
    """Decorator that makes a property lazy-evaluated.
    """
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property


class Scraper(object):
    """
    Encapsulates Stackexchange scraping
    """

    @lazy_property
    def sites(self):
        """
        Returns a dictionary of all Stackexchange sites
        """
        url = (config.API_BASE_URL + "sites?pagesize=10000&filter="
               "!SmNnbu6IrvLP5nC(hk")
        items = requests.get(url).json().get("items")
        return {item["api_site_parameter"]: item for item in items}

    def get_question(self, question_id):
        """
        Retrieves a question with all answers and comments
        """
        url = (
            config.API_BASE_URL + 
            "%s?order=desc&sort=activity&site=stackoverflow&filter="
            "!)Ehv2Yl*OQfQ*ji0eSXZuEg.YqNfPFiEVg2emRci8aiNY.Xc-"
        ) % question_id
        return requests.get(url).json().get("items")

    def questions(self, *, site="meta", fromdate=None, todate=None):
        """
        Generator for retrieving the questions starting from `fromdate` till `todate`
        `fromdate` and `todate` are either datetime, date, or int (Unix Epoch)
        """
        url = (config.API_BASE_URL + "questions?&filter="
               "!)Ehv2Yl*OhhLOkeHr5)YcUAgEK*(hc7aypu_0Y_ehVcszKs.-"
               "&order=desc&sort=creation"
               "&site=" + site)
        if fromdate:
            url += "fromdate=%i" % to_epoch(fromdate)
        if todate:
            url += "todate=%i" % to_epoch(todate)

        items = requests.get(url).json().get("items")
        for item in items:
            yield item

    def post_site_name(self, post_url):
        for site in self.sites.values():
            if post_url.startswith(site["site_url"]):
                return site["name"]
        else:
            return "SITE NOT FOUND"

    def to_output_json(self, item, site=None):
        """
        Formats post item accoding to the spec:

        {
            "abstract": <question asked>,
            "external_id": stackexchange_<section name with hyphens for spaces>_<question with hypens replacing the spaces>,
            "date": "<date the question was asked in UTC ISO format, YYYY-MM-DDTHH:MM+00:00; if the hours and minutes are not available, use 00:00 for the time>",
            "title": <question asked>
            "url": "<url linking back to the page>",
            "words": "<just the words, without html or javascript code; the question and the answers>",
            "meta": {
                "stackexchange": {}
            }
        }
        """

        if site:
            site_name = self.sites[site]
        else:
            site_name = self.post_site_name(item["link"])

        words = item["body_markdown"]
        if item["is_answered"]:
            words += ' ' + ' '.join(a["body_markdown"]
                                    for a in item["answers"])

        external_id = ("stackexchange_%s_%s" % (
            item["title"],
            site_name)).replace(' ', '_')

        creation_date = datetime.fromtimestamp(
            item["creation_date"]).isoformat()
        return {
            "abstract": item["title"],
            "external_id": external_id,
            "date": creation_date,
            "title": item["title"],
            "url": item["link"],
            "words": words,
            "meta": {
                "stackexchange": {}
            }
        }

    @classmethod
    def process(cls, site="meta"):

        scraper = cls()
        output_dir = os.path.join(config.OUTPUT_DIR, site)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for q in scraper.questions(site=site):
            item = scraper.to_output_json(q)
            with open(os.path.join(output_dir, "%d.json" % q["question_id"]), "w") as of:
                json.dump(item, of, sort_keys=True, indent=4)

if __name__ == '__main__':
    Scraper.process(site="meta")
