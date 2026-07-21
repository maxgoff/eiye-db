export type DataSourceType = "filesystem" | "postgresql" | "rest_api";

export interface DataSource {
  id: string;
  name: string;
  type: DataSourceType;
  status: string;
  config: Record<string, unknown>;
  description: string;
  tags: string[];
  pii_risk_level: string;
  created_at: string;
  updated_at: string;
  last_connected: string | null;
}

export interface SchemaField {
  name: string;
  type: string;
}

export interface SchemaTable {
  name: string;
  fields: SchemaField[];
}

export interface Schema {
  datasource_id: string;
  tables: SchemaTable[];
  discovered_at: string;
}

export interface QueryResponse {
  datasource_id: string;
  rows: Record<string, unknown>[];
  row_count: number;
  pii_filtered: boolean;
  pii_counts: Record<string, number>;
  execution_time_ms: number;
}

export const TYPE_LABELS: Record<DataSourceType, string> = {
  filesystem: "Filesystem",
  postgresql: "PostgreSQL",
  rest_api: "REST API",
};
