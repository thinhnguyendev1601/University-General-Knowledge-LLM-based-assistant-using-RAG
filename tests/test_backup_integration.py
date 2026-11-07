"""Real pg_dump/pg_restore, in disposable databases only. Opt in with BACKUP_TESTS=1."""
from dataclasses import replace
from datetime import timedelta
import json
import os
import shutil
import uuid

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from api.auth_security import password_hasher
from api.models import AccountToken, Conversation, Document, DocumentAudit, DocumentVersion, LoginSession, Message, User, utcnow
from api.settings import ROOT, get_settings
from scripts.backup_backend import BACKUPS, RESTORES, create_backup, restore_backup, verify_backup, checksum
from scripts.import_document_metadata import import_manifest
from scripts.verification_support import temporary_database, drop_test_database

pytestmark = pytest.mark.skipif(not os.getenv('BACKUP_TESTS'),reason='Opt-in local Docker pg_dump/restore drill')


def test_backup_restore_preserves_content_versions_and_revokes_old_credentials(tmp_path):
    settings=get_settings()
    target='university_restore_'+uuid.uuid4().hex
    name='b7-backup-'+uuid.uuid4().hex
    output=BACKUPS/name
    restored=RESTORES/target
    try:
        with temporary_database(settings.database_url) as url:
            source=create_engine(url,hide_parameters=True)
            try:
                with Session(source) as db,db.begin():
                    import_manifest(db,ROOT/'data/manifest.csv')
                    user=User(email='restore@university.edu.vn',name='Preserved',password_hash=password_hasher.hash('a restore verification password'))
                    db.add(user); db.flush()
                    conversation=Conversation(user_id=user.id,title='Preserved conversation')
                    db.add(conversation); db.flush()
                    citations=[{'docId':'uit-acad-reg-2022','chunkId':'uit-acad-reg-2022:1:20','quote':'Original verified quote'}]
                    db.add(Message(conversation_id=conversation.id,role='assistant',content='Original answer',sequence=1,
                                   citations=citations,status='answered'))
                    db.add(LoginSession(id='s'*64,user_id=user.id,csrf_token='c',expires_at=utcnow()+timedelta(hours=1)))
                    db.add(AccountToken(user_id=user.id,token_hash='t'*64,purpose='reset',expires_at=utcnow()+timedelta(hours=1)))
                created=create_backup(name,replace(settings,database_url=url))
                assert created['status']=='created'
                metadata=verify_backup(output)
                assert metadata['schemaRevision']=='a76d18b4c902'
                result=restore_backup(name,target,replace(settings,database_url=url))
                assert result['status']=='restored_to_quarantine'
                from sqlalchemy.engine import make_url
                restored_engine=create_engine(make_url(url).set(database=target),hide_parameters=True)
                try:
                    with Session(restored_engine) as db:
                        restored_user=db.scalar(select(User))
                        assert restored_user.name=='Preserved'
                        password_hasher.verify(restored_user.password_hash,'a restore verification password')
                        assert db.scalar(select(Conversation)).title=='Preserved conversation'
                        answer=db.scalar(select(Message))
                        assert answer.content=='Original answer' and answer.citations==citations
                        assert db.scalar(select(func.count()).select_from(Document))==21
                        assert db.scalar(select(func.count()).select_from(DocumentVersion))==21
                        assert db.scalar(select(func.count()).select_from(DocumentAudit))==21
                        assert db.scalar(select(func.count()).select_from(LoginSession))==0
                        assert db.scalar(select(AccountToken)).consumed_at is not None
                    for relative,info in metadata['files'].items():
                        if relative.startswith('data/'):
                            assert checksum(restored/relative)==info['sha256']
                    # Refuse a second restore into an existing directory/database.
                    with pytest.raises(ValueError,match='already exists'):
                        restore_backup(name,target,replace(settings,database_url=url))
                finally:
                    restored_engine.dispose()
            finally:
                source.dispose()
    finally:
        drop_test_database(settings.database_url,target)
        for path,parent in ((output,BACKUPS),(restored,RESTORES)):
            if path.exists():
                assert path.resolve().parent==parent.resolve() and path.resolve().is_relative_to((ROOT/'var').resolve())
                shutil.rmtree(path)
