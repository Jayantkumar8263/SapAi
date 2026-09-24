"""
Inventory Database Service
==========================

Provides the database operations required by the BSP
inventory automation process.

Documented BSP flow:

    Final Inventory
          ↓
    replace mminv_new
          ↓
    unique material codes
          ↓
    20,000-record batching
          ↓
    ZMAT-FUND_POPR
          ↓
    Inventory PO
          ↓
    replace mminv1_new

IMPORTANT
---------
The actual BSP production database type is not yet known.

Therefore this service works against a supplied DB-API
connection and does not assume SQL Server, Access, Oracle,
etc.

SQLite is used only for automated tests.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


# ============================================================
# DATABASE SERVICE
# ============================================================


class InventoryDatabase:
    """
    Database abstraction for BSP inventory processing.

    Parameters
    ----------
    connection:
        An existing DB-API connection.

    The connection can eventually be:

        SQL Server
        Access
        Oracle
        PostgreSQL
        SQLite
        etc.

    as long as it supports the operations used by this class.
    """

    def __init__(
        self,
        connection,
    ):
        if connection is None:

            raise ValueError(
                "Database connection cannot be None."
            )

        self.connection = connection

    # =========================================================
    # TABLE NAME VALIDATION
    # =========================================================

    @staticmethod
    def _validate_table_name(
        table_name: str,
    ) -> str:
        """
        Validate a table name before using it in SQL.

        Table names cannot safely be passed as SQL parameters,
        so we strictly validate them.
        """

        if not table_name:
            raise ValueError(
                "Table name cannot be empty."
            )

        table_name = str(
            table_name
        ).strip()

        if not table_name.replace(
            "_",
            "",
        ).isalnum():

            raise ValueError(
                f"Invalid table name: {table_name}"
            )

        return table_name

    # =========================================================
    # REPLACE TABLE
    # =========================================================

    def replace_table(
        self,
        dataframe: pd.DataFrame,
        table_name: str,
    ) -> dict[str, Any]:
        """
        Replace the contents of a database table.

        This represents the BSP process:

            delete old table contents
            import new Inventory

        The table itself is recreated when supported by pandas.
        """

        if dataframe is None:

            raise ValueError(
                "DataFrame cannot be None."
            )

        if not isinstance(
            dataframe,
            pd.DataFrame,
        ):

            raise TypeError(
                "dataframe must be a pandas DataFrame."
            )

        table_name = (
            self._validate_table_name(
                table_name
            )
        )

        dataframe = dataframe.copy()

        # -----------------------------------------------------
        # Normalize column names
        # -----------------------------------------------------

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

        # -----------------------------------------------------
        # Write replacement table
        # -----------------------------------------------------

        dataframe.to_sql(
            table_name,
            self.connection,
            if_exists="replace",
            index=False,
        )

        return {
            "success": True,
            "table": table_name,
            "rows": len(dataframe),
            "columns": list(
                dataframe.columns
            ),
        }

    # =========================================================
    # COUNT ROWS
    # =========================================================

    def count_rows(
        self,
        table_name: str,
    ) -> int:
        """
        Return the number of records in a table.
        """

        table_name = (
            self._validate_table_name(
                table_name
            )
        )

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name}
                """
            )

            row = cursor.fetchone()

            return int(
                row[0]
            )

        finally:

            cursor.close()

    # =========================================================
    # UNIQUE MATERIAL CODES
    # =========================================================

    def get_unique_material_codes(
        self,
        table_name: str,
        material_code_column: str = "Material Code",
    ) -> list[str]:
        """
        Extract unique material codes from a database table.

        This is the database equivalent of the BSP step:

            Copy unique material codes
            ↓
            split into 20,000-record batches
        """

        table_name = (
            self._validate_table_name(
                table_name
            )
        )

        if not material_code_column:
            raise ValueError(
                "Material-code column cannot be empty."
            )

        query = f"""
            SELECT DISTINCT
                "{material_code_column}"
            FROM {table_name}
            WHERE "{material_code_column}"
                IS NOT NULL
        """

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                query
            )

            rows = cursor.fetchall()

        finally:

            cursor.close()

        codes: list[str] = []

        seen: set[str] = set()

        for row in rows:

            if not row:
                continue

            value = row[0]

            if value is None:
                continue

            code = str(
                value
            ).strip()

            if not code:
                continue

            # Handle Excel-style numeric values.
            if code.endswith(".0"):

                try:

                    number = float(
                        code
                    )

                    if number.is_integer():

                        code = str(
                            int(number)
                        )

                except ValueError:
                    pass

            if code in seen:
                continue

            seen.add(code)

            codes.append(
                code
            )

        return codes

    # =========================================================
    # TABLE EXISTS
    # =========================================================

    def table_exists(
        self,
        table_name: str,
    ) -> bool:
        """
        Check whether a table exists.

        This implementation uses SQLite-compatible metadata.
        Production-specific adapters can override this later
        if required by the BSP database.
        """

        table_name = (
            self._validate_table_name(
                table_name
            )
        )

        cursor = self.connection.cursor()

        try:

            cursor.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                AND name = ?
                """,
                (table_name,),
            )

            return (
                cursor.fetchone()
                is not None
            )

        finally:

            cursor.close()

    # =========================================================
    # READ TABLE
    # =========================================================

    def read_table(
        self,
        table_name: str,
    ) -> pd.DataFrame:
        """
        Read a complete table into a DataFrame.
        """

        table_name = (
            self._validate_table_name(
                table_name
            )
        )

        return pd.read_sql_query(
            f"""
            SELECT *
            FROM {table_name}
            """,
            self.connection,
        )


# ============================================================
# SQLITE CONNECTION
# ============================================================


def create_sqlite_connection(
    database_file: str | Path = ":memory:",
) -> sqlite3.Connection:
    """
    Create a SQLite connection.

    SQLite is used for local testing only.

    The production BSP database connection will be supplied
    later once the actual database technology is confirmed.
    """

    return sqlite3.connect(
        database_file
    )