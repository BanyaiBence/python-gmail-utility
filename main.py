from google import GmailService, EmailBuilder
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

if __name__ == '__main__':
	builder = (EmailBuilder()
		.to(input('TO: '))
	    .subject(input('SUBJECT: '))
	    .message(input('MESSAGE: ')))

	while True:
		attachment = input('ATTACHMENT: ')
		if attachment == '':
			break
		builder.attach(attachment)

	email = builder.build()
	service = GmailService()
	service.send_message(email)


