from peewee import BooleanField, CharField
from model import base_model as bm

class File(bm.Base_Model):
    file_name = CharField()
    full_path = CharField(max_length=4096)
    source_path = CharField(max_length=4096)
    extension = CharField(max_length=4)
    media_path = CharField(max_length=4096)
    fingerprint = CharField(max_length=65)
    is_matched = BooleanField(default=False)
    is_hardlinked = BooleanField(default=False)