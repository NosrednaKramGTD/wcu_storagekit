class StorageKitError(Exception):
    """Base error."""


class ConfigError(StorageKitError):
    """Config missing/invalid."""


class UnknownProvider(StorageKitError):
    """Provider alias not found in config."""


class InvalidURI(StorageKitError):
    """URI missing provider:// prefix."""
