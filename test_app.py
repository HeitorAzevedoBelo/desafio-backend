import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_create_user(client):
    new_user = {
        'name': 'Test User',
        'cpf_cnpj': '12345678901',
        'password': 'password',
        'email': 'test@example.com',
        'balance': 1000.0
    }
    response = client.post('/create_user', json=new_user)
    assert response.status_code == 201
    assert b'User created successfully' in response.data

def test_get_all_users(client):
    response = client.get('/get_all_users')
    assert response.status_code == 200

def test_transfer(client):
    transfer_data = {
        'payee': '1',
        'payer': '2',
        'value': 50.0
    }
    response = client.post('/transfer', json=transfer_data)
    assert response.status_code in [200, 400, 401]