# Testing

The suite runs against a real MySQL 8 database named `hacknyu25_test`. CI sets this up
in `.github/workflows/test.yml`; locally you need to do it once.

## Setup

Create the database and load the schema (MAMP defaults shown; adjust host/port/credentials):

```sh
mysql -h 127.0.0.1 -P 8889 -uroot -proot -e "CREATE DATABASE hacknyu25_test"
for f in create.sql triggers.sql tips_schema.sql promotional_codes_migration.sql; do
  sed 's/^USE hacknyu25;/USE hacknyu25_test;/' "src/database/$f" \
    | mysql -h 127.0.0.1 -P 8889 -uroot -proot hacknyu25_test
done
```

Or use a throwaway container:

```sh
docker run -d --rm --name preppr-mysql-test -e MYSQL_ROOT_PASSWORD=root \
  -e MYSQL_DATABASE=hacknyu25_test -p 3307:3306 mysql:8.0
```

After a schema change, drop and recreate `hacknyu25_test` the same way.

## Running

```sh
DB_NAME_TEST=hacknyu25_test python -m pytest                  # whole suite
DB_NAME_TEST=hacknyu25_test python -m pytest -m subscription  # one marker
DB_NAME_TEST=hacknyu25_test python -m pytest tests/test_pantry.py
```

`DB_HOST`, `DB_PORT`, `DB_USER` and `DB_PASSWORD` come from the environment or `.env`,
as for the app. Markers are listed in `pytest.ini`.

## How isolation works

The app commits as it goes, so tests are not wrapped in transactions. Instead, before
every test `tests/conftest.py` empties every table, restores the reference rows the
schema files insert (`pantry_categories`, `subscription_tier_features`, `tips`), and
seeds test data. Tests can therefore write freely, and nothing they write survives into
the next test.

- Use the `test_db` fixture (or `open_test_connection()`) for direct SQL. It autocommits,
  so the app sees setup rows and assertions see what the app committed.
- To make the app fail, patch `get_db` in the module under test
  (e.g. `src.backend.apis.budget.get_db`), not `src.database.get_db`.
- Never run the suite against a database you care about: it is wiped before every test.
  `conftest.py` refuses to run unless the database is `hacknyu25_test`.
