"""Controlled faults for backend acceptance tests. Requires a disposable test database."""
from contextlib import asynccontextmanager
from pathlib import Path
import tempfile
import time
import os

from sqlalchemy.engine import make_url

from api.app import app
from api.rag_admission import shutdown_admission
from api.rag_runtime import STATE
from api.settings import ROOT,get_settings
from tests.test_rag import _two_school_pipe


@asynccontextmanager
async def controlled_lifespan(app):
    settings=get_settings()
    if settings.app_env!='test' or not (make_url(settings.database_url).database or '').startswith('university_b7_'):
        raise RuntimeError('Controlled B7 app is restricted to disposable test databases')
    temp_root=Path(os.environ['B7_TEMP_ROOT']).resolve()
    if not temp_root.is_relative_to((ROOT/'var/verification').resolve()):
        raise RuntimeError('Controlled corpus must stay in the private verification workspace')
    with tempfile.TemporaryDirectory(prefix='corpus-',dir=temp_root) as directory:
        pipe=_two_school_pipe(Path(directory),lambda system,prompt:{
            'can_answer':True,'answer':'Dưới 3,0.',
            'citations':[{'source':'C1','quote':'điểm trung bình học kỳ dưới 3,0'}]})
        original=pipe.answer

        def delayed(question,institution=None):
            time.sleep(1.2 if question.startswith('B7 timeout') else .4)
            return original(question,institution=institution)

        pipe.answer=delayed
        STATE['pipe']=pipe
        try:
            yield
        finally:
            shutdown_admission()
            STATE.clear()


app.router.lifespan_context=controlled_lifespan
