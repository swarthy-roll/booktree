from peewee import BooleanField, CharField, DateTimeField, TextField
from datetime import datetime
from model import base_model as bm

class File(bm.Base_Model):
    file_name = CharField()
    full_path = CharField(max_length=4096, unique=True)
    source_path = CharField(max_length=4096)
    extension = CharField(max_length=4)
    media_path = CharField(max_length=4096, null=True)
    fingerprint = CharField(max_length=65)
    is_matched = BooleanField(default=False)
    is_hardlinked = BooleanField(default=False)
    probe_results = TextField(null=True)
    timestamp = DateTimeField(default = datetime.now())