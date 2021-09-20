import email
import json
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock

from model import (Action, Email_config, create_gcf_db_engine, create_gcf_db_session)
from flask import Response
from sqlalchemy import and_
from sqlalchemy.orm.attributes import flag_modified


def main(request):
    with create_gcf_db_session(create_gcf_db_engine())() as session:
        req_dict = request.form.to_dict()
        # pprint(req_dict)
        email_message = email.message_from_string(req_dict['email'])

        body = ''
        if email_message.is_multipart():
            for part in email_message.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get('Content-Disposition'))

                if ctype == 'text/plain' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                elif ctype == 'text/html' and 'attachment' not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                    break # Default to html body
        else:
            body = email_message.get_payload(decode=True)


        is_from_outlook = True if 'outlook' in email_message.get('Message-ID') else False
        to_address = str(email_message.get('To'))
        print(to_address)
        if '<' in to_address:
            index = to_address.index('<')
            to_address = to_address[index + 1: len(to_address) - 1]

        forwarded_to_address = str(email_message.get('X-Forwarded-To'))
        print(forwarded_to_address)

        ### For gmail, inbound_parse_email is in X-Forwarded-To field. For O365, it's in the To field ###
        if 'Janium Forwarding Rule Test Email' in json.dumps(req_dict):
            if email_config := session.query(Email_config).filter(Email_config.inbound_parse_email.in_([to_address, forwarded_to_address])).first():
                email_config.is_email_forwarding_rule_verified = True
                flag_modified(email_config, 'is_email_forwarding_rule_verified')
                session.commit()
        elif 'forwarding-noreply@google.com' in json.dumps(req_dict) or 'Gmail Forwarding Confirmation' in json.dumps(req_dict):
            if email_config := session.query(Email_config).filter(Email_config.inbound_parse_email.in_([to_address, forwarded_to_address])).first():
                body = str(body)
                confirmation_code_index = body.index('Confirmation code')
                confirmation_code = body[confirmation_code_index + 19: confirmation_code_index + 28]
                email_config.gmail_forwarding_confirmation_code = confirmation_code
                flag_modified(email_config, 'gmail_forwarding_confirmation_code')
                session.commit()
        else:
            references = str(email_message.get('References')).split(',')
            for reference in references:
                reference = str(reference).replace('<', '').replace('>', '').split('@')[0]
                if original_send_action := session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 4)).first():
                    if original_receive_action := session.query(Action).filter(and_(Action.email_message_id == reference, Action.action_type_id == 6)).first():
                        pass
                    else:
                        new_action = Action(str(uuid4()), original_send_action.contact_id, 6, datetime.utcnow(), None, None, reference)
                        session.add(new_action)
                        session.commit()
        return Response('Success', 200)

if __name__ == '__main__':
    data = {
        "ulinc_config_id": "d0b9f557-942c-4d5f-b986-8ff935ebce81",
        "contact_source_id": "e6fcfe00-d61b-4f55-b946-f76db032c7a7"
    }
    req = Mock(get_json=Mock(return_value=data), args=data)
    func_res = main(req)
    print(func_res.get_data())
    print(func_res.status_code)
