import os
import json
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.conf import settings

from utils.save_snapshots import move_json, save_in_disk
from evidence.parse import Build


logger = logging.getLogger('django')


User = get_user_model()


class Command(BaseCommand):
    help = "Insert Snapshots"
    snapshots = []
    files = []
    devices = []

    def add_arguments(self, parser):
        parser.add_argument('path', type=str, help='Path to snapshots')
        parser.add_argument('email', type=str, help='Email of user')


    def handle(self, *args, **kwargs):
        path = kwargs['path']
        email = kwargs['email']
        self.user = User.objects.get(email=email)

        if os.path.isfile(path):
            self.open(path)

        elif os.path.isdir(path):
            self.read_directory(path)

        self.parsing()

    def read_directory(self, directory):
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                self.open(filepath)

    def open(self, filepath):
        try:
            with open(filepath, 'r') as file:
                content = json.loads(file.read())
                path_name = save_in_disk(content, self.user.institution.name)

                self.snapshots.append((content, path_name))

        except Exception as e:
            logger.error("Could not open file %s: %s", filepath, e)

    def parsing(self):
        for s, p in self.snapshots:
            try:
                self.devices.append(Build(s, self.user))
                move_json(p, self.user.institution.name)
            except Exception as e:
                snapshot_id = s.get("uuid", "")
                txt = "Could not parse snapshot %s: %s"
                logger.error(txt, snapshot_id, e)
