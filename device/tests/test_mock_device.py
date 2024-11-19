from device.models import Device
from unittest.mock import MagicMock


class TestDevice(Device):
    def __init__(self, id):
        super().__init__(id=id)
        self.shortid = id[:6].upper()
        self.uuids = []
        self.hids = ['hid1', 'hid2']
        self._setup_evidence()

    def _setup_evidence(self):
        self._evidence = MagicMock()
        self._evidence.doc = {
            'type': 'Computer',
            'manufacturer': 'Test Manufacturer',
            'model': 'Test Model',
            'device': {
                'serialNumber': 'SN123456',
                'type': 'Computer'
            }
        }
        self._evidence.get_manufacturer = lambda: 'Test Manufacturer'
        self._evidence.get_model = lambda: 'Test Model'
        self._evidence.get_chassis = lambda: 'Computer'
        self._evidence.get_components = lambda: [
            {
                'type': 'CPU',
                'model': 'Intel i7',
                'manufacturer': 'Intel',
                'serialNumber': 'SN12345678'
            },
            {
                'type': 'RAM',
                'size': '8GB',
                'manufacturer': 'Kingston',
                'serialNumber': 'SN87654321'
            }
        ]
        self.last_evidence = self._evidence

    @property
    def components(self):
        return self.last_evidence.get_components()

    @property
    def serial_number(self):
        return self.last_evidence.doc['device']['serialNumber']
