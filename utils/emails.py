import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, subject, text_body=None, html_body=None):
    sender_email = "johnsmith179805@gmail.com"
    sender_password = "wnss dlsn buau woql"  # Make sure you set this securely

    # Set up the email
    message = MIMEMultipart("alternative")
    message["From"] = sender_email
    message["To"] = to_email
    message["Subject"] = subject

    if text_body:
        text_part = MIMEText(text_body, "plain","utf-8")
        message.attach(text_part)

    if html_body:
        html_part = MIMEText(html_body, "html","utf-8")
        message.attach(html_part)

    # Connect to Gmail SMTP
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, message.as_bytes())

