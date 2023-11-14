import uuid
import hashlib


class Iota:
    """
    Framework for simulate the comunication with IOTA DLT  
    """

    def issue_did(self):
        u = str(uuid.uuid4()).encode()
        d = hashlib.sha3_256(u).hexdigest()
        did = "did:iota:{}".format(d)
        return did


iota = Iota()
