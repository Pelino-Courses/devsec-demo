"""
Fix a stale mupenz_fulgence_profile table that was created by a previous
version of the app.

The live table contains columns (phone, gender, avatar) with NOT NULL
constraints that no longer exist in the current model.  Because there are
zero profile rows, we can safely recreate the table without any data loss.

We use SeparateDatabaseAndState so that only the database is touched —
the migration state is already correct from 0001_initial.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('mupenz_fulgence', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            # These operations run against the actual database only
            database_operations=[
                # 1. Build the correct table under a temporary name
                migrations.RunSQL(
                    sql="""
                        CREATE TABLE "mupenz_fulgence_profile_new" (
                            "id"          integer      NOT NULL PRIMARY KEY AUTOINCREMENT,
                            "bio"         text         NOT NULL DEFAULT '',
                            "location"    varchar(100) NOT NULL DEFAULT '',
                            "birth_date"  date         NULL,
                            "created_at"  datetime     NOT NULL,
                            "updated_at"  datetime     NOT NULL,
                            "user_id"     integer      NOT NULL UNIQUE
                                          REFERENCES "auth_user" ("id")
                                          DEFERRABLE INITIALLY DEFERRED
                        )
                    """,
                    reverse_sql='DROP TABLE IF EXISTS "mupenz_fulgence_profile_new";',
                ),
                # 2. Remove the stale table (no rows to preserve)
                migrations.RunSQL(
                    sql='DROP TABLE "mupenz_fulgence_profile";',
                    reverse_sql=migrations.RunSQL.noop,
                ),
                # 3. Promote the new table to the canonical name
                migrations.RunSQL(
                    sql='ALTER TABLE "mupenz_fulgence_profile_new" '
                        'RENAME TO "mupenz_fulgence_profile";',
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            # No state operations — the ORM model is already correct
            state_operations=[],
        ),
    ]
