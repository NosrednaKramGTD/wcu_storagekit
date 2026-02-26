import textwrap
import pytest

from wcu_storagekit.config import load_from_yaml_path
from wcu_storagekit.errors import ConfigError


def test_env_substitution_success(tmp_path, monkeypatch):
    monkeypatch.setenv('SFTP_KEYFILE', '/home/app/.ssh/id_ed25519')
    cfg_text = textwrap.dedent('''
    storage:
      env_substitution: true
      providers:
        sftpdrop:
          base_uri: "sftp://user@host:22/incoming"
          options:
            key_filename: "${SFTP_KEYFILE}"
    ''').lstrip()
    p = tmp_path / 'cfg.yaml'
    p.write_text(cfg_text)
    cfg = load_from_yaml_path(str(p))
    assert cfg.providers['sftpdrop'].options['key_filename'] == '/home/app/.ssh/id_ed25519'


def test_env_substitution_missing_var_fails(tmp_path):
    cfg_text = textwrap.dedent('''
    storage:
      env_substitution: true
      providers:
        x:
          base_uri: "file:///tmp"
          options:
            password: "${MISSING_VAR}"
    ''').lstrip()
    p = tmp_path / 'cfg.yaml'
    p.write_text(cfg_text)
    with pytest.raises(ConfigError):
        load_from_yaml_path(str(p))


def test_env_substitution_can_be_disabled(tmp_path):
    cfg_text = textwrap.dedent('''
    storage:
      env_substitution: false
      providers:
        x:
          base_uri: "file:///tmp"
          options:
            password: "${LITERAL}"
    ''').lstrip()
    p = tmp_path / 'cfg.yaml'
    p.write_text(cfg_text)
    cfg = load_from_yaml_path(str(p))
    assert cfg.providers['x'].options['password'] == '${LITERAL}'
