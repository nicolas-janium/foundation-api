import boto3
import os
from email.message import EmailMessage
from email.header import Header
from html2text import html2text
import css_inline
from minify_html import minify
from pprint import pprint
from foundation_api.V1.utils.send_email import add_tracker
from bs4 import BeautifulSoup as Soup
from bs4 import NavigableString

client = boto3.client(
    'ses',
    region_name="us-east-2",
    aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
)

def send_simple_email(recipient, body, subject):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = subject
    main_email['From'] = str(Header('{} <{}>')).format('Nic Arnold', 'nic@janium.io')
    main_email['To'] = recipient
    main_email['MIME-Version'] = '1.0'

    main_email.add_alternative(body, 'plain')

    response = client.send_raw_email(
        Source=main_email['From'],
        Destinations=[main_email['To']],
        RawMessage={
            "Data": main_email.as_string()
        }
    )
    return response

def create_custom_verification_email_template():
    response = client.create_custom_verification_email_template(
        TemplateName='janium-sender-verification',
        FromEmailAddress='nic@janium.io',
        TemplateSubject='Janium Sender Verification',
        TemplateContent="""
            <html>
            <head></head>
            <body style='font-family:sans-serif;'>
            <h1 style='text-align:center'>Ready to start sending 
            email with Janium?</h1>
            <p>We here at Janium are happy to have you on
                board! There's just one last step to complete before
                you can start sending email. Just click the following
                link to verify your email address. Once we confirm that 
                you're really you, we'll give you some additional 
                information to help you get started with ProductName.</p>
            </body>
            </html>
        """,
        SuccessRedirectionURL='https://janium.io/',
        FailureRedirectionURL='https://janium.io/failed_verification'
    )
    print(response)

def send_verification_email(recipient):
    response = client.send_custom_verification_email(
        EmailAddress=recipient,
        TemplateName='janium-sender-verification'
    )
    print(response)

def send_forwarding_verification_email(recipient):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = "Janium Forwarding Verification"
    main_email['From'] = str(Header('{} <{}>')).format('Janium', 'noreply@janium.io')
    main_email['To'] = recipient
    main_email.add_header('jid', os.getenv('JANIUM_EMAIL_ID'))
    main_email['MIME-Version'] = '1.0'

    email_html = """\
        <!DOCTYPE html>
        <html>
            <div>
                Test. Ignore or delete
            </div>
        </html>
    """

    email_html = add_tracker(email_html)
    email_html = minify(email_html, minify_js=False, minify_css=False)

    main_email.add_alternative(email_html, 'html')

    response = client.send_raw_email(
        Source=main_email['From'],
        Destinations=[main_email['To']],
        RawMessage={
            "Data": main_email.as_string()
        }
    )

def verify_ses_dkim(from_address):
    dkim_status_response = client.get_identity_dkim_attributes(
        Identities=[from_address]
    )
    if dkim_status_response['DkimAttributes'][from_address]['DkimVerificationStatus'] == 'NotStarted':
        enable_dkim_response = client.set_identity_dkim_enabled(
            Identity=from_address,
            DkimEnabled=True
        )
        get_dkim_response = client.verify_domain_dkim(
            Domain=from_address[from_address.index('@') + 1 : ]
        )

        return {
            "status": "started",
            "dkim_tokens": get_dkim_response['DkimTokens']
        }
    elif dkim_status_response['DkimAttributes'][from_address]['DkimVerificationStatus'] == 'Pending':
        return {
            "status": "pending",
            "dkim_tokens": dkim_status_response['DkimAttributes'][from_address]['DkimTokens']
        }
    elif dkim_status_response['DkimAttributes'][from_address]['DkimVerificationStatus'] == 'Success':
        return {
            "status": "success",
            "dkim_tokens": dkim_status_response['DkimAttributes'][from_address]['DkimTokens']
        }

def main():
    # create_custom_verification_email_template()
    # send_verification_email('narnold113@gmail.com')
    # send_forwarding_verification_email('nic@janium.io')
    # from_address = 'nic@janium.io'
    verify_dkim_response = verify_ses_dkim('nic@janium.io')
    # verify_dkim('narnold113@gmail.com')

    # pprint({
    #     'message': 'Dkim verification pending',
    #     'data': [
    #         {
    #             'name': '{}._domainkey.{}'.format(token, from_address[from_address.index('@') + 1 : ]),
    #             'type': 'CNAME',
    #             'value': '{}.dkim.amazonses.com'.format(token)
    #         }
    #         for token in verify_dkim_response['dkim_tokens']
    #     ]
    # })

if __name__ == "__main__":
    main()