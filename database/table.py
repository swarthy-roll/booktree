from database.database import db
from model.base_model import Base_Model
from peewee import IntegrityError

def create_table(table_name):
    print(f"Attempting to create the {table_name} table...")
    success = False
    try:
        model_classes = Base_Model.__subclasses__()

        for model in model_classes:
            if model.__name__ == table_name:
                db.connect()
                print(f"Creating the {model.__name__} table...")
                db.create_tables([model])
                db.close()
                success = True

    except Exception as e:
        print(f"{e}")
    finally:
        if not success:
            print(f"WARNING: Could not create table {table_name}!")

def create_tables():
    try:
        model_classes = Base_Model.__subclasses__()
        
        with db.atomic() as transaction:
            try:
                db.create_tables(model_classes)
            except IntegrityError:
                print("Error occurred while attempting to create database tables.")
                transaction.rollback()
        

        print("All tables created successfully!")
    
    except Exception as e:
        print(f"ERROR: Error creating database tables: {e}")

def drop_all_tables():
    try:
        db.connect()

        db.pragma('foreign_keys', 0) #turn off foreign keys temporarily so we can drop tables without foreign key constraint errors
        cursor = db.execute_sql("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            print(f"Dropping the {table} table...")
            db.execute_sql(f"DROP TABLE IF EXISTS {table};")

        db.pragma('foreign_keys', 1) #turn foreign keys back on
        db.close()
        print("All tables dropped successfully.")
    
    except Exception as e:
        print(f"ERROR: Failed to drop tables: {e}")