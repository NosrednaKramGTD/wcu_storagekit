import pytest

from wcu_storagekit.client import StorageClient
from wcu_storagekit.config import StorageConfig, ProviderConfig
from wcu_storagekit.errors import InvalidURI, UnknownProvider


def make_client(tmp_path):
    cfg = StorageConfig(providers={
        'mem': ProviderConfig(base_uri='memory://bucket', options={}),
        'local': ProviderConfig(base_uri=f'file://{tmp_path}', options={}),
    })
    return StorageClient(cfg)


def test_requires_provider_prefix(tmp_path):
    sc = make_client(tmp_path)
    with pytest.raises(InvalidURI):
        sc.exists('no-prefix-here')


def test_unknown_provider(tmp_path):
    sc = make_client(tmp_path)
    with pytest.raises(UnknownProvider):
        sc.exists('nope://x')


def test_open_write_read_memory(tmp_path):
    sc = make_client(tmp_path)
    with sc.open('mem://a.txt', 'wb') as f:
        f.write(b'hello')
    with sc.open('mem://a.txt', 'rb') as f:
        assert f.read() == b'hello'


def test_copy_cross_backend_stream(tmp_path):
    sc = make_client(tmp_path)
    with sc.open('mem://src.bin', 'wb') as f:
        f.write(b'xyz' * 1000)
    sc.copy('mem://src.bin', 'local://dst.bin')
    with sc.open('local://dst.bin', 'rb') as f:
        data = f.read()
    assert data == b'xyz' * 1000


def test_ls_and_rm(tmp_path):
    sc = make_client(tmp_path)
    with sc.open('local://a/one.txt', 'wb') as f:
        f.write(b'1')
    sc.makedirs('local://a', exist_ok=True)
    listed = sc.ls('local://a', detail=False)
    assert any('one.txt' in x for x in listed)
    sc.rm('local://a/one.txt')
    assert not sc.exists('local://a/one.txt')
