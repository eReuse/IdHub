import json
import hashlib

from dmidecode import DMIParse
from django.db import models

from utils.constants import STR_EXTEND_SIZE, CHASSIS_DH
from evidence.xapian import search
from evidence.parse_details import ParseSnapshot
from user.models import User, Institution


class Annotation(models.Model):
    class Type(models.IntegerChoices):
        SYSTEM = 0, "System"
        USER = 1, "User"
        DOCUMENT = 2, "Document"
        ERASE_SERVER = 3, "EraseServer"

    created = models.DateTimeField(auto_now_add=True)
    uuid = models.UUIDField()
    owner = models.ForeignKey(Institution, on_delete=models.CASCADE)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True)
    type = models.SmallIntegerField(choices=Type)
    key = models.CharField(max_length=STR_EXTEND_SIZE)
    value = models.CharField(max_length=STR_EXTEND_SIZE)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["type", "key", "uuid"], name="unique_type_key_uuid")
        ]


class Evidence:
    def __init__(self, uuid):
        self.uuid = uuid
        self.owner = None
        self.doc = None
        self.created = None
        self.dmi = None
        self.annotations = []
        self.components = []
        self.default = "n/a"

        self.get_owner()
        self.get_time()

    def get_annotations(self):
        self.annotations = Annotation.objects.filter(
            uuid=self.uuid
        ).order_by("created")

    def get_owner(self):
        if not self.annotations:
            self.get_annotations()
        a = self.annotations.first()
        if a:
            self.owner = a.owner

    def get_phid(self):
        if not self.doc:
            self.get_doc()
            
        return hashlib.sha3_256(json.dumps(self.doc)).hexdigest()

    def get_doc(self):
        self.doc = {}
        if not self.owner:
            self.get_owner()
        qry = 'uuid:"{}"'.format(self.uuid)
        matches = search(self.owner, qry, limit=1)
        if matches and matches.size() < 0:
            return

        for xa in matches:
            self.doc = json.loads(xa.document.get_data())

        if not self.is_legacy():
            dmidecode_raw = self.doc["data"]["dmidecode"]
            self.dmi = DMIParse(dmidecode_raw)

    def get_time(self):
        if not self.doc:
            self.get_doc()
        self.created = self.doc.get("endTime")

        if not self.created:
            self.created = self.annotations.last().created

    def get_components(self):
        if self.is_legacy():
            return self.doc.get('components', [])
        self.set_components()
        return self.components

    def get_manufacturer(self):
        if self.is_web_snapshot():
            kv = self.doc.get('kv', {})
            if len(kv) < 1:
                return ""
            return list(self.doc.get('kv').values())[0]

        if self.is_legacy():
            return self.doc['device']['manufacturer']

        return self.dmi.manufacturer().strip()

    def get_model(self):
        if self.is_web_snapshot():
            kv = self.doc.get('kv', {})
            if len(kv) < 2:
                return ""
            return list(self.doc.get('kv').values())[1]

        if self.is_legacy():
            return self.doc['device']['model']

        return self.dmi.model().strip()

    def get_chassis(self):
        if self.is_legacy():
            return self.doc['device']['model']

        chassis = self.dmi.get("Chassis")[0].get("Type", '_virtual')
        lower_type = chassis.lower()

        for k, v in CHASSIS_DH.items():
            if lower_type in v:
                return k
        return ""

    def get_serial_number(self):
        if self.is_legacy():
            return self.doc['device']['serialNumber']
        return self.dmi.serial_number().strip()

    @classmethod
    def get_all(cls, user):
        return Annotation.objects.filter(
            owner=user.institution,
            type=Annotation.Type.SYSTEM,
            key="hidalgo1",
        ).order_by("-created").values_list("uuid", "created").distinct()

    def set_components(self):
        snapshot = ParseSnapshot(self.doc).snapshot_json
        self.components = snapshot['components']

    def is_legacy(self):
        return self.doc.get("software") != "workbench-script"

    def is_web_snapshot(self):
        return self.doc.get("type") == "WebSnapshot"
