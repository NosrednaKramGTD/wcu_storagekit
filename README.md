# storagekit

A small, config-driven storage wrapper built on **fsspec**. The goal is to be able to pass around storage locations and change them out as needed without impacting the application. For example s4s_file can point to a local direcitory today, an s3 server tomorrow and a sftp server next week. The only change needed would bit in hte `storagekit.yaml` file. This is to make it easier to store files safe and security, expecially with the increases desire to have files in could services. Below covers the basic design. 

- Your app always uses **explicit provider aliases** like `primary://path/to/file`.
- A YAML config maps each provider alias to a backend `base_uri` like `s3://bucket/prefix`, `sftp://user@host/path`, or `file:///data`.
- Adding new backends later is usually: install a plugin package + add a provider stanza.

## Install

Base:

```bash
uv add git+https://github.com/NosrednaKramGTD/wcu_storagekit.git
```

With optional backends:

```bash
uv add git+https://github.com/NosrednaKramGTD/wcu_storagekit.git[s3]
uv add git+https://github.com/NosrednaKramGTD/wcu_storagekit.git[sftp]
uv add git+https://github.com/NosrednaKramGTD/wcu_storagekit.git[azure]
```

## Configure

Create a YAML file (example: `example_storagekit.yaml`) and set:

```bash
export STORAGEKIT_CONFIG=/etc/storagekit.yaml
```

## Usage

```python
from storagekit import StorageClient

sc = StorageClient.from_env()  # reads STORAGEKIT_CONFIG

sc.upload("/tmp/a.bin", "s3main://uploads/a.bin")
sc.download("s3main://uploads/a.bin", "/tmp/a.bin")

with sc.open("local://reports/today.csv", "wb") as f:
    f.write(b"hello\n")

sc.copy("s3main://uploads/a.bin", "sftpdrop://incoming/a.bin")
```

## Notes

- URIs **must** include a provider alias (`provider://...`).
- Environment substitution uses `${VARNAME}` patterns in YAML. Missing variables fail fast at startup.
