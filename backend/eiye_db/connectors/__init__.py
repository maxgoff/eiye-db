"""Connector factory."""

from eiye_db.connectors.base import Connector, ConnectorError
from eiye_db.models import DataSourceType

__all__ = ["Connector", "ConnectorError", "get_connector"]


def get_connector(type: DataSourceType, config: dict) -> Connector:
    if type == DataSourceType.POSTGRESQL:
        from eiye_db.connectors.postgres import PostgresConnector

        return PostgresConnector(config)
    if type == DataSourceType.FILE_SYSTEM:
        from eiye_db.connectors.filesystem import FilesystemConnector

        return FilesystemConnector(config)
    if type == DataSourceType.REST_API:
        from eiye_db.connectors.rest import RestConnector

        return RestConnector(config)
    raise ConnectorError(f"no connector implemented for type '{type}'")
