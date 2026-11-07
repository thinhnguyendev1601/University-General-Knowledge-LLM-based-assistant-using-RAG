"""Real SMTP and password-reset API against a local Mailpit sink; no external email."""
import os
import logging
import re
import uuid
from urllib.parse import parse_qs,urlsplit

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app import app
from api.auth_security import digest
from api.mail import get_mailer
from api.models import AccountToken
from tests.test_auth import account, HEADERS, PASSWORD

pytestmark=pytest.mark.skipif(not os.getenv('MAILPIT_TESTS'),reason='Opt-in local Mailpit SMTP acceptance')


def test_real_smtp_reset_single_use_session_revocation_and_no_verification_email(account,caplog):
    caplog.set_level(logging.INFO,logger='uvicorn.error')
    client,engine,_=account
    email='b7-mail-'+uuid.uuid4().hex+'@university.edu.vn'
    # Restore the real adapter; account fixture captures mail for normal unit tests.
    app.dependency_overrides.pop(get_mailer,None)
    ids=[]
    with httpx.Client(base_url='http://127.0.0.1:8025',timeout=5) as mailpit:
        def messages():
            response=mailpit.get('/api/v1/search',params={'query':'to:'+email})
            assert response.status_code==200
            return response.json()['messages']

        try:
            assert client.post('/api/auth/register',json={'email':email,'name':'Mailpit verification','password':PASSWORD}).status_code==201
            assert messages()==[]
            auth=client.post('/api/auth/login',json={'email':email,'password':PASSWORD})
            assert auth.status_code==200
            old_cookie=client.cookies.get('university_session')
            delivery=client.post('/api/auth/forgot-password',json={'email':email})
            assert delivery.status_code==202
            inbox=messages()
            assert len(inbox)==1
            ids=[item['ID'] for item in inbox]
            body=mailpit.get('/api/v1/message/'+ids[0]).json()['Text']
            link=re.search(r'http://[^\s]+/reset-password#token=[^\s]+',body).group()
            parsed=urlsplit(link)
            assert not parsed.query
            token=parse_qs(parsed.fragment)['token'][0]
            assert token not in caplog.text and email not in caplog.text
            assert 'smtp_delivery' in caplog.text and delivery.headers['X-Request-Id'] in caplog.text
            with Session(engine) as db:
                assert db.scalar(select(AccountToken)).token_hash==digest(token)
            response=client.post('/api/auth/reset-password',json={'token':token,'password':PASSWORD+' changed'})
            assert response.status_code==200
            assert client.post('/api/auth/reset-password',json={'token':token,'password':PASSWORD+' again'}).status_code==400
            client.cookies.set('university_session',old_cookie)
            assert client.get('/api/auth/me').status_code==401
            assert client.post('/api/auth/login',json={'email':email,'password':PASSWORD+' changed'}).status_code==200
        finally:
            # Delete only messages addressed to this test's unique synthetic recipient.
            ids=list({item['ID'] for item in messages()} | set(ids))
            if ids:
                response=mailpit.request('DELETE','/api/v1/messages',json={'IDs':ids})
                assert response.status_code==200
