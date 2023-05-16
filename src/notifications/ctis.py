from .source import NotificationSource
from config import Config
import requests
import html2text 
from enum import Enum
import urllib.parse
import random
import string

class ReqStat(Enum):
    NEW = 1
    OLD = 2
    ERR = 3

class CTIS():

    headers = {}
    url = ""

    def __init__(self, url: str, username: str, password: str):
        self.url = url
        self.CTIS_login(username, password)

    def do_req(self, url, json):
        response = requests.post(self.url + url, headers = self.headers, json = json)
        ok = ReqStat.NEW
        if response.status_code == 201:
            if "relationships" in url:
                res = response.json()
            else:
                res = response.json()["_id"]
        elif response.status_code == 409:
            if "relationshipTypes" in url or "relationships" in url:
                res = response.json()
            else:
                res = response.json()["_error"]["message"]["_id"]
            ok = ReqStat.OLD
        else:
            res = response.json()
            ok = ReqStat.ERR

        return ok, res
    
    def check_aliases(self, entity_url, name):
        res = requests.get(self.url + entity_url, headers = self.headers, json = []).json()["_items"]
        for e in res:
            if "aliases" in e and name in e["aliases"]:
                return e["_id"]
        return None

    def add_relationship_al_vic(self, rel_type, src, src_type, dst, dst_type):
        json_query = [
            {
                "confidence": 100,
                "sub-type": "is_victim",
                "relationship_type": rel_type,
                "source_ref": src,
                "source_type": src_type,
                "target_ref": dst,
                "target_type": dst_type,
                "type": "relationship"
            }
        ]

        ok, rel = self.do_req("/relationships", json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create al-vic relationship {rel}")
        return rel

    def add_relationship(self, rel_type, src, src_type, dst, dst_type):
        json_query = [
            {
                "confidence": 100,
                "relationship_type": rel_type,
                "source_ref": src,
                "source_type": src_type,
                "target_ref": dst,
                "target_type": dst_type,
                "type": "relationship"
            }
        ]

        ok, rel = self.do_req("/relationships", json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create relationship {rel}")
        return rel

    def add_identity(self, name):
        res = self.check_aliases("/identities", name)
        if res != None:
            return res
        if name in Config["mappings"]["identities"].keys():
            name = Config["mappings"]["identities"][name]
        json_query = [
            {
                "confidence": 100,
                "name": name,
                "identity_class": "organization",
                "x-sources": [
                    {
                        "source_name": "default",
                        "classification": 0,
                        "releasability": 0,
                        "tlp": 0
                    }
                ]
            }
        ]

        ok, identity = self.do_req("/identities", json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create identity {name}")
        return identity

    def do_patch(self, url, etag, json):
        hdr = self.headers.copy()
        hdr["If-Match"] = etag
        return requests.patch(self.url + url, headers=hdr, json=json).json()

    def do_get(self, url):
        return requests.get(self.url + url, headers=self.headers).json()

    def add_entity(self, param, type, description):
        if type not in Config["mappings"]["entities"].keys():
            with open("/files/missing_entities.txt", 'a+') as f:
                f.write(f"Entity type doesn't exist in mapping: {type}; param: {param}; description: {description}\n")
            return None
        description = f"RF type: {type}\n" + html2text.html2text(description)
        json_query = [
            {
                Config["mappings"]["entities"][type]["description"]: description,
                Config["mappings"]["entities"][type]["param"]: param,
                "x-sources": [
                    {
                        "source_name": "default",
                        "classification": 0,
                        "releasability": 0,
                        "tlp": 0
                    }
               ],
            }
        ]
        if "class" in Config["mappings"]["entities"][type].keys():
            json_query[0]["identity_class"] = Config["mappings"]["entities"][type]["class"] 

        ok, entity = self.do_req("/" + Config["mappings"]["entities"][type]["type"], json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create entity {entity} of type {type}")
        return entity

    def add_dossier(self, name, originator, text, owners):
        json_query = [
            {
                "name": name,
                "type": "x-dossier",
                "x-sources": [
                    {
                        "source_name": "default",
                        "classification": 0,
                        "releasability": 0,
                        "tlp": 0
                    }
                ],
                "id_dossier": ''.join(random.choice(string.ascii_lowercase) for i in range(16)),
                "originator": "ori def", #TODO originator,
                "addressee": ["addr def"], #TODO owners,
                "text": text
            }
        ]

        ok, dossier = self.do_req("/x-dossiers", json_query)
        if ok == ReqStat.ERR:
            if "addressee" not in dossier["_issues"].keys() and "originator" not in dossier["_issues"].keys():
                raise Exception(f"Can't create dossier: {dossier}")
            if "addressee" in dossier["_issues"].keys():
                self.update_setting("xdossiers_addressee_allowed", owners)
            if "originator" in dossier["_issues"].keys():
                self.update_setting("xdossiers_originator_allowed", [originator])
            ok, dossier = self.do_req("/x-dossiers", json_query)
            if ok == ReqStat.ERR:
                raise Exception(f"Can't create dossier: {dossier}")
        return dossier

    def add_alert(self, id, name, message):
        json_query = [
            {
                "entity_type": "report",
                "alert_type": "notify-frontend",
                "labels": ["rf"],
                "title": name + " - " + str(id),
                "message": message,
                "from": "rf",
                "role": "analyst",
                "x-sources": [
                    {
                        "source_name": "default",
                        "classification": 0,
                        "releasability": 0,
                        "tlp": 0
                    }
                ]
            }
        ]

        ok, alert = self.do_req("/alerts", json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create alert: {alert}")
        if ok == ReqStat.OLD:
            return None
        return alert

    def update_setting(self, setting, new):
         cur = self.do_get(f"/settings?where=%7B%22parameter_name%22%20%3A%20%22{setting}%22%7D")["_items"][0]
         etag = cur["_etag"]
         id = cur["_id"]
         del cur["_id"]
         del cur["_aging_time"]
         del cur["_created"]
         del cur["_etag"]
         del cur["_links"]
         del cur["_updated"]
         cur["parameter_value"]["list_values"] += new
         self.do_patch(f"/settings/{id}", etag, cur)

    def check_alert_exists(self, id, title):
        cur = self.do_get(f"/alerts?where=%7B%22title%22%3A%20%22{urllib.parse.quote_plus(title + ' - ' + id)}%22%7D&page=1&max_results=25")
        if cur["_items"]:
            return True
        else:
            return False

    def add_eei(self, name, url, author):
        json_query = [
            {
                "name": name,
                "description": url,
                "author": author,
                "x-sources": [
                    {
                        "source_name": "default",
                        "classification": 0,
                        "releasability": 0,
                        "tlp": 0
                    }
                ]
            }
        ]

        ok, eei = self.do_req("/eeis", json_query)
        if ok == ReqStat.ERR:
            raise Exception(f"Can't create eei: {eei}")
        return eei

    def CTIS_login(self, user, password):
        #response = requests.post(f"{self.url}/api/auth/login", json={"username": user, "password": password})
        response = requests.get(f"{self.url}/login", auth=(user, password))
        self.headers = {'accept': 'application/json', 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + response.json()["data"]["access_token"]}
