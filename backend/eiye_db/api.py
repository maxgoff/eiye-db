"""REST API routes."""

from fastapi import APIRouter, Depends, HTTPException

from eiye_db import audit, registry, service
from eiye_db.connectors import ConnectorError
from eiye_db.models import DataSource, DataSourceCreate, DataSourceUpdate, SourceQueryRequest, SourceQueryResponse
from eiye_db.security import Identity, require_api_key

router = APIRouter(prefix="/api/v1")


@router.post("/datasources", response_model=DataSource, status_code=201)
def create_datasource(req: DataSourceCreate, identity: Identity = Depends(require_api_key)):
    try:
        ds = registry.create(req)
    except ValueError as e:
        raise HTTPException(409, str(e))
    audit.record("create", "datasource", ds.id, identity.key_id, ds.id)
    return ds


@router.get("/datasources", response_model=list[DataSource])
def list_datasources(identity: Identity = Depends(require_api_key)):
    return registry.list_all()


@router.get("/datasources/{datasource_id}", response_model=DataSource)
def get_datasource(datasource_id: str, identity: Identity = Depends(require_api_key)):
    ds = registry.get(datasource_id)
    if ds is None:
        raise HTTPException(404, "datasource not found")
    return ds


@router.put("/datasources/{datasource_id}", response_model=DataSource)
def update_datasource(datasource_id: str, req: DataSourceUpdate, identity: Identity = Depends(require_api_key)):
    ds = registry.update(datasource_id, req)
    if ds is None:
        raise HTTPException(404, "datasource not found")
    audit.record("update", "datasource", datasource_id, identity.key_id, datasource_id)
    return ds


@router.delete("/datasources/{datasource_id}", status_code=204)
def delete_datasource(datasource_id: str, identity: Identity = Depends(require_api_key)):
    if not registry.delete(datasource_id):
        raise HTTPException(404, "datasource not found")
    audit.record("delete", "datasource", datasource_id, identity.key_id, datasource_id)


@router.post("/datasources/{datasource_id}/test", response_model=DataSource)
async def test_datasource(datasource_id: str, identity: Identity = Depends(require_api_key)):
    try:
        return await service.test_connection(datasource_id, identity.key_id)
    except service.NotFoundError:
        raise HTTPException(404, "datasource not found")
    except ConnectorError as e:
        raise HTTPException(502, str(e))


@router.post("/datasources/{datasource_id}/discover")
async def discover_datasource(datasource_id: str, identity: Identity = Depends(require_api_key)):
    try:
        return await service.discover_schema(datasource_id, identity.key_id)
    except service.NotFoundError:
        raise HTTPException(404, "datasource not found")
    except ConnectorError as e:
        raise HTTPException(502, str(e))


@router.get("/surface/sources")
def surface_sources(identity: Identity = Depends(require_api_key)):
    sources = []
    for ds in registry.list_all():
        schema = registry.get_schema(ds.id)
        sources.append(
            {
                "id": ds.id,
                "name": ds.name,
                "type": ds.type,
                "status": ds.status,
                "description": ds.description,
                "tables": len(schema["tables"]) if schema else None,
            }
        )
    return sources


@router.get("/surface/schema/{datasource_id}")
def surface_schema(datasource_id: str, identity: Identity = Depends(require_api_key)):
    if registry.get(datasource_id) is None:
        raise HTTPException(404, "datasource not found")
    schema = registry.get_schema(datasource_id)
    if schema is None:
        raise HTTPException(404, "no schema discovered yet; POST /datasources/{id}/discover first")
    return schema


@router.post("/query", response_model=SourceQueryResponse)
async def query(req: SourceQueryRequest, identity: Identity = Depends(require_api_key)):
    if req.include_pii and not identity.is_admin:
        raise HTTPException(403, "include_pii requires the admin API key")
    try:
        return await service.run_query(
            req.datasource_id, req.request, req.limit, identity.key_id, include_pii=req.include_pii
        )
    except service.NotFoundError:
        raise HTTPException(404, "datasource not found")
    except ConnectorError as e:
        raise HTTPException(502, str(e))
    except TimeoutError:
        raise HTTPException(504, "query timed out")


@router.get("/audit")
def audit_log(limit: int = 100, identity: Identity = Depends(require_api_key)):
    if not identity.is_admin:
        raise HTTPException(403, "audit log requires the admin API key")
    return audit.recent(min(limit, 1000))
