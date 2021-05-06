import boto3
import os

client = boto3.client(
    'ses',
    region_name="us-east-2",
    aws_access_key_id=os.getenv('SES_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('SES_SECRET_ACCESS_KEY')
)

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

def main():
    # create_custom_verification_email_template()
    send_verification_email('narnold113@gmail.com')

if __name__ == "__main__":
    main()