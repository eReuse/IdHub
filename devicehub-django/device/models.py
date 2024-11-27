from django.db import models, connection

from utils.constants import ALGOS
from evidence.models import Annotation, Evidence
from lot.models import DeviceLot


class Device:
    class Types(models.TextChoices):
        DESKTOP = "Desktop"
        LAPTOP = "Laptop"
        SERVER = "Server"
        GRAPHICCARD = "GraphicCard"
        HARDDRIVE = "HardDrive"
        SOLIDSTATEDRIVE = "SolidStateDrive"
        MOTHERBOARD = "Motherboard"
        NETWORKADAPTER = "NetworkAdapter"
        PROCESSOR = "Processor"
        RAMMODULE = "RamModule"
        SOUNDCARD = "SoundCard"
        DISPLAY = "Display"
        BATTERY = "Battery"
        CAMERA = "Camera"

    def __init__(self, *args, **kwargs):
        # the id is the chid of the device
        self.id = kwargs["id"]
        self.uuid = kwargs.get("uuid")
        self.pk = self.id
        self.shortid = self.pk[:6].upper()
        self.algorithm = None
        self.owner = None
        self.annotations = []
        self.hids = []
        self.uuids = []
        self.evidences = []
        self.lots = []
        self.last_evidence = None
        self.get_last_evidence()

    def initial(self):
        self.get_annotations()
        self.get_uuids()
        self.get_hids()
        self.get_evidences()
        self.get_lots()

    def get_annotations(self):
        if self.annotations:
            return self.annotations

        self.annotations = Annotation.objects.filter(
            type=Annotation.Type.SYSTEM,
            value=self.id
        ).order_by("-created")

        if self.annotations.count():
            self.algorithm = self.annotations[0].key
            self.owner = self.annotations[0].owner

        return self.annotations

    def get_user_annotations(self):
        if not self.uuids:
            self.get_uuids()

        annotations = Annotation.objects.filter(
            uuid__in=self.uuids,
            owner=self.owner,
            type=Annotation.Type.USER
        )
        return annotations

    def get_user_documents(self):
        if not self.uuids:
            self.get_uuids()

        annotations = Annotation.objects.filter(
            uuid__in=self.uuids,
            owner=self.owner,
            type=Annotation.Type.DOCUMENT
        )
        return annotations

    def get_uuids(self):
        for a in self.get_annotations():
            if a.uuid not in self.uuids:
                self.uuids.append(a.uuid)

    def get_hids(self):
        annotations = self.get_annotations()

        algos = list(ALGOS.keys())
        algos.append('CUSTOM_ID')
        self.hids = list(set(annotations.filter(
            type=Annotation.Type.SYSTEM,
            key__in=algos,
        ).values_list("value", flat=True)))

    def get_evidences(self):
        if not self.uuids:
            self.get_uuids()

        self.evidences = [Evidence(u) for u in self.uuids]

    def get_last_evidence(self):
        if self.last_evidence:
            return

        if self.uuid:
            self.last_evidence = Evidence(self.uuid)
            return

        annotations = self.get_annotations()
        if not annotations.count():
            return
        annotation = annotations.first()
        self.last_evidence = Evidence(annotation.uuid)

    def is_eraseserver(self):
        if not self.uuids:
            self.get_uuids()
        if not self.uuids:
            return False

        annotation = Annotation.objects.filter(
            uuid__in=self.uuids,
            owner=self.owner,
            type=Annotation.Type.ERASE_SERVER
        ).first()

        if annotation:
            return True
        return False

    def last_uuid(self):
        if self.uuid:
            return self.uuid
        return self.uuids[0]

    def get_lots(self):
        self.lots = [
            x.lot for x in DeviceLot.objects.filter(device_id=self.id)]

    @classmethod
    def get_unassigned(cls, institution, offset=0, limit=None):

        sql = """
            WITH RankedAnnotations AS (
                SELECT
                    t1.value,
                    t1.key,
                    ROW_NUMBER() OVER (
                        PARTITION BY t1.uuid
                        ORDER BY
                            CASE
                                WHEN t1.key = 'CUSTOM_ID' THEN 1
                                WHEN t1.key = 'hidalgo1' THEN 2
                                ELSE 3
                            END,
                            t1.created DESC
                    ) AS row_num
                FROM evidence_annotation AS t1
                LEFT JOIN lot_devicelot AS t2 ON t1.value = t2.device_id
                WHERE t2.device_id IS NULL
                  AND t1.owner_id = {institution}
                  AND t1.type = {type}
            )
            SELECT DISTINCT
                value
            FROM
                RankedAnnotations
            WHERE
                row_num = 1
        """.format(
            institution=institution.id,
            type=Annotation.Type.SYSTEM,
        )
        if limit:
            sql += " limit {} offset {}".format(int(limit), int(offset))

        sql += ";"

        annotations = []
        with connection.cursor() as cursor:
            cursor.execute(sql)
            annotations = cursor.fetchall()

        devices = [cls(id=x[0]) for x in annotations]
        count = cls.get_unassigned_count(institution)
        return devices, count

    @classmethod
    def get_unassigned_count(cls, institution):

        sql = """
            WITH RankedAnnotations AS (
                SELECT
                    t1.value,
                    t1.key,
                    ROW_NUMBER() OVER (
                        PARTITION BY t1.uuid
                        ORDER BY
                            CASE
                                WHEN t1.key = 'CUSTOM_ID' THEN 1
                                WHEN t1.key = 'hidalgo1' THEN 2
                                ELSE 3
                            END,
                            t1.created DESC
                    ) AS row_num
                FROM evidence_annotation AS t1
                LEFT JOIN lot_devicelot AS t2 ON t1.value = t2.device_id
                WHERE t2.device_id IS NULL
                  AND t1.owner_id = {institution}
                  AND t1.type = {type}
            )
            SELECT
                COUNT(DISTINCT value)
            FROM
                RankedAnnotations
            WHERE
                row_num = 1
        """.format(
            institution=institution.id,
            type=Annotation.Type.SYSTEM,
        )
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()[0][0]

    @classmethod
    def get_annotation_from_uuid(cls, uuid, institution):
        sql = """
            WITH RankedAnnotations AS (
                SELECT
                    t1.value,
                    t1.key,
                    ROW_NUMBER() OVER (
                        PARTITION BY t1.uuid
                        ORDER BY
                            CASE
                                WHEN t1.key = 'CUSTOM_ID' THEN 1
                                WHEN t1.key = 'hidalgo1' THEN 2
                                ELSE 3
                            END,
                            t1.created DESC
                    ) AS row_num
                FROM evidence_annotation AS t1
                LEFT JOIN lot_devicelot AS t2 ON t1.value = t2.device_id
                WHERE t2.device_id IS NULL
                  AND t1.owner_id = {institution}
                  AND t1.type = {type}
                  AND t1.uuid = '{uuid}'
            )
            SELECT DISTINCT
                value
            FROM
                RankedAnnotations
            WHERE
                row_num = 1;
        """.format(
            uuid=uuid.replace("-", ""),
            institution=institution.id,
            type=Annotation.Type.SYSTEM,
        )

        annotations = []
        with connection.cursor() as cursor:
            cursor.execute(sql)
            annotations = cursor.fetchall()

        return cls(id=annotations[0][0])

    @property
    def is_websnapshot(self):
        self.get_last_evidence()
        return self.last_evidence.doc['type'] == "WebSnapshot"

    @property
    def last_user_evidence(self):
        self.get_last_evidence()
        return self.last_evidence.doc['kv'].items()

    @property
    def manufacturer(self):
        self.get_last_evidence()
        return self.last_evidence.get_manufacturer()

    @property
    def serial_number(self):
        self.get_last_evidence()
        return self.last_evidence.get_serial_number()

    @property
    def type(self):
        self.get_last_evidence()
        if self.last_evidence.doc['type'] == "WebSnapshot":
            return self.last_evidence.doc.get("device", {}).get("type", "")

        return self.last_evidence.get_chassis()

    @property
    def model(self):
        self.get_last_evidence()
        return self.last_evidence.get_model()

    @property
    def components(self):
        self.get_last_evidence()
        return self.last_evidence.get_components()
