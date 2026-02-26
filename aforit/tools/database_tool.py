"""Database tool - interact with SQLite and other databases."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from aforit.tools.base import BaseTool, ToolResult


class DatabaseTool(BaseTool):
    """Execute SQL queries against SQLite databases."""

    name = "database"
    description = (
        "Interact with SQLite databases. Supports query, execute, schema "
        "inspection, table listing, and data export."
    )
    parameters = {
        "action": {
            "type": "string",
            "enum": ["query", "execute", "tables", "schema", "export", "create"],
            "description": "Database operation to perform",
        },
        "db_path": {
            "type": "string",
            "description": "Path to the SQLite database file",
        },
        "sql": {
            "type": "string",
            "description": "SQL query or statement to execute",
        },
        "table": {
            "type": "string",
            "description": "Table name (for schema/export actions)",
        },
        "format": {
            "type": "string",
            "enum": ["table", "json", "csv"],
            "description": "Output format (default: table)",
        },
    }
    required_params = ["action", "db_path"]
    timeout = 30.0

    # SQL patterns that are blocked for safety
    BLOCKED_PATTERNS = [
        "DROP DATABASE",
        "DROP TABLE IF EXISTS sqlite_",
        "ATTACH DATABASE",
        "DETACH DATABASE",
    ]

    async def execute(
        self,
        action: str,
        db_path: str,
        sql: str = "",
        table: str = "",
        format: str = "table",
        **kwargs,
    ) -> ToolResult:
        """Execute a database operation."""
        handlers = {
            "query": self._query,
            "execute": self._execute,
            "tables": self._list_tables,
            "schema": self._get_schema,
            "export": self._export,
            "create": self._create_db,
        }

        handler = handlers.get(action)
        if not handler:
            return ToolResult(success=False, output="", error=f"Unknown action: {action}")

        try:
            return await handler(db_path=db_path, sql=sql, table=table, format=format)
        except sqlite3.Error as e:
            return ToolResult(success=False, output="", error=f"SQLite error: {str(e)}")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    def _check_sql_safety(self, sql: str) -> str | None:
        """Check if SQL is safe to execute."""
        sql_upper = sql.upper().strip()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in sql_upper:
                return f"Blocked SQL pattern: {pattern}"
        return None

    async def _query(self, db_path: str, sql: str, format: str = "table", **kw) -> ToolResult:
        """Execute a SELECT query and return results."""
        if not sql:
            return ToolResult(success=False, output="", error="SQL query required")

        safety = self._check_sql_safety(sql)
        if safety:
            return ToolResult(success=False, output="", error=safety)

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(sql)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            if format == "json":
                data = [dict(row) for row in rows]
                output = json.dumps(data, indent=2, default=str)
            elif format == "csv":
                lines = [",".join(columns)]
                for row in rows:
                    lines.append(",".join(str(v) for v in row))
                output = "\n".join(lines)
            else:
                output = self._format_table(columns, [tuple(row) for row in rows])

            return ToolResult(
                success=True,
                output=output,
                metadata={"rows": len(rows), "columns": columns},
            )
        finally:
            conn.close()

    async def _execute(self, db_path: str, sql: str, **kw) -> ToolResult:
        """Execute a non-SELECT SQL statement."""
        if not sql:
            return ToolResult(success=False, output="", error="SQL statement required")

        safety = self._check_sql_safety(sql)
        if safety:
            return ToolResult(success=False, output="", error=safety)

        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(sql)
            conn.commit()
            return ToolResult(
                success=True,
                output=f"Executed successfully. Rows affected: {cursor.rowcount}",
                metadata={"rows_affected": cursor.rowcount},
            )
        finally:
            conn.close()

    async def _list_tables(self, db_path: str, **kw) -> ToolResult:
        """List all tables in the database."""
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.execute(
                "SELECT name, type FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY name"
            )
            results = cursor.fetchall()
            output = "\n".join(f"[{t}] {name}" for name, t in results)
            return ToolResult(
                success=True,
                output=output or "No tables found.",
                metadata={"count": len(results)},
            )
        finally:
            conn.close()

    async def _get_schema(self, db_path: str, table: str = "", **kw) -> ToolResult:
        """Get the schema of a table or the entire database."""
        conn = sqlite3.connect(db_path)
        try:
            if table:
                cursor = conn.execute(f"PRAGMA table_info({table})")
                columns = cursor.fetchall()
                lines = [f"Table: {table}\n"]
                for col in columns:
                    cid, name, ctype, notnull, default, pk = col
                    flags = []
                    if pk:
                        flags.append("PRIMARY KEY")
                    if notnull:
                        flags.append("NOT NULL")
                    if default is not None:
                        flags.append(f"DEFAULT {default}")
                    flag_str = f" ({', '.join(flags)})" if flags else ""
                    lines.append(f"  {name} {ctype}{flag_str}")
                output = "\n".join(lines)
            else:
                cursor = conn.execute(
                    "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY name"
                )
                statements = [row[0] for row in cursor.fetchall()]
                output = "\n\n".join(statements)

            return ToolResult(success=True, output=output)
        finally:
            conn.close()

    async def _export(self, db_path: str, table: str = "", format: str = "json", **kw) -> ToolResult:
        """Export table data."""
        if not table:
            return ToolResult(success=False, output="", error="Table name required for export")
        return await self._query(db_path=db_path, sql=f"SELECT * FROM {table}", format=format)

    async def _create_db(self, db_path: str, sql: str = "", **kw) -> ToolResult:
        """Create a new database with optional schema."""
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
        try:
            if sql:
                conn.executescript(sql)
                conn.commit()
            return ToolResult(
                success=True,
                output=f"Database created at {db_path}" + (f" with schema applied" if sql else ""),
            )
        finally:
            conn.close()

    def _format_table(self, columns: list[str], rows: list[tuple]) -> str:
        """Format query results as an ASCII table."""
        if not columns:
            return "(no results)"

        # Calculate column widths
        widths = [len(str(col)) for col in columns]
        for row in rows:
            for i, val in enumerate(row):
                widths[i] = max(widths[i], len(str(val)))

        # Build table
        separator = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
        header = "|" + "|".join(f" {col:<{widths[i]}} " for i, col in enumerate(columns)) + "|"

        lines = [separator, header, separator]
        for row in rows[:100]:
            line = "|" + "|".join(
                f" {str(val):<{widths[i]}} " for i, val in enumerate(row)
            ) + "|"
            lines.append(line)
        lines.append(separator)

        if len(rows) > 100:
            lines.append(f"... {len(rows) - 100} more rows")

        return "\n".join(lines)
