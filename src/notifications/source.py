# webhook/url only at this point, email or something in the future
# would require reworking config loading into something fancier
class NotificationSource():
    def send_error_notification(url: str, context: str, error: str, fatal: bool = False) -> bool:
        raise Exception("Function implementation not found")
