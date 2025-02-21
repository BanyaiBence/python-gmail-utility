import pickle
import os
import base64 #
from dataclasses import dataclass, field
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import re
import logging
logging.basicConfig(level=logging.INFO)

class EmailBuilder:
    LOGGER = logging.getLogger('EmailBuilder')
    def __init__(self):
        self.email = Email()

    def to(self, recipient: str):
        """Sets the recipient of the email."""
        if not Email.validate_address(recipient):
            EmailBuilder.error('Invalid email address')
            return self
        self.email.to = recipient
        return self

    def subject(self, subject: str):
        """Sets the subject of the email."""
        self.email.subject = subject
        return self

    def message(self, message: str):
        """Sets the body content of the email."""
        self.email.message = message
        return self

    def attach(self, attachment: str):
        """Attaches a file to the email."""
        self.email.attachments.append(attachment)
        return self

    def build(self):
        """Constructs the email and returns it as a base64 encoded string."""
        if not self.email.to:
            raise ValueError('Email must have a recipient')
        if not self.email.subject:
            raise ValueError('Email must have a subject')
        if not self.email.message:
            raise ValueError('Email must have a message')

        return self.email


@dataclass
class Email:
    """Dataclass to store email data."""
    to: str = field(default_factory=str)
    subject: str = field(default_factory=str)
    message: str = field(default_factory=str)
    attachments: list = field(default_factory=list)

    def __str__(self):
        return f'To: {self.to}\nSubject: {self.subject}\nMessage: {self.message}\nAttachments:\n{"\n".join(self.attachments)}'

    def __repr__(self):
        return f'{self.to}, {self.subject}, {self.message}'

    def encode(self):
        """Converts the email to a MIME format message."""
        mime_message = MIMEMultipart()
        mime_message['to'] = self.to
        mime_message['subject'] = self.subject
        mime_message.attach(MIMEText(self.message, 'plain'))

        # Attach files to the email
        for attachment in self.attachments:
            part = MIMEBase('application', 'octet-stream')
            with open(attachment, 'rb') as file:
                part.set_payload(file.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename={attachment}')
            mime_message.attach(part)

        return base64.urlsafe_b64encode(mime_message.as_bytes()).decode()

    @staticmethod
    def validate_address(email: str) -> bool:
        """Validates an email address using regex."""
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        return bool(re.match(email_regex, email))


class GmailService:

    CLIENT_SECRET_FILE = 'secrets.json'
    API_NAME = 'gmail'
    API_VERSION = 'v1'
    SCOPES = ['https://mail.google.com/']
    LOGGER = logging.getLogger('GmailService')

    def __init__(self, client_secret_file=CLIENT_SECRET_FILE):
        """Initializes the GmailService object and authenticates with Google."""
        self.CLIENT_SECRET_FILE = client_secret_file
        cred = None
        pickle_file = f'token_{GmailService.API_NAME}_{GmailService.API_VERSION}.pickle'

        if os.path.exists(pickle_file):
            with open(pickle_file, 'rb') as token:
                cred = pickle.load(token)
                GmailService.LOGGER.info(f'Credentials loaded from {pickle_file}')

        # Refresh or authenticate new credentials if necessary
        if not cred or not cred.valid:
            if cred and cred.expired and cred.refresh_token:
                cred.refresh(Request())
                GmailService.LOGGER.info('Refreshed credentials')
            else:
                flow = InstalledAppFlow.from_client_secrets_file(self.CLIENT_SECRET_FILE, GmailService.SCOPES)
                cred = flow.run_local_server()
                GmailService.LOGGER.info('New credentials generated')

            with open(pickle_file, 'wb') as token:
                pickle.dump(cred, token)
                GmailService.LOGGER.info(f'Credentials saved to {pickle_file}')

        # Initialize the Gmail API service
        try:
            self.service = build(GmailService.API_NAME, GmailService.API_VERSION, credentials=cred)
            GmailService.LOGGER.info(f'{GmailService.API_NAME} service created successfully')
        except Exception as e:
            raise ConnectionError(f'Unable to connect: {e}')

    def send_message(self, email: str):
        """Sends the email using the Gmail API."""
        try:
            message = self.service.users().messages().send(userId='me', body={'raw': email.encode()}).execute()
            GmailService.LOGGER.info(f'Email sent successfully: {email}')
            return message
        except Exception as e:
            GmailService.LOGGER.error(f'An error occurred while sending the email: {e}')
