from core.privacy import hash_identifier,scrub
def test_hmac_deterministic_and_salted(monkeypatch):
    monkeypatch.setenv('SHG_SALT','a'); x=hash_identifier('99999 99999'); assert len(x)==64 and x==hash_identifier('9999999999'); assert x!=hash_identifier('9999999999','b'); assert '9999999999' not in scrub('call 9999999999')
