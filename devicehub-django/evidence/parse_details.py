import json
import logging
import numpy as np

from datetime import datetime
from dmidecode import DMIParse
from json_repair import repair_json

from utils.constants import CHASSIS_DH, DATASTORAGEINTERFACE


logger = logging.getLogger('django')


def get_lshw_child(child, nets, component):
    if child.get('id') == component:
        nets.append(child)
    if child.get('children'):
        [get_lshw_child(x, nets, component) for x in child['children']]


class ParseSnapshot:
    def __init__(self, snapshot, default="n/a"):
        self.default = default
        self.dmidecode_raw = snapshot["data"].get("dmidecode", "{}")
        self.smart_raw = snapshot["data"].get("disks", [])
        self.hwinfo_raw = snapshot["data"].get("hwinfo", "")
        self.lshw_raw = snapshot["data"].get("lshw", {}) or {}
        self.lscpi_raw = snapshot["data"].get("lspci", "")
        self.device = {"actions": []}
        self.components = []
        self.monitors = []

        self.dmi = DMIParse(self.dmidecode_raw)
        self.smart = self.loads(self.smart_raw)
        self.lshw = self.loads(self.lshw_raw)
        self.hwinfo = self.parse_hwinfo()

        self.set_computer()
        self.get_hwinfo_monitors()
        self.set_components()
        self.snapshot_json = {
            "type": "Snapshot",
            "device": self.device,
            "software": snapshot["software"],
            "components": self.components,
            "uuid": snapshot['uuid'],
            "version": snapshot['version'],
            "endTime": snapshot["timestamp"],
            "elapsed": 1,
        }

    def set_computer(self):
        self.device['manufacturer'] = self.dmi.manufacturer().strip()
        self.device['model'] = self.dmi.model().strip()
        self.device['serialNumber'] = self.dmi.serial_number()
        self.device['type'] = self.get_type()
        self.device['sku'] = self.get_sku()
        self.device['version'] = self.get_version()
        self.device['system_uuid'] = self.get_uuid()
        self.device['family'] = self.get_family()
        self.device['chassis'] = self.get_chassis_dh()

    def set_components(self):
        self.get_cpu()
        self.get_ram()
        self.get_mother_board()
        self.get_graphic()
        self.get_data_storage()
        self.get_display()
        self.get_sound_card()
        self.get_networks()

    def get_cpu(self):
        for cpu in self.dmi.get('Processor'):
            serial = cpu.get('Serial Number')
            if serial == 'Not Specified' or not serial:
                serial = cpu.get('ID').replace(' ', '')
            self.components.append(
                {
                    "actions": [],
                    "type": "Processor",
                    "speed": self.get_cpu_speed(cpu),
                    "cores": int(cpu.get('Core Count', 1)),
                    "model": cpu.get('Version'),
                    "threads": int(cpu.get('Thread Count', 1)),
                    "manufacturer": cpu.get('Manufacturer'),
                    "serialNumber": serial,
                    "brand": cpu.get('Family'),
                    "address": self.get_cpu_address(cpu),
                    "bogomips": self.get_bogomips(),
                }
            )

    def get_ram(self):
        for ram in self.dmi.get("Memory Device"):
            if ram.get('size') == 'No Module Installed':
                continue
            if not ram.get("Speed"):
                continue

            self.components.append(
                {
                    "actions": [],
                    "type": "RamModule",
                    "size": self.get_ram_size(ram),
                    "speed": self.get_ram_speed(ram),
                    "manufacturer": ram.get("Manufacturer", self.default),
                    "serialNumber": ram.get("Serial Number", self.default),
                    "interface": ram.get("Type", "DDR"),
                    "format": ram.get("Form Factor", "DIMM"),
                    "model": ram.get("Part Number", self.default),
                }
            )

    def get_mother_board(self):
        for moder_board in self.dmi.get("Baseboard"):
            self.components.append(
                {
                    "actions": [],
                    "type": "Motherboard",
                    "version": moder_board.get("Version"),
                    "serialNumber": moder_board.get("Serial Number", "").strip(),
                    "manufacturer": moder_board.get("Manufacturer", "").strip(),
                    "biosDate": self.get_bios_date(),
                    "ramMaxSize": self.get_max_ram_size(),
                    "ramSlots": len(self.dmi.get("Memory Device")),
                    "slots": self.get_ram_slots(),
                    "model": moder_board.get("Product Name", "").strip(),
                    "firewire": self.get_firmware_num(),
                    "pcmcia": self.get_pcmcia_num(),
                    "serial": self.get_serial_num(),
                    "usb": self.get_usb_num(),
                }
            )

    def get_graphic(self):
        displays = []
        get_lshw_child(self.lshw, displays, 'display')
        
        for c in displays:
            if not c['configuration'].get('driver', None):
                continue

            self.components.append(
                {
                    "actions": [],
                    "type": "GraphicCard",
                    "memory": self.get_memory_video(c),
                    "manufacturer": c.get("vendor", self.default),
                    "model": c.get("product", self.default),
                    "serialNumber": c.get("serial", self.default),
                }
            )

    def get_memory_video(self, c):
        # get info of lspci
        # pci_id = c['businfo'].split('@')[1]
        # lspci.get(pci_id) | grep size
        # lspci -v -s 00:02.0
        return None

    def get_data_storage(self):
        for sm in self.smart:
            if sm.get('smartctl', {}).get('exit_status') == 1:
                continue
            model = sm.get('model_name')
            manufacturer = None
            hours = sm.get("power_on_time", {}).get("hours", 0)
            if model and len(model.split(" ")) > 1:
                mm = model.split(" ")
                model = mm[-1]
                manufacturer = " ".join(mm[:-1])

            self.components.append(
                {
                    "actions": self.sanitize(sm),
                    "type": self.get_data_storage_type(sm),
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": sm.get('serial_number'),
                    "size": self.get_data_storage_size(sm),
                    "variant": sm.get("firmware_version"),
                    "interface": self.get_data_storage_interface(sm),
                    "hours": hours,
                }
            )

    def sanitize(self, action):
        return []

    def get_bogomips(self):
        if not self.hwinfo:
            return self.default
        
        bogomips = 0
        for row in self.hwinfo:
            for cel in row:
                if 'BogoMips' in cel:
                    try:
                        bogomips += float(cel.split(":")[-1])
                    except:
                        pass
        return bogomips

    def get_networks(self):
        networks = []
        get_lshw_child(self.lshw, networks, 'network')
        
        for c in networks:
            capacity = c.get('capacity')
            wireless = bool(c.get('configuration', {}).get('wireless', False))
            self.components.append(
                {
                    "actions": [],
                    "type": "NetworkAdapter",
                    "model": c.get('product'),
                    "manufacturer": c.get('vendor'),
                    "serialNumber": c.get('serial'),
                    "speed": capacity,
                    "variant": c.get('version', 1),
                    "wireless": wireless or False,
                    "integrated": "PCI:0000:00" in c.get("businfo", ""),
                }
            )

    def get_sound_card(self):
        multimedias = []
        get_lshw_child(self.lshw, multimedias, 'multimedia')
        
        for c in multimedias:
            self.components.append(
                {
                    "actions": [],
                    "type": "SoundCard",
                    "model": c.get('product'),
                    "manufacturer": c.get('vendor'),
                    "serialNumber": c.get('serial'),
                }
            )

    def get_display(self):  # noqa: C901
        TECHS = 'CRT', 'TFT', 'LED', 'PDP', 'LCD', 'OLED', 'AMOLED'

        for c in self.monitors:
            resolution_width, resolution_height = (None,) * 2
            refresh, serial, model, manufacturer, size = (None,) * 5
            year, week, production_date = (None,) * 3

            for x in c:
                if "Vendor: " in x:
                    manufacturer = x.split('Vendor: ')[-1].strip()
                if "Model: " in x:
                    model = x.split('Model: ')[-1].strip()
                if "Serial ID: " in x:
                    serial = x.split('Serial ID: ')[-1].strip()
                if "   Resolution: " in x:
                    rs = x.split('   Resolution: ')[-1].strip()
                    if 'x' in rs:
                        resolution_width, resolution_height = [
                            int(r) for r in rs.split('x')
                        ]
                if "Frequencies: " in x:
                    try:
                        refresh = int(float(x.split(',')[-1].strip()[:-3]))
                    except Exception:
                        pass
                if 'Year of Manufacture' in x:
                    year = x.split(': ')[1]

                if 'Week of Manufacture' in x:
                    week = x.split(': ')[1]

                if "Size: " in x:
                    size = self.get_size_monitor(x)
            technology = next((t for t in TECHS if t in c[0]), None)

            if year and week:
                d = '{} {} 0'.format(year, week)
                production_date = datetime.strptime(d, '%Y %W %w').isoformat()

            self.components.append(
                {
                    "actions": [],
                    "type": "Display",
                    "model": model,
                    "manufacturer": manufacturer,
                    "serialNumber": serial,
                    'size': size,
                    'resolutionWidth': resolution_width,
                    'resolutionHeight': resolution_height,
                    "productionDate": production_date,
                    'technology': technology,
                    'refreshRate': refresh,
                }
            )

    def get_hwinfo_monitors(self):
        for c in self.hwinfo:
            monitor = None
            external = None
            for x in c:
                if 'Hardware Class: monitor' in x:
                    monitor = c
                if 'Driver Info' in x:
                    external = c

            if monitor and not external:
                self.monitors.append(c)

    def get_size_monitor(self, x):
        i = 1 / 25.4
        t = x.split('Size: ')[-1].strip()
        tt = t.split('mm')
        if not tt:
            return 0
        sizes = tt[0].strip()
        if 'x' not in sizes:
            return 0
        w, h = [int(x) for x in sizes.split('x')]
        return "{:.2f}".format(np.sqrt(w**2 + h**2) * i)

    def get_cpu_address(self, cpu):
        default = 64
        for ch in self.lshw.get('children', []):
            for c in ch.get('children', []):
                if c['class'] == 'processor':
                    return c.get('width', default)
        return default

    def get_usb_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "USB" in u.get("Port Type", "").upper()
            ]
        )

    def get_serial_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "SERIAL" in u.get("Port Type", "").upper()
            ]
        )

    def get_firmware_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "FIRMWARE" in u.get("Port Type", "").upper()
            ]
        )

    def get_pcmcia_num(self):
        return len(
            [
                u
                for u in self.dmi.get("Port Connector")
                if "PCMCIA" in u.get("Port Type", "").upper()
            ]
        )

    def get_bios_date(self):
        return self.dmi.get("BIOS")[0].get("Release Date", self.default)

    def get_firmware(self):
        return self.dmi.get("BIOS")[0].get("Firmware Revision", '1')

    def get_max_ram_size(self):
        size = 0
        for slot in self.dmi.get("Physical Memory Array"):
            capacity = slot.get("Maximum Capacity", '0').split(" ")[0]
            size += int(capacity)

        return size

    def get_ram_slots(self):
        slots = 0
        for x in self.dmi.get("Physical Memory Array"):
            slots += int(x.get("Number Of Devices", 0))
        return slots

    def get_ram_size(self, ram):
        memory = ram.get("Size", "0")
        return memory

    def get_ram_speed(self, ram):
        size = ram.get("Speed", "0")
        return size

    def get_cpu_speed(self, cpu):
        speed = cpu.get('Max Speed', "0")
        return speed

    def get_sku(self):
        return self.dmi.get("System")[0].get("SKU Number", self.default).strip()

    def get_version(self):
        return self.dmi.get("System")[0].get("Version", self.default).strip()

    def get_uuid(self):
        return self.dmi.get("System")[0].get("UUID", '').strip()

    def get_family(self):
        return self.dmi.get("System")[0].get("Family", '')

    def get_chassis(self):
        return self.dmi.get("Chassis")[0].get("Type", '_virtual')

    def get_type(self):
        chassis_type = self.get_chassis()
        return self.translation_to_devicehub(chassis_type)

    def translation_to_devicehub(self, original_type):
        lower_type = original_type.lower()
        CHASSIS_TYPE = {
            'Desktop': [
                'desktop',
                'low-profile',
                'tower',
                'docking',
                'all-in-one',
                'pizzabox',
                'mini-tower',
                'space-saving',
                'lunchbox',
                'mini',
                'stick',
            ],
            'Laptop': [
                'portable',
                'laptop',
                'convertible',
                'tablet',
                'detachable',
                'notebook',
                'handheld',
                'sub-notebook',
            ],
            'Server': ['server'],
            'Computer': ['_virtual'],
        }
        for k, v in CHASSIS_TYPE.items():
            if lower_type in v:
                return k
        return self.default

    def get_chassis_dh(self):
        chassis = self.get_chassis()
        lower_type = chassis.lower()
        for k, v in CHASSIS_DH.items():
            if lower_type in v:
                return k
        return self.default

    def get_data_storage_type(self, x):
        # TODO @cayop add more SSDS types
        SSDS = ["nvme"]
        SSD = 'SolidStateDrive'
        HDD = 'HardDrive'
        type_dev = x.get('device', {}).get('type')
        trim = x.get('trim', {}).get("supported") in [True, "true"]
        return SSD if type_dev in SSDS or trim else HDD

    def get_data_storage_interface(self, x):
        interface = x.get('device', {}).get('protocol', 'ATA')
        if interface.upper() in DATASTORAGEINTERFACE:
            return interface.upper()

        txt = "Sid: {}, interface {} is not in DataStorageInterface Enum".format(
            self.sid, interface
        )
        self.errors("{}".format(err))

    def get_data_storage_size(self, x):
        return x.get('user_capacity', {}).get('bytes')

    def parse_hwinfo(self):
        hw_blocks = self.hwinfo_raw.split("\n\n")
        return [x.split("\n") for x in hw_blocks]

    def loads(self, x):
        if isinstance(x, str):
            try:
                try:
                    hw = json.loads(x)
                except json.decoder.JSONDecodeError:
                    hw = json.loads(repair_json(x))
                return hw
            except Exception as ss:
                logger.warning("%s", ss)
                return {}
        return x

    def errors(self, txt=None):
        if not txt:
            return self._errors

        logger.error(txt)
        self._errors.append("%s", txt)

