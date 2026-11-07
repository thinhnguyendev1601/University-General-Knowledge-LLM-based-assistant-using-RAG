"""Bounded local HTTP acceptance/load run; every run owns a new disposable database."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import timedelta,datetime,timezone
import argparse
from collections import Counter
import json
import math
import os
from pathlib import Path
import socket
import subprocess
import sys
import threading
import tempfile
import time
import uuid

import httpx
import psutil
from fastapi import HTTPException
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from api.chat_schemas import SendMessage
from api.chat_storage import complete_generation,start_generation
from api.models import Conversation,Document,User,utcnow
from api.settings import ROOT,get_settings
from scripts.import_document_metadata import import_manifest
from scripts.seed_demo_accounts import seed_demo_accounts
from scripts.verification_support import temporary_database

QUESTION='Ở UIT khi nào bị cảnh báo học tập?'


class Server:
    def __init__(self,url,live):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0)); self.port=sock.getsockname()[1]
        self.base=f'http://127.0.0.1:{self.port}'
        self.origin=f'http://localhost:{self.port}'
        work_parent=ROOT/'var/verification'
        work_parent.mkdir(parents=True,exist_ok=True)
        self.workspace=tempfile.TemporaryDirectory(prefix='b7-',dir=work_parent)
        self.env={**os.environ,'DATABASE_URL':url,'APP_ENV':'test','FRONTEND_URL':self.origin,
                  'RAG_ENABLED':'true','PYTHONDONTWRITEBYTECODE':'1','B7_TEMP_ROOT':self.workspace.name}
        if not live:
            self.env.update(CHAT_QUEUE_TIMEOUT_SECONDS='0.15',CHAT_PROCESSING_TIMEOUT_SECONDS='0.8',CHAT_MAX_WAITING='2')
        self.module='api.app:app' if live else 'scripts.controlled_test_app:app'
        self.process=None

    def start(self):
        self.process=subprocess.Popen([sys.executable,'-B','-m','uvicorn',self.module,'--host','127.0.0.1',
            '--port',str(self.port),'--log-level','warning'],cwd=ROOT,env=self.env,
            stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
        until=time.monotonic()+120
        with httpx.Client(base_url=self.base,timeout=5) as client:
            while time.monotonic()<until:
                if self.process.poll() is not None:
                    raise RuntimeError('Verification API exited during startup')
                try:
                    if client.get('/api/health/ready').status_code==200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(.2)
        raise RuntimeError('Verification API did not become ready')

    def stop(self):
        if self.process is None or self.process.poll() is not None:return
        try:
            children=psutil.Process(self.process.pid).children(recursive=True)
        except psutil.Error:children=[]
        for child in reversed(children):
            try:child.terminate()
            except psutil.Error:pass
        self.process.terminate()
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
        _,alive=psutil.wait_procs(children,timeout=2)
        for child in alive:
            try:child.kill()
            except psutil.Error:pass

    def client(self):
        return httpx.Client(base_url=self.base,timeout=240,headers={'Origin':self.origin,'X-Requested-With':'XMLHttpRequest'})

    def close(self):
        self.stop()
        path=Path(self.workspace.name)
        if (path.is_symlink() or path.resolve().parent!=(ROOT/'var/verification').resolve()
                or not path.name.startswith('b7-') or not path.resolve().is_relative_to((ROOT/'var').resolve())):
            raise ValueError('Unsafe verification workspace cleanup path')
        self.workspace.cleanup()


class Resources:
    def __init__(self,pid):
        self.pid=pid;self.stop_event=threading.Event();self.samples=[]
        self.thread=threading.Thread(target=self.sample,daemon=True)

    def sample(self):
        while not self.stop_event.is_set():
            try:
                parent=psutil.Process(self.pid)
                processes=[parent,*parent.children(recursive=True)]
                rss=cpu=0
                for process in processes:
                    try:
                        rss+=process.memory_info().rss
                        times=process.cpu_times();cpu+=times.user+times.system
                    except psutil.Error:pass
                self.samples.append((time.monotonic(),rss,cpu))
            except psutil.Error:pass
            self.stop_event.wait(.1)

    def __enter__(self):self.thread.start();return self
    def __exit__(self,*args):self.stop_event.set();self.thread.join(timeout=2)

    def result(self):
        if not self.samples:return {'sampleCount':0}
        duration=self.samples[-1][0]-self.samples[0][0]
        cpu=max(sample[2] for sample in self.samples)-self.samples[0][2]
        return {'sampleCount':len(self.samples),'apiPeakRssMiB':round(max(s[1] for s in self.samples)/1048576,2),
                'apiCpuSeconds':round(max(0,cpu),3),'apiCpuPercentOfOneCore':round(100*max(0,cpu)/max(duration,.001),2),
                'externalOllamaIncluded':False}


def login(client,email,password):
    response=client.post('/api/auth/login',json={'email':email,'password':password})
    assert response.status_code==200
    client.headers['X-CSRF-Token']=response.json()['csrfToken']


def create(client):
    response=client.post('/api/chat/conversations',json={})
    assert response.status_code==201
    return response.json()['id']


def wave(server,user,count,allowed):
    ids=[create(user) for _ in range(count)]
    barrier=threading.Barrier(count)
    def ask(conversation):
        with server.client() as client:
            client.cookies.update(user.cookies)
            client.headers['X-CSRF-Token']=user.headers['X-CSRF-Token']
            request_id=str(uuid.uuid4())
            barrier.wait(timeout=10)
            started=time.monotonic()
            response=client.post('/api/chat/messages',json={'conversationId':conversation,'content':QUESTION,
                                                          'requestId':request_id,'institutionId':'uit'})
            elapsed=(time.monotonic()-started)*1000
            assert response.status_code in {200,503}
            saved=client.get(f'/api/chat/conversations/{conversation}/messages').json()
            assert sum(item['role']=='user' for item in saved)==1
            if response.status_code==200:
                data=response.json()
                assert data['status']=='answered' and data['citations']
                assert {item['docId'] for item in data['citations']}<=allowed
                assert len(saved)==2
                replay=client.post('/api/chat/messages',json={'conversationId':conversation,'content':QUESTION,
                                                            'requestId':request_id,'institutionId':'uit'})
                assert replay.status_code==200 and replay.json()['id']==data['id']
            else:
                assert response.headers['Retry-After']=='5'
                assert saved[0]['deliveryStatus']=='failed' and saved[0]['errorCode']=='rag_busy'
            return {'status':response.status_code,'elapsedMs':round(elapsed,2),'conversation':conversation,'saved':saved}
    with Resources(server.process.pid) as resources,ThreadPoolExecutor(max_workers=count) as pool:
        futures=[pool.submit(ask,id) for id in ids]
        observed_pending=False
        until=time.monotonic()+5
        while time.monotonic()<until and not all(future.done() for future in futures):
            for conversation in ids:
                saved=user.get(f'/api/chat/conversations/{conversation}/messages').json()
                if any(item['deliveryStatus']=='pending' for item in saved):
                    observed_pending=True
                    break
            if observed_pending:break
            time.sleep(.01)
        started=time.monotonic()
        read=user.get('/api/chat/conversations')
        read_ms=(time.monotonic()-started)*1000
        assert read.status_code==200 and read_ms<5000
        results=[future.result(timeout=240) for future in futures]
    durations=sorted(item['elapsedMs'] for item in results)
    summary={'concurrentRequests':count,'statuses':dict(Counter(str(item['status']) for item in results)),
        'latencyMs':{'p50':durations[len(durations)//2],'p95':durations[math.ceil(len(durations)*.95)-1],'max':max(durations)},
        'historyReadMs':round(read_ms,2),'historyReadWhilePendingObserved':observed_pending,'resources':resources.result()}
    summary['latencyByStatusMs']={}
    for status in sorted({item['status'] for item in results}):
        values=sorted(item['elapsedMs'] for item in results if item['status']==status)
        summary['latencyByStatusMs'][str(status)]={'count':len(values),'min':min(values),
            'p50':values[len(values)//2],'p95':values[math.ceil(len(values)*.95)-1],'max':max(values)}
    return summary,results


def run(live=False):
    settings=get_settings()
    with temporary_database(settings.database_url) as url:
        engine=create_engine(url,hide_parameters=True)
        server=Server(url,live)
        try:
            with Session(engine) as db,db.begin():
                seed_demo_accounts(db,replace(settings,database_url=url,app_env='development'))
                import_manifest(db,ROOT/'data/manifest.csv')
                allowed=set(db.scalars(select(Document.legacy_doc_id).where(Document.corpus_role=='indexed')))
            if not live:allowed={'uit-reg','iu-reg'}
            server.start()
            with server.client() as user,server.client() as admin,server.client() as outsider:
                login(user,'user@university.edu.vn','user-demo-local-2026')
                login(admin,'admin@university.edu.vn','admin-demo-local-2026')
                assert outsider.get('/api/admin/documents').status_code==401
                assert user.get('/api/admin/documents').status_code==403
                assert len(admin.get('/api/admin/documents').json())==21
                unknown='other-'+uuid.uuid4().hex[:10]+'@university.edu.vn'
                assert outsider.post('/api/auth/register',json={'name':'Other test user','email':unknown,'password':'B7 verification password'}).status_code==201
                login(outsider,unknown,'B7 verification password')
                summaries=[];successful=None
                for count in (1,3,6):
                    summary,results=wave(server,user,count,allowed)
                    if count==6:
                        assert any(item['status']==503 for item in results), 'Run did not saturate the bounded queue'
                    summaries.append(summary)
                    successful=next((item for item in results if item['status']==200),successful)
                    print(json.dumps({'wave':summary}),flush=True)
                assert successful is not None
                target=successful['conversation']
                for other in (outsider,admin):
                    assert other.get(f'/api/chat/conversations/{target}').status_code==404
                    assert other.get(f'/api/chat/conversations/{target}/messages').status_code==404
                    assert other.patch(f'/api/chat/conversations/{target}',json={'title':'Forbidden'}).status_code==404
                    assert other.delete(f'/api/chat/conversations/{target}').status_code==404
                    assert other.post('/api/chat/messages',json={'conversationId':target,'content':QUESTION}).status_code==404
                login(user,'user@university.edu.vn','user-demo-local-2026')
                assert user.get(f'/api/chat/conversations/{target}/messages').json()==successful['saved']
                if not live:
                    timeout_chat=create(user);request_id=str(uuid.uuid4())
                    body={'conversationId':timeout_chat,'content':'B7 timeout '+QUESTION,'requestId':request_id,'institutionId':'uit'}
                    assert user.post('/api/chat/messages',json=body).status_code==504
                    assert user.post('/api/chat/messages',json=body).status_code==503
                    time.sleep(.4)
                    assert len(user.get(f'/api/chat/conversations/{timeout_chat}/messages').json())==1
                pending=create(user)
                body=SendMessage(conversationId=pending,content=QUESTION,requestId=uuid.uuid4(),institutionId='uit')
                with Session(engine) as db:
                    owner=db.get(Conversation,pending).user_id
                    old=start_generation(db,owner,body,900)
                assert user.post('/api/chat/messages',json=body.model_dump(mode='json')).status_code==409
                server.stop()
                with Session(engine) as db,db.begin():
                    db.get(Conversation,pending).generation_started_at=utcnow()-timedelta(seconds=901)
                server.start()
                assert user.get(f'/api/chat/conversations/{target}/messages').json()==successful['saved']
                assert user.post('/api/chat/messages',json=body.model_dump(mode='json')).status_code==200
                with Session(engine) as db:
                    try:complete_generation(db,old,{})
                    except HTTPException as error:assert error.status_code==409
                    else:raise AssertionError('Stale completion was accepted')
            return {'result':'PASS','date':datetime.now(timezone.utc).isoformat(),'mode':'live_ollama' if live else 'controlled_pipeline',
                'waves':summaries,'crossOwnershipChecks':10,'historyAfterNewLogin':True,'restartRecovery':True,
                'recoveryLeaseAdvancedForTest':True,'lateCompletionRejected':True,'timeoutContainment':True if not live else None,
                'corpusIsolation':'real_indexed_only' if live else 'controlled_fixture_only','productionCapacityClaim':False}
        finally:
            server.close();engine.dispose()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--live',action='store_true')
    parser.add_argument('--name',required=True)
    args=parser.parse_args()
    if not all(c.isalnum() or c in '-_' for c in args.name) or not args.name:
        parser.error('Use a simple receipt name')
    output=ROOT/'docs/verification'/(args.name+'.json')
    if output.exists():parser.error('Receipt already exists; use a new name')
    try:
        result=run(args.live)
    except Exception as error:
        result={'result':'FAIL','mode':'live_ollama' if args.live else 'controlled_pipeline','errorType':type(error).__name__}
        output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        raise
    result['disposableDatabaseRemoved']=True
    result['disposableWorkDirectoryRemoved']=True
    output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'result':result['result'],'receipt':output.name}))


if __name__=='__main__':main()
