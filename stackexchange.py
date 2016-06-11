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
from datetime import datetime, date, timezone
import os
import json
import argparse
import xlrd
from collections import OrderedDict

import config


def to_epoch(timestamp=None):
    """
    Converts datetime or date into Unix Epoch 
    """
    if timestamp is None:
        return None
    if type(timestamp) is datetime:
        return int(timestamp.replace(tzinfo=timezone.utc).timestamp())
    if type(timestamp) is date:
        return int(datetime.combine(
            timestamp,
            datetime.min.time())
            .replace(tzinfo=timezone.utc)
            .timestamp())
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
        url = (config.API_BASE_URL + "questions?filter="
               "!)Ehv2Yl*OhhLOkeHr5)YcUAgEK*(hc7aypu_0Y_ehVcszKs.-"
               "&order=desc&sort=creation"
               "&site=" + site)
        if fromdate:
            url += "fromdate=%i" % to_epoch(fromdate)
        if todate:
            url += "todate=%i" % to_epoch(todate)

        resp = requests.get(url).json()
        ### print(json.dumps(resp, indent=4))
        items = resp.get("items")
        for item in items:
            yield item

    def find_site_by_url(self, url):

        for site in self.sites.values():
            if url.startswith(site["site_url"]):
                return site
        else:
            raise Exception("Site not found for %r" % url)

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
            site_name = self.sites[site]["name"]
        else:
            site_name = self.find_site_by_url(item["link"])["name"]

        # collect words:
        words = item["body_markdown"]
        if item["is_answered"]:
            words += ' ' + ' '.join(a["body_markdown"]
                                    for a in item["answers"])

        external_id = ("stackexchange_%s_%s" % (
            site_name, item["title"])).replace(' ', '-')

        creation_date = datetime.fromtimestamp(
            item["creation_date"]).isoformat()
        return OrderedDict([
            ("external_id", external_id),
            ("abstract", item["title"]),
            ("date", creation_date),
            ("title", item["title"]),
            ("url", item["link"]),
            ("words", words),
            ("meta", {
                "stackexchange": {"forum": site_name}
            })
        ])

    def process_site(self, *, site="meta"):
        """
        Collects data for a single Stackexchange site and 
        stores extracted JSON  on $OUTPUT_DIR/`site API name`.
        """

        output_dir = os.path.join(config.OUTPUT_DIR, site)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for q in self.questions(site=site):
            item = self.to_output_json(q)
            with open(os.path.join(output_dir,
                    "stackexchange_%s_%d.json" % (site, q["question_id"])), "w") as of:
                json.dump(item, of, indent=4)


    def process_xls(self, *, file_name="stackexchange_forums.xlsx"):
        """
        Read the list of 'sites' from the Excel worksheet and
        retrieve the question/ansers.

        Expected format is (site name, site URL), eg,
        Stack Overflow | http://stackoverflow.com/
        Super User	   | http://superuser.com/
        Ask Ubuntu	   | http://askubuntu.com/
        ...
        """

        book = xlrd.open_workbook(file_name)
        sheet = book.sheet_by_index(0)
        for rx in range(sheet.nrows):
            site_name, site_url = (c.value for c in sheet.row(rx))
            site = self.find_site_by_url(site_url)
            print("*** Processing: %s (%s)" % (site_name, site_url))
            self.process_site(site=site["api_site_parameter"])


def main():
    parser = argparse.ArgumentParser(description="Stackexchange site "
                                     "parser and scraper.")
    parser.add_argument('-e', '--excel', dest='excel',
                        help=('Excel spreasheet workbook file name '
                              'containing list of the sites.'))
    parser.add_argument('-s', '--site', dest='site',
                        help=('Single Stackexchange site API name, e.g., '
                              '"meta", "stacoverflow", etc. (default: "meta")'),
                        default="meta")

    args = parser.parse_args()
    scraper = Scraper()
    if args.excel:
        scraper.process_xls(file_name=args.excel)
    else:
        scraper.process_site(site=args.site)

if __name__ == '__main__':
    main()
