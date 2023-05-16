import logging

from config import Config
from .slack import SlackNotification
from .ctis import CTIS

class NotificationManager():
    def send_error_notification(context: str, error: str, fatal: bool = False):
        if "slack" in Config:
            if not SlackNotification.send_error_notification(Config["slack"]["url"], context, error, fatal):
                logging.error("Failed to send error notification to Slack workspace")

    def send_info_notification(info: str):
        if "slack" in Config:
            if not SlackNotification.send_info_notification(Config["slack"]["url"], info):
                logging.error("Failed to send info notification to Slack workspace")
