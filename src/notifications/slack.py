from datetime import datetime
import logging
import requests
from typing import Dict
import json

from .source import NotificationSource

class SlackNotification(NotificationSource):
    def _post_webhook(body: Dict, url: str) -> bool:
        r = requests.post(url, json=body)
        if r.status_code != 200:
            logging.error(
                f"Error sending Slack notification ({r.status_code}): {r.content.decode()}")
            return False

        return True

    def send_error_notification(url: str, context: str, error: str, fatal: bool = False) -> bool:

        if error:
            err = error
        else:
            err = " "
        if len(err) > 1000:
            err = err[:1000] + "..."

        body = {
            "attachments": [
                {
                    "color": "#fc0303",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"{'Fatal ' if fatal else ''}Error"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*An error occurred:* {context}"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"```{err}```\nFor more details, please check the app container logs"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": "If you think this is a bug, please <https://github.com/myasn1k/rd-ctis-integration/issues|open an issue> on GitHub"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        return SlackNotification._post_webhook(body, url)
    
    def send_info_notification(url: str, info: str) -> bool:
        body = {
            "attachments": [
                {
                    "color": "#0FFF50",
                    "blocks": [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"Info"
                            }
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": info
                            }
                        }
                    ]
                }
            ]
        }

        return SlackNotification._post_webhook(body, url)
