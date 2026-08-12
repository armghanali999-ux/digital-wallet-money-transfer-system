from django.db import connection
from django.utils import timezone

from transactions.models import IdempotencyRecord, ReferenceSequence


class TransactionRepository:
    @staticmethod
    def next_reference():
        today = timezone.localdate()
        table = connection.ops.quote_name(ReferenceSequence._meta.db_table)
        date_column = connection.ops.quote_name("business_date")
        value_column = connection.ops.quote_name("last_value")
        # LAST_INSERT_ID(expr) is connection-local. The upsert makes allocation
        # atomic even when two requests create/use the day's counter together.
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO {table} ({date_column}, {value_column}) VALUES (%s, LAST_INSERT_ID(1)) "
                f"ON DUPLICATE KEY UPDATE {value_column} = LAST_INSERT_ID({value_column} + 1)",
                [today],
            )
            cursor.execute("SELECT LAST_INSERT_ID()")
            value = cursor.fetchone()[0]
        return f"TXN-{today:%Y%m%d}-{value:06d}"

    @staticmethod
    def idempotency(actor, operation, key, fingerprint):
        table = connection.ops.quote_name(IdempotencyRecord._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT IGNORE INTO {table} "
                "(actor_id, operation, `key`, request_fingerprint, transaction_id, response_data, created_at) "
                "VALUES (%s, %s, %s, %s, NULL, NULL, %s)",
                [actor.id, operation, key, fingerprint, timezone.now()],
            )
            created = cursor.rowcount == 1
        record = IdempotencyRecord.objects.select_for_update().get(actor=actor, operation=operation, key=key)
        return record, created
