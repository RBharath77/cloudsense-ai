from fastapi.testclient import TestClient
from app.auth import hash_password, verify_password, create_token
from app.main import app
from app.database import SessionLocal
from app.models import User, Organization

client = TestClient(app)

def test_password_hash():
    h = hash_password('secret')
    assert h != 'secret'
    assert verify_password('secret', h)

def test_login_success_and_failure():
    # 1. Successful admin login
    res_ok = client.post('/api/auth/login', json={'email': 'admin@cloudsense.ai', 'password': 'CloudSense@123'})
    assert res_ok.status_code == 200
    data = res_ok.json()
    assert 'access_token' in data
    assert data['role'] == 'ADMIN'

    # 2. Invalid password
    res_bad = client.post('/api/auth/login', json={'email': 'admin@cloudsense.ai', 'password': 'WrongPassword!'})
    assert res_bad.status_code == 401
    assert 'Invalid email or password' in res_bad.json()['detail']

def test_auth_me_endpoint():
    # Login as admin
    res = client.post('/api/auth/login', json={'email': 'admin@cloudsense.ai', 'password': 'CloudSense@123'})
    assert res.status_code == 200
    token = res.json()['access_token']

    # Get /api/auth/me
    me_res = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data['email'] == 'admin@cloudsense.ai'
    assert me_data['role'] == 'ADMIN'
    assert 'organization_id' in me_data
    assert me_data['organization_name'] == 'CloudSense AI'

def test_logout_and_revocation():
    # Login as finops persona
    res = client.post('/api/auth/login', json={'email': 'finops@cloudsense.ai', 'password': 'CloudSense@123'})
    assert res.status_code == 200
    token = res.json()['access_token']

    # Verify authorized
    assert client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'}).status_code == 200

    # Logout
    logout_res = client.post('/api/auth/logout', headers={'Authorization': f'Bearer {token}'})
    assert logout_res.status_code == 200
    assert logout_res.json()['status'] == 'success'

    # Verify token is now revoked
    revoked_res = client.get('/api/auth/me', headers={'Authorization': f'Bearer {token}'})
    assert revoked_res.status_code == 401
    assert 'revoked' in revoked_res.json()['detail'].lower()

def test_forgot_and_reset_password():
    # 1. Forgot password request
    res = client.post('/api/auth/forgot-password', json={'email': 'auditor@cloudsense.ai'})
    assert res.status_code == 200
    code = res.json()['demo_code']

    # 2. Reset with wrong code
    res_bad = client.post('/api/auth/reset-password', json={
        'email': 'auditor@cloudsense.ai',
        'code': '999999',
        'new_password': 'NewPassword@123',
    })
    assert res_bad.status_code == 400

    # 3. Reset with valid code
    res_ok = client.post('/api/auth/reset-password', json={
        'email': 'auditor@cloudsense.ai',
        'code': code,
        'new_password': 'CloudSense@123',
    })
    assert res_ok.status_code == 200
    assert 'updated successfully' in res_ok.json()['message']

    # 4. Verify login with updated password
    login_res = client.post('/api/auth/login', json={'email': 'auditor@cloudsense.ai', 'password': 'CloudSense@123'})
    assert login_res.status_code == 200

def test_verify_otp_endpoint():
    res = client.post('/api/auth/forgot-password', json={'email': 'finops@cloudsense.ai'})
    assert res.status_code == 200
    otp = res.json()['otp']
    
    # Bad OTP
    bad_res = client.post('/api/auth/verify-otp', json={'email': 'finops@cloudsense.ai', 'code': '000000'})
    assert bad_res.status_code == 400

    # Good OTP
    ok_res = client.post('/api/auth/verify-otp', json={'email': 'finops@cloudsense.ai', 'code': otp})
    assert ok_res.status_code == 200
    assert ok_res.json()['verified'] is True

def test_admin_direct_user_password_reset():
    # Admin resets password for viewer@cloudsense.ai
    res = client.post('/api/admin/users/reset-password', json={
        'admin_email': 'admin@cloudsense.ai',
        'admin_password': 'CloudSense@123',
        'target_email': 'viewer@cloudsense.ai',
        'new_password': 'AdminResetPass@2026',
    })
    assert res.status_code == 200
    assert 'updated successfully by administrator' in res.json()['message']

    # Viewer logs in with new password
    login_res = client.post('/api/auth/login', json={
        'email': 'viewer@cloudsense.ai',
        'password': 'AdminResetPass@2026',
    })
    assert login_res.status_code == 200

    # Restore viewer's password for test consistency
    client.post('/api/admin/users/reset-password', json={
        'admin_email': 'admin@cloudsense.ai',
        'admin_password': 'CloudSense@123',
        'target_email': 'viewer@cloudsense.ai',
        'new_password': 'CloudSense@123',
    })

def test_registration_otp_flow():
    from app.main import REGISTRATION_PENDING
    from unittest.mock import patch
    import uuid
    
    test_email = f"newhire_{uuid.uuid4().hex[:8]}@cloudsense.ai"
    with patch('app.main.send_otp_email', return_value=(True, 'OTP dispatched')):
        req_res = client.post('/api/auth/register-request', json={
            'name': 'Dev User',
            'email': test_email,
            'password': 'SecurePass@1234',
        })
        assert req_res.status_code == 200
        assert 'verification code sent' in req_res.json()['message'].lower()
        
        # Verify pending record exists
        assert test_email in REGISTRATION_PENDING
        otp_code = REGISTRATION_PENDING[test_email]['otp']
        assert len(otp_code) == 6

        # Bad OTP fails
        bad_res = client.post('/api/auth/verify-registration-otp', json={
            'email': test_email,
            'code': '000000',
        })
        assert bad_res.status_code == 400

        # Valid OTP succeeds and creates account
        good_res = client.post('/api/auth/verify-registration-otp', json={
            'email': test_email,
            'code': otp_code,
        })
        assert good_res.status_code == 200
        token = good_res.json()['access_token']
        assert token is not None
        assert good_res.json()['email'] == test_email

def test_admin_direct_reset_by_id_without_otp():
    # 1. Admin logs in
    admin_login = client.post('/api/auth/login', json={
        'email': 'admin@cloudsense.ai',
        'password': 'CloudSense@123',
    })
    admin_token = admin_login.json()['access_token']
    headers = {'Authorization': f'Bearer {admin_token}'}

    # 2. Get list of workspace users
    users_res = client.get('/api/users', headers=headers)
    assert users_res.status_code == 200
    users = users_res.json()
    viewer_user = next((u for u in users if u['email'] == 'viewer@cloudsense.ai'), None)
    assert viewer_user is not None

    # 3. Admin directly resets viewer password WITHOUT ANY OTP
    reset_res = client.post(
        f"/api/users/{viewer_user['id']}/reset-password",
        headers=headers,
        json={'new_password': 'DirectAdminPass@2026'},
    )
    assert reset_res.status_code == 200
    assert 'updated successfully by administrator' in reset_res.json()['message']

    # 4. Viewer can immediately log in with new password
    v_login = client.post('/api/auth/login', json={
        'email': 'viewer@cloudsense.ai',
        'password': 'DirectAdminPass@2026',
    })
    assert v_login.status_code == 200

    # 5. Restore password back
    client.post(
        f"/api/users/{viewer_user['id']}/reset-password",
        headers=headers,
        json={'new_password': 'CloudSense@123'},
    )


