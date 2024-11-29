import os
import json
import logging

from django.core.management.base import BaseCommand
from django.conf import settings

from utils.device import create_annotation, create_doc, create_index
from user.models import Institution
from evidence.parse import Build


logger = logging.getLogger('django')


class Command(BaseCommand):
    help = "Reindex snapshots"
    snapshots = []
    EVIDENCES = settings.EVIDENCES_DIR

    def handle(self, *args, **kwargs):
        if os.path.isdir(self.EVIDENCES):
            self.read_files(self.EVIDENCES)

        self.parsing()

    def read_files(self, directory):
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if not os.path.isdir(filepath):
                continue

            institution = Institution.objects.filter(name=filename).first()

            if not institution:
                continue
            user = institution.user_set.filter(is_admin=True).first()
            if not user:
                txt = "No there are Admins for the institution: %s"
                logger.warning(txt, institution.name)
                continue

            snapshots_path = os.path.join(filepath, "snapshots")
            placeholders_path = os.path.join(filepath, "placeholders")

            for f in os.listdir(snapshots_path):
                f_path = os.path.join(snapshots_path, f)

                if f_path[-5:] == ".json" and os.path.isfile(f_path):
                    self.open(f_path, user)

            for f in os.listdir(placeholders_path):
                f_path = os.path.join(placeholders_path, f)

                if f_path[-5:] == ".json" and os.path.isfile(f_path):
                    self.open(f_path, user)

    def open(self, filepath, user):
        with open(filepath, 'r') as file:
            content = json.loads(file.read())
            self.snapshots.append((content, user, filepath))

    def parsing(self):
        for s, user, f_path in self.snapshots:
            if s.get("type") == "Websnapshot":
                self.build_placeholder(s, user, f_path)
            else:
                self.build_snapshot(s, user, f_path)

    def build_placeholder(self, s, user, f_path):
            try:
                create_index(s, user)
                create_annotation(s, user, commit=True)
            except Exception as err:
                txt = "In placeholder %s \n%s"
                logger.warning(txt, f_path, err)
                
    def build_snapshot(self, s, user, f_path):
            try:
                Build(s, user)
            except Exception:
                txt = "Error: in Snapshot {}".format(f_path)
                logger.error(txt)
