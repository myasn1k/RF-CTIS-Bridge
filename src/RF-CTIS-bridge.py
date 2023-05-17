import logging
import sys
import traceback

from config import Config
from notifications import NotificationManager
from notifications.ctis import CTIS

from rfapi import ConnectApiClient
import json, yaml
import random
import string

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
    datefmt="%Y/%m/%d %H:%M:%S",
    handlers=[
        logging.StreamHandler()
    ]
)

def add_dossiers_rels(alert, dossiers):
    for dossier in dossiers:
        ctis.add_relationship("related-to", alert, "alerts", dossier, "x-dossiers")

def parse_docs_and_create(documents, owner):
    if not documents or "documents" not in documents.keys():
        return None, None
    documents = documents["documents"]
    docs = []
    ctis_docs = []
    for doc in documents:
        tmp = {}
        rand = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        if doc["title"]:
            tmp["title"] = doc["title"]
        else:
            tmp["title"] = rand
        logging.debug("Doc title: " + tmp["title"])
        if doc["source"]:
            tmp["source"] = doc["source"]["name"]
        else:
            tmp["source"] = rand
        logging.debug("Doc source: " + tmp["source"])
        tmp["url"] = doc["url"]
        logging.debug("Doc url: " + str(doc["url"]))
        tmp["authors"] = []
        for author in doc["authors"]:
            tmp["authors"].append(author["name"])
        logging.debug("Doc authors: " + str(tmp["authors"]))
        ctis_dossier = ctis.add_dossier(tmp["title"], tmp["source"], f"Url: {tmp['url']}\nAuthors: {tmp['authors']}", owner)
        ctis_docs.append(ctis_dossier)
        tmp["ref"] = []
        for ref in doc["references"]:
            tmp1 = {"fragment": ref["fragment"], "refs": []}
            for e in ref["entities"]:
                tmp1["refs"].append(e["name"])
                logging.debug(f"Entity: name: {e['name']}, type: {e['type']}, frag: {ref['fragment']}")
                try:
                    ctis_ent = ctis.add_entity(e["name"], e["type"], ref["fragment"])
                    if ctis_ent:
                        ctis.add_relationship("related-to", ctis_dossier, "x-dossiers", ctis_ent, Config["mappings"]["entities"][e["type"]]["type"])
                except:
                    logging.error(f"Got a NON fatal error while creating entity {e['name']} of type {e['type']} with fragment {ref['fragment']}, notifying")
                    tb = traceback.format_exc()
                    # send slack error notifications
                    NotificationManager.send_error_notification(
                            "Entity creation error", f"Entity {e['name']} of type {e['type']} with fragment {ref['fragment']}\n" + tb, fatal=False)
                    # log exception
                    logging.error(tb.strip())  # there is a trailing newline
            tmp["ref"].append(tmp1)
        logging.debug("Entity refs: " + str(tmp["ref"]))
        docs.append(tmp)
    return docs, ctis_docs

rf = ConnectApiClient(auth=Config["recorded_future"]["token"])
ctis = CTIS(Config["ctis"]["url"], Config["ctis"]["username"], Config["ctis"]["password"])

def main(argv):
    logging.info("Started")

    NotificationManager.send_info_notification("Starting sync")

    alerts = rf.search_alerts(freetext="",limit=100).entities
    for alert in alerts:
        my_alert = {}
        alert_element = rf.lookup_alert(alert.id)["data"]

        logging.debug("Alert title: " + alert_element["title"])
        logging.debug("Alert url: " + alert_element["url"])
        my_alert["title"] = alert_element["title"].replace("\n", "")
        my_alert["url"] = alert_element["url"]

        if ctis.check_alert_exists(alert.id, my_alert["title"]):
            continue

        owners = []
        owners_ctis = []
        for owner in alert_element["owner_organisation_details"]["organisations"]:
            owners.append(owner["organisation_name"])
            owner_ctis = ctis.add_identity(owner["organisation_name"])
            owners_ctis.append(owner_ctis)
        logging.debug("Alert owners: " + str(owners))
        my_alert["owners"] = owners

        logging.debug("Alert rule name: " + alert_element["rule"]["name"])
        logging.debug("Alert rule url: " + alert_element["rule"]["url"])
        logging.debug("Alert rule owner: " + alert_element["rule"]["owner_name"])
        my_alert["rule"] = {"name": alert_element["rule"]["name"], "url": alert_element["rule"]["url"], "owner": alert_element["rule"]["owner_name"]}
        eei_alert_rule = ctis.add_eei(my_alert["rule"]["name"], my_alert["rule"]["url"], my_alert["rule"]["owner"])

        ctis_docs = {}
        for entity in alert_element["entities"]:
            logging.debug("General docs")
            my_alert["docs"], ctis_docs["docs"] = parse_docs_and_create(entity, owners)
            logging.debug("Entity docs")
            my_alert["ent"], ctis_docs["ent"] = parse_docs_and_create(entity["entity"], owners)
            logging.debug("Risk docs")
            my_alert["risk"], ctis_docs["risk"] = parse_docs_and_create(entity["risk"], owners)
            logging.debug("Trend docs")
            my_alert["trend"], ctis_docs["trend"] = parse_docs_and_create(entity["trend"], owners)

        alert_ctis = ctis.add_alert(alert.id, my_alert["title"], f"RF alert url: {my_alert['url']}\nALERT SUMMARY:\n{yaml.dump(my_alert)}")
        ctis.add_relationship("related-to", eei_alert_rule, "eeis", alert_ctis, "alerts")
        for owner in owners_ctis:
            ctis.add_relationship_al_vic("related-to", alert_ctis, "alerts", owner_ctis, "identities")
        for k, docs in ctis_docs.items():
            if docs: add_dossiers_rels(alert_ctis, docs)

    NotificationManager.send_info_notification("Finished, exiting")
    logging.info("Finished, exiting")

if __name__ == "__main__":
    try:
        main(sys.argv)
    except:
        logging.error(f"Got a fatal error, notifying + aborting")

        tb = traceback.format_exc()

        # send slack error notifications
        NotificationManager.send_error_notification(
            f"Fatal error", tb, fatal=True)

        # log exception
        logging.error(tb.strip())  # there is a trailing newline
