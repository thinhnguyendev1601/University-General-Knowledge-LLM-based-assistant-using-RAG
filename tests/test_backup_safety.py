import json
from pathlib import Path

import pytest

from scripts.backup_backend import checksum, private_path, verify_backup, BACKUPS, RESTORE_DATABASE


def bundle(tmp_path):
    (tmp_path/'data').mkdir()
    (tmp_path/'data/manifest.csv').write_text('test corpus',encoding='utf-8')
    (tmp_path/'database.dump').write_bytes(b'PGDMP-test-data')
    metadata={'formatVersion':1,'files':{name:{'sha256':checksum(tmp_path/name),'bytes':(tmp_path/name).stat().st_size}
        for name in ['database.dump','data/manifest.csv']}}
    (tmp_path/'bundle.json').write_text(json.dumps(metadata),encoding='utf-8')
    return metadata


def test_bundle_requires_exact_inventory_and_checksums(tmp_path):
    original=bundle(tmp_path)
    assert verify_backup(tmp_path) == original
    (tmp_path/'database.dump').write_bytes(b'changed')
    with pytest.raises(ValueError,match='checksum'):
        verify_backup(tmp_path)


def test_unlisted_files_are_rejected(tmp_path):
    bundle(tmp_path)
    (tmp_path/'unexpected').write_text('not listed')
    with pytest.raises(ValueError,match='inventory'):
        verify_backup(tmp_path)


@pytest.mark.parametrize('name',['../data','..','/absolute','C:\\backup','name/subfolder',''])
def test_backup_names_cannot_target_other_directories(name):
    with pytest.raises(ValueError):
        private_path(BACKUPS,name)


@pytest.mark.parametrize('name',['university','postgres','university_restore_','other_database','university_restore_x;DROP'])
def test_restore_target_cannot_be_a_live_database_or_sql(name):
    assert not RESTORE_DATABASE.fullmatch(name)


def test_verification_workspace_is_cleaned_without_leaving_child_process_files():
    from scripts.verify_backend import Server
    server=Server('postgresql+psycopg://unused:unused@127.0.0.1/unused',False)
    directory=Path(server.workspace.name)
    (directory/'partial-child-corpus').mkdir()
    (directory/'partial-child-corpus/file.txt').write_text('controlled fixture')
    server.close()
    assert not directory.exists()
