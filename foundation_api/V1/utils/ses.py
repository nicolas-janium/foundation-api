import boto3
import os
from email.message import EmailMessage
from email.header import Header
from minify_html import minify
from foundation_api.V1.utils.send_email import add_identifier

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
        TemplateName='janium-ses-identity-verification-template',
        FromEmailAddress='support@janium.io',
        TemplateSubject='Janium Single Sender Email Verification',
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
                information to help you get started.</p>
            </body>
            </html>
        """,
        SuccessRedirectionURL='https://app.janium.io',
        FailureRedirectionURL='https://janium.io/failed_verification'
    )
    print(response)

def send_forwarding_rule_test_email(recipient):
    main_email = EmailMessage()
    main_email.make_alternative()

    main_email['Subject'] = "Janium Forwarding Rule Test Email"
    main_email['From'] = str(Header('{} <{}>')).format('Janium', 'support@janium.io')
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

    email_html = add_identifier(email_html)
    email_html = minify(email_html, minify_js=False, minify_css=False)

    main_email.add_alternative(email_html, 'html')

    return client.send_raw_email(
        Source=main_email['From'],
        Destinations=[main_email['To']],
        RawMessage={
            "Data": main_email.as_string()
        }
    )





### Onboarding steps ###

def send_ses_identity_verification_email(recipient):
    response = client.send_custom_verification_email(
        EmailAddress=recipient,
        TemplateName='janium-single-sender-email-verification-template'
    )

def is_ses_identity_verified(email_address):
    response = client.get_identity_verification_attributes(
        Identities=[
            email_address,
        ]
    )
    if response['VerificationAttributes'][email_address]['VerificationStatus'] == 'Success':
        return True
    return False

def create_ses_identiy_dkim_tokens(email_address):
    get_dkim_response = client.verify_domain_dkim(
        Domain=email_address[email_address.index('@') + 1 : ]
    )
    enable_dkim_signing_response = client.set_identity_dkim_enabled(
        Identity=email_address,
        DkimEnabled=True
    )
    return {
        "dkim_tokens": get_dkim_response['DkimTokens']
    }

# def enable_ses_identity_dkim_signing(email_address):
#     return client.set_identity_dkim_enabled(
#         Identity=email_address,
#         DkimEnabled=True
#     )

def is_ses_identity_dkim_verified(email_address):
    dkim_status_response = client.get_identity_dkim_attributes(
        Identities=[email_address]
    )
    if dkim_status_response['DkimAttributes'][email_address]['DkimVerificationStatus'] == 'Success':
        return True
    return False

def list_identity_policies(identity):
    response = client.list_identity_policies(
        Identity=identity,
    )

    print(response)

def get_ses_identity_verification_status(identity):
    response = client.get_identity_verification_attributes(
        Identities=[
            identity,
        ]
    )
    print(response)

def main():
    # get_ses_identity_verification_status('jason@cxo.org')
    create_ses_identiy_dkim_tokens('jason@cxo.org')
    # enable_ses_identity_dkim_signing('jason@cxo.org')
    # pass
    # create_custom_verification_email_template()
    # send_verification_email('narnold113@gmail.com')
    # send_forwarding_verification_email('nic@janium.io')
    # from_address = 'nic@janium.io'
    # verify_dkim_response = verify_ses_dkim('nic@janium.io')
    # verify_dkim('narnold113@gmail.com')

    # print(is_ses_identity_verified('support@janium.io'))

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