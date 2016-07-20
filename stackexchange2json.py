#!/usr/bin/env python3

# -------------------------------------------------------------------------
# Name:     stackexchange.py
#
# Author:   Radomirs Cirskis
#
# Created:  2016-07-06
# Licence:  WTFPL
# -------------------------------------------------------------------------

## NB! on MS Windows set UTF-8 for the console (cmd.exe): chcp 65001
import requests
from datetime import datetime, date, timezone
import os
import json
import argparse
import xlrd
from collections import OrderedDict
import tinys3
from multiprocessing import Pool, TimeoutError
import time
from fake_useragent import UserAgent

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


class S3Bucket(object):

    @lazy_property
    def conn(self):
        """
        Establishes connection to S3 bucket
        """
        return tinys3.Connection(
            config.S3_ACCESS_KEY,
            config.S3_SECRET_KEY,
            default_bucket=self.name)

    def __init__(self, name=None):
        self.name = name if name else config.S3_BUCKET

    def upload(self, file_name):

        _, output_file_name = os.path.split(file_name)

        with open(file_name, 'rb') as f:
            self.conn.upload(output_file_name, f)


class Scraper(object):
    """
    Encapsulates Stackexchange scraping
    """

    def __init__(self, s3=True, workers=config.WORKERS, verbose=False):
        self.s3 = s3
        self.workers = workers
        self.verbose = verbose
        _ = self.sites  ## pre-cache the 'sites'
        
    @lazy_property
    def output_dir(self):
        """
        Determines the output directory from the configuration 
        and creates it if it doesn't exist yet.
        """
        output_dir = os.path.join(config.OUTPUT_DIR)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        return output_dir
        
    @lazy_property
    def ua(self):
        return UserAgent()
        
    @property
    def user_agent(self):
        return self.ua.random
        
    @lazy_property
    def sites(self):
        """
        Returns a dictionary of all Stackexchange sites
        """
        
        sites_json_filename = os.path.join(self.output_dir, "sites.json")
            
        if os.path.exists(sites_json_filename):
            with open(sites_json_filename, "r") as sf:
                sites = json.load(sf)
                
        else:
        
            url = (config.API_BASE_URL + "sites?pagesize=10000&filter="
                   "!SmNnbu6IrvLP5nC(hk")
            
            for delay in range(3, 28, 5):  # 5 attempts MAX with increasing delay
                try:
                    resp = requests.get(
                            url,
                            headers={'User-Agent': self.user_agent}).json()
                except requests.exceptions.ConnectionError as ex:
                    print("!!!", ex)
                    time.sleep(delay)
                    continue
                    
                if "error_id" in resp:
                    if resp["error_id"] != 502:
                        print("!!! Error querying the site '%s':" % site)
                        print(json.dumps(resp, indent=4))
                    time.sleep(delay)  # wait for a while
                else:
                    break  # success
            else:
                return {}
            
            sites = {item["api_site_parameter"]: item for item in resp.get("items")}
            with open(sites_json_filename, "w") as sf:
                json.dump(sites, sf)
            
        return sites

    @lazy_property
    def bucket(self):
        return S3Bucket()

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
        
        The iterator will continue to retrieve the items until the output is
        empty or the flag "has_more" is set FALSE, eg:
        
            {
                items: [],
                has_more: true,
                quota_max: 300,
                quota_remaining: 295
            }
        """
        
        page = 1
        
        while True:  ## executes until reached the end:
        
            if self.verbose:
                print("*** Processing site %r, page %d." % (site, page))

            url = (config.API_BASE_URL + "questions?filter="
                   "!)Ehv2Yl*OhhLOkeHr5)YcUAgEK*(hc7aypu_0Y_ehVcszKs.-"
                   "&order=desc&sort=creation"
                   "&site=%s&page=%d" % (site, page))
            if fromdate:
                url += "fromdate=%i" % to_epoch(fromdate)
            if todate:
                url += "todate=%i" % to_epoch(todate)

            for delay in range(3, 53, 5):  # 10 attempts MAX with increasing delay
                try:
                    resp = requests.get(
                            url,
                            headers={'User-Agent': self.user_agent}).json()
                except requests.exceptions.ConnectionError as ex:
                    print("!!!", ex)
                    time.sleep(delay)
                    continue

                if "error_id" in resp:
                    if resp["error_id"] != 502:
                        print("!!! Error querying the site '%s':" % site)
                        print(json.dumps(resp, indent=4))
                    time.sleep(delay)  # wait for a while
                else:
                    break  # success
                    
            else:
                print("!!! Failed to retrieve the questions form the site '%s'" % site)
                return
                
            items = resp.get("items")
            if items:
                for item in items:
                    yield item
            else:
                if page == 1:
                    print("!!! No items found for the site '%s'" % site)
                break  ## reached 'END'
            
            if not resp.get("has_more"):  ## the last page reached
                break
            
            page += 1

    def site_url(self, site):
        s = self.sites.get(site)
        return s.get("site_url") if s else None
        
    def site_name(self, site):
        s = self.sites.get(site)
        return s.get("name") if s else None

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
        if item["is_answered"] and "answers" in item:
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

        output_dir = os.path.join(self.output_dir, site)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        for q in self.questions(site=site):
            item = self.to_output_json(q)
            file_name = os.path.join(output_dir,
                                     "stackexchange_%s_%d.json" % (site, q["question_id"]))
            with open(file_name, "w") as of:
                json.dump(item, of, indent=4)

            if self.s3:
                self.bucket.upload(file_name)

    def process_sites(self, *, sites):
        """
        Process sites in parallel
        """
        
        if self.workers <= 1:  # single worker
            for site in sites:
                site_url = self.site_url(site)
                site_name = self.site_name(site)
                self.process_site(site=site)
                print("*** %s (%s) processed" % (site_name, site_url))
        else:
            with Pool(processes=self.workers) as pool:
                params = dict(s3=self.s3)
                site_data = [(s, params) for s in sites]
                for res in pool.starmap(process_site, site_data):
                    site = res.get("site")
                    params = res.get("params")
                    site_url = self.site_url(site)
                    site_name = self.site_name(site)
                    
                    print("*** %s (%s) processed" % (site_name, site_url))

    def get_sites(self, *, file_name="stackexchange_forums.xlsx"):
        """
        Extrast site names form the excel workbook
        """
        book = xlrd.open_workbook(file_name)
        sheet = book.sheet_by_index(0)
        for rx in range(sheet.nrows):
            site_name, site_url = (c.value for c in sheet.row(rx))
            site = self.find_site_by_url(site_url)
            yield site["api_site_parameter"]

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

        sites = self.get_sites(file_name=file_name)
        self.process_sites(sites=sites)


def process_site(site="meta", params={}):
    """
    Module level function for parallel invocation
    """
    s3 = params.get("s3", False)  # Parameters passed trough the pool
    scraper = Scraper(s3=s3)
    scraper.process_site(site=site)
    return dict(site=site, params=params)


def main():
    parser = argparse.ArgumentParser(description="Stackexchange site "
                                     "parser and scraper.")
    parser.add_argument('-W', '--workers', dest='workers',
                        help='Number of worker processes (default: %d)' % config.WORKERS, type=int, default=config.WORKERS)
    parser.add_argument('-V', '--verbose', action='store_true',
                        help='Provides more detailed output.')
    parser.add_argument('-l', '--list-sites', action='store_true',
                        help='List all available sites.')
    parser.add_argument('--no-s3', dest='s3', action='store_false',
                        help='Suppress file upload to S3')
    parser.set_defaults(s3=True)
    parser.add_argument('-e', '--excel', dest='excel',
                        help=('Excel spreasheet workbook file name '
                              'containing list of the sites.'))
    parser.add_argument('-s', '--site', dest='site',
                        help=('Single Stackexchange site API name, e.g., '
                              '"meta", "stacoverflow", etc. (default: "meta")'),
                        default="meta")

    args = parser.parse_args()
    scraper = Scraper(s3=args.s3, workers=args.workers, verbose=ags.verbose)
    if args.list_sites:
        for name, site in scraper.sites.items():
            print((
                "*** %(api_site_parameter)s:\nName: %(name)s, Type: %(site_type)s, " "URL: %(site_url)s, State: %(site_state)s") % site)
    elif args.excel:
        scraper.process_xls(file_name=args.excel)
    else:
        scraper.process_site(site=args.site)

if __name__ == '__main__':
    main()
