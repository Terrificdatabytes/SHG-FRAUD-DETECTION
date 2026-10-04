"""Demo-only reset scoped to pending applicant overlays."""
from .config import load_config
from .db import audit, connect


def reset_demo() -> None:
    connection = connect(load_config().db_path)
    try:
        with connection:
            app_nodes = [row[0] for row in connection.execute(
                "SELECT DISTINCT node_id FROM applications WHERE is_demo=1 AND node_id IN "
                "(SELECT id FROM nodes WHERE status='pending')"
            )]
            connection.execute(
                "DELETE FROM alerts WHERE app_id IN (SELECT app_id FROM applications "
                "WHERE is_demo=1 AND node_id IN (SELECT id FROM nodes WHERE status='pending'))"
            )
            connection.execute(
                "DELETE FROM applications WHERE is_demo=1 AND node_id IN "
                "(SELECT id FROM nodes WHERE status='pending')"
            )
            for node_id in app_nodes:
                connection.execute("DELETE FROM explanations WHERE node_id=?", (node_id,))
                connection.execute("DELETE FROM scores WHERE node_id=?", (node_id,))
            for node_id in app_nodes:
                connection.execute(
                    "DELETE FROM edges WHERE status='pending' AND (src=? OR dst=?)",
                    (node_id, node_id),
                )
                connection.execute(
                    "DELETE FROM nodes WHERE status='pending' AND id=?", (node_id,)
                )
            connection.execute(
                "DELETE FROM nodes WHERE status='pending' "
                "AND id NOT IN (SELECT src FROM edges) "
                "AND id NOT IN (SELECT dst FROM edges)"
            )
            audit(connection, "RESET_DEMO", "Pending demo overlays cleared", "system")
    finally:
        connection.close()
