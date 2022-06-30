"""
(c) BancaStato 2021
"""
import configparser
import sys
import requests
import json
import xmltodict
from datetime import datetime, date, timedelta
import logging
import logging.config
import os.path
import hashlib


OUTPUT_DIR = "./"
REPORT_JSON = "fusc_rep.json"
CONFIG_FILE = "./fusc_config.ini"
DATE_FORMAT = "%Y-%m-%d"


def get_logging(log_path):
    """
    logging.basicConfig(
        filename=log_path,
        level=logging.DEBUG,
        format="[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    """

    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("chardet.charsetprober").setLevel(logging.WARNING)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.WARNING)
    logging.getLogger("elasticsearch").setLevel(logging.WARNING)

    return logger


def _get_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    return config


def prepare_daily_list_url(fusc_url, start_date, stop_date, page=0):
    # GET FUSC QUERY URL
    return fusc_url.format(start_date, stop_date, page)


def get_element(url):
    # GET SINGLE FUSC ELEMENT
    response = requests.get(url)
    return xmltodict.parse(response.text)


out_global = {}

max = 50


def get_data_interval(fusc_url, start_date, stop_date, page, logger):
    """
    FUSC PARSING: Produces a dict id:entry of entries for the selected time range.
    """
    global max
    global out_global
    url = prepare_daily_list_url(fusc_url, start_date, stop_date, page)
    print(url)
    
    response = requests.get(url)
    xpars = xmltodict.parse(response.text)
    output_dict = json.loads(json.dumps(xpars["bulk:bulk-export"]))
    print(output_dict.keys())

    for l in output_dict["publication"]:

        url_tmp = l["@ref"]

        try:
            ele = get_element(url_tmp)

        except Exception as e:
            logger.error(str(e))
            continue
        output_dict = json.loads(json.dumps(ele))
        key = list(output_dict.keys())[0]
        element = output_dict[key]
        meta = element["meta"]
        content = element["content"]

        section = key.split(":")[0].split("-")[0]

        out_global[url_tmp] = {"section": section, "meta": meta, "content": content}
    print(len(out_global))
    return


def do_round(logger, day=None, day_end=None):
    global max

    # fusc_query_url = conf["FUSC"]["rest_query_url"]
    fusc_query_url = "https://amtsblattportal.ch/api/v1/publications/xml?publicationStates=PUBLISHED&publicationDate.start={}&publicationDate.end={}&page={}&cantons=TI&cantons=GR"
    #print(fusc_query_url)
    page = 0
    try:
        while True:

            logger.debug("Loading data from FUSC")
            if not day_end:
                day_end = datetime.now().strftime(DATE_FORMAT)
            #print(fusc_query_url)
            get_data_interval(
                fusc_query_url,
                day,
                day_end,
                str(page),
                logger,
            )
            page += 1

    except Exception as e:
        logger.error(str(e))
        # res = "".join(traceback.format_exception(type(e)), e, e.__traceback__)
        logger.error("# page {} saved".format(page))


def get_interval(days=1):
    a = datetime.today()
    numdays = days
    interval_list = []
    for x in reversed(range(0, numdays)):
        fr = a - timedelta(days=x + 1)
        to = a - timedelta(days=x)
        interval_list.append(
            {
                "from": fr.strftime(DATE_FORMAT),
                "to": to.strftime(DATE_FORMAT),
            }
        )
    return interval_list


def export_fusc(fr, to):
    global max

    logger = get_logging("./")

    try:
        do_round(logger, day=fr, day_end=to)
    except Exception as e:
        logger.error("Main Exception: " + str(e))
    print(len(out_global))
    with open("{}.json".format(to), "w") as jf:
        json.dump(out_global, jf)
    return "{}.json".format(to)


def get_report(interval=2):
    try:
        with open(REPORT_JSON, "r") as jf:
            return json.load(jf)
    except Exception as e:
        print(e)
        a = datetime.today()
        a = a - timedelta(days=interval)
        out = {"last_update": a.strftime(DATE_FORMAT), "lf": None}
        return out


def store_report(rep):
    with open(REPORT_JSON, "w") as jf:
        return json.dump(rep, jf)

def main2():
    lf = export_fusc("2022-06-27", "2022-06-28")

def main():
    rep = get_report(interval=6)
    end = datetime.today() - timedelta(days=1)  # yesterday
    end = end.strftime(DATE_FORMAT)

    if rep["last_update"] != end:
        print("Updare interval [{} {}]".format(rep["last_update"], end))
        lf = export_fusc(rep["last_update"], end)
        rep["last_update"] = end
        rep["lf"] = lf
        store_report(rep)
        print("Export complete, output file: {}".format(lf))
    else:
        print("NTD")


if __name__ == "__main__":
    main2()

