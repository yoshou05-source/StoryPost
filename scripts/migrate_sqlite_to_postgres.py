#!/usr/bin/env python3
"""
Copy data from the local SQLite `instance/story_posts.db` into a Postgres (or other) database.

Usage:
  Set `TARGET_DATABASE_URL` to your production database (e.g. Postgres) and run:
    python scripts/migrate_sqlite_to_postgres.py

Optional: set `SQLITE_PATH` to point to a different sqlite file.

The script will:
  - copy categories (by name, avoiding duplicates)
  - copy story posts and map categories

Run `flask db upgrade` on the target DB before running this script.
"""
import os
from sqlalchemy import create_engine, MetaData, Table, select, insert
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..'))
default_sqlite = os.path.join(project_root, 'instance', 'story_posts.db')
sqlite_path = os.environ.get('SQLITE_PATH', default_sqlite)
if sqlite_path and not sqlite_path.startswith('sqlite:'):
    source_url = f"sqlite:///{sqlite_path}"
else:
    source_url = sqlite_path

target_url = os.environ.get('TARGET_DATABASE_URL') or os.environ.get('DATABASE_URL')
if not target_url:
    raise SystemExit('ERROR: set TARGET_DATABASE_URL or DATABASE_URL to the target DB connection string')

print('Source:', source_url)
print('Target:', target_url)

def reflect_table(engine, table_name):
    md = MetaData()
    md.reflect(bind=engine, only=[table_name])
    return md.tables.get(table_name)

def main():
    src_engine = create_engine(source_url)
    tgt_engine = create_engine(target_url)

    try:
        src_conn = src_engine.connect()
        tgt_conn = tgt_engine.connect()
    except SQLAlchemyError as e:
        raise SystemExit(f'Error connecting to databases: {e}')

    src_meta = MetaData()
    src_meta.reflect(bind=src_engine)
    tgt_meta = MetaData()
    tgt_meta.reflect(bind=tgt_engine)

    if 'categories' not in src_meta.tables or 'story_posts' not in src_meta.tables:
        raise SystemExit('Source sqlite DB does not contain required tables: categories, story_posts')

    src_cats = src_meta.tables['categories']
    src_posts = src_meta.tables['story_posts']

    if 'categories' not in tgt_meta.tables or 'story_posts' not in tgt_meta.tables:
        print('Warning: target DB missing expected tables. Ensure migrations have been applied (flask db upgrade).')

    tgt_cats = tgt_meta.tables.get('categories')
    tgt_posts = tgt_meta.tables.get('story_posts')

    mapping = {}  # old_category_id -> new_category_id

    trans_tgt = tgt_conn.begin()
    try:
        # Copy categories
        src_cat_rows = src_conn.execute(select(src_cats)).fetchall()
        for row in src_cat_rows:
            row_dict = row._mapping
            name = row_dict['name']
            # Check if category exists in target by name
            existing = None
            if tgt_cats is not None:
                existing = tgt_conn.execute(select(tgt_cats).where(tgt_cats.c.name == name)).fetchone()

            if existing:
                new_id = existing._mapping['id']
            else:
                if tgt_cats is None:
                    raise SystemExit('Target does not have `categories` table.')
                insert_stmt = insert(tgt_cats).values(
                    name=row_dict['name'],
                    description=row_dict.get('description'),
                    color=row_dict.get('color')
                )
                res = tgt_conn.execute(insert_stmt)
                try:
                    new_id = res.inserted_primary_key[0]
                except Exception:
                    # Fallback: select by name
                    new_row = tgt_conn.execute(select(tgt_cats).where(tgt_cats.c.name == name)).fetchone()
                    new_id = new_row._mapping['id']

            mapping[row_dict['id']] = new_id

        # Copy posts
        src_post_rows = src_conn.execute(select(src_posts)).fetchall()
        for row in src_post_rows:
            row_dict = row._mapping
            # Basic duplicate check: title + created_at
            exists = None
            if tgt_posts is not None:
                exists = tgt_conn.execute(
                    select(tgt_posts).where(
                        (tgt_posts.c.title == row_dict['title']) & (tgt_posts.c.created_at == row_dict['created_at'])
                    )
                ).fetchone()

            if exists:
                continue

            if tgt_posts is None:
                raise SystemExit('Target does not have `story_posts` table.')

            mapped_cat = mapping.get(row_dict['category_id']) if row_dict['category_id'] is not None else None

            insert_stmt = insert(tgt_posts).values(
                title=row_dict['title'],
                content=row_dict['content'],
                category_id=mapped_cat,
                is_favorite=row_dict.get('is_favorite', False),
                status=row_dict.get('status', 'published'),
                created_at=row_dict.get('created_at'),
                updated_at=row_dict.get('updated_at')
            )
            tgt_conn.execute(insert_stmt)

        trans_tgt.commit()
        print('Migration complete.')
    except Exception:
        trans_tgt.rollback()
        raise
    finally:
        src_conn.close()
        tgt_conn.close()

if __name__ == '__main__':
    main()
