import logging
from typing import Optional, List
import traceback
from typing import Dict, Tuple, Any
from prometheus.couters import instance_id, count_instance_errors

log = logging.getLogger(__name__)


class SQLQueryBuilder:
    def __init__(self, table_name: str):
        self.table_name = table_name
        self.sql = ""
        self.args = []

    def select(self, fields: Optional[List[str]] = None) -> 'SQLQueryBuilder':
        if fields:
            fields = ", ".join([f"{x}" for x in fields])
        else:
            fields = "*"
        self.sql = f"SELECT {fields} FROM {self.table_name}"
        return self

    def delete(self) -> 'SQLQueryBuilder':
        self.sql = f"DELETE FROM {self.table_name}"
        return self

    def where(self, conditions: Dict[str, Tuple[str, Any]]) -> 'SQLQueryBuilder':
        where_clause = " AND ".join(
            [f"{key} {op} ${i + len(self.args) + 1}" for i, (key, (op, _)) in enumerate(conditions.items())]
        )
        self.sql = f"{self.sql} WHERE {where_clause}"
        self.args.extend([value for _, (_, value) in conditions.items()])
        return self

    def limit(self, limit: int) -> 'SQLQueryBuilder':
        new_args = self.args + [limit]
        self.sql = f"{self.sql} LIMIT ${len(new_args)}"
        self.args = new_args
        return self

    def order_by(self, column_name: str, sort_order: str) -> 'SQLQueryBuilder':
        self.sql = f"{self.sql} ORDER BY {column_name} {sort_order}"
        return self

    def group_by(self, columns: List[str]) -> 'SQLQueryBuilder':
        group_by_clause = ", ".join(columns)
        self.sql = f"{self.sql} GROUP BY {group_by_clause}"
        return self

    def update(self, fields: Dict[str, Any]) -> 'SQLQueryBuilder':
        set_clause = ", ".join([f"{key} = ${i + 1}" for i, key in enumerate(fields)])
        self.sql = f"UPDATE {self.table_name} SET {set_clause}"
        self.args = list(fields.values())
        return self

    def insert(self, fields: Dict[str, Any], on_conflict: Optional[str] = None,
               update_fields: Optional[List[str]] = None) -> 'SQLQueryBuilder':
        columns = ", ".join(fields.keys())
        placeholders = ', '.join([f"${i + 1}" for i in range(len(fields))])
        sql = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders})"
        if on_conflict:
            if update_fields:
                conflict_update = ", ".join(
                    [f"{col} = EXCLUDED.{col}" for col in update_fields]
                )
                sql += f" ON CONFLICT ({on_conflict}) DO UPDATE SET {conflict_update}"
            else:
                sql += f" ON CONFLICT ({on_conflict}) DO NOTHING"
        self.args = list(fields.values())
        self.sql = sql
        return self

    def build(self) -> Tuple[str, List[Any]]:
        try:
            return self.sql, self.args
        except Exception as e:
            count_instance_errors.labels(instance=instance_id).inc()
            log.error("An error occurred: %s", str(e))
            log.debug(f"Exception traceback:\n{traceback.format_exc()}")
