from app.auth import hash_password, verify_password

def test_password_hash():
    h=hash_password('secret'); assert h!='secret'; assert verify_password('secret',h)
