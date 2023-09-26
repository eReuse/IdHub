import pytest
from ssikit import create_did
import re

# 'did:key:z6MkjtArtcgMSgV8aBdbFCFETqhFanLVRXcQPs7BeXyF5wdL'
def test_create_did():
    pattern = r"did:.*:[a-zA-Z0-9]+"

    result = create_did('key')
    assert result.startswith("did:")
    #assert re.match(result,'^did:[a-zA-Z]+:[a-zA-Z0-9]+') is not None

#test_create_did()