import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()


def send_email(to_email: str, subject: str, body: str, is_html: bool = False):
    from_email = os.environ['EMAIL']
    from_password = os.environ['APP_PASSWORD']

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    if is_html:
        msg.attach(MIMEText(body, "html"))  # HTML part
    else:
        msg.attach(MIMEText(body, "plain"))  # Plain text

    server = smtplib.SMTP("smtp.gmail.com", 587)
    server.starttls()
    server.login(from_email, from_password)
    server.send_message(msg)
    server.quit()