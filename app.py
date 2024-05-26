from flask import Flask, abort, make_response, request, jsonify
import psycopg2 as psy2
import os
import dotenv
from markupsafe import escape
import requests

# Instanciando Flask
app = Flask(__name__)

# Configurando database
dotenv.load_dotenv()

db_name = os.getenv("DB_NAME")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_port = os.getenv("DB_PORT")

try:
    conn = psy2.connect(database=db_name, user=db_user, password=db_password, host=db_host, port=db_port)
    cursor = conn.cursor()
except Exception as e:
    print(f"Error connecting to the database: {e}")
    raise

def validate_user_data(data):
    required_fields = ['name', 'cpf_cnpj', 'password', 'email', 'balance']
    for field in required_fields:
        if field not in data:
            return False, f"Missing field: {field}"
    return True, ""

@app.post("/create_user")
def create_user():
    if not request.is_json:
        return make_response(jsonify("Invalid input"), 400)
    
    data = request.json
    is_valid, message = validate_user_data(data)
    if not is_valid:
        return make_response(jsonify(message), 400)
    
    user_data = [
        escape(data['name']),
        escape(data['cpf_cnpj']),
        escape(data['password']),
        escape(data['email']),
        escape(data['balance'])
    ]

    is_seller = escape(data.get('is_seller', False))
    user_data.append(is_seller)

    try:
        cursor.execute(
            "INSERT INTO users (name, cpf_cnpj, password, email, balance, is_seller) VALUES (%s, %s, %s, %s, %s, %s)",
            user_data
        )
        conn.commit()
        return make_response(jsonify('User created successfully'), 201)
    except:
        return make_response(jsonify("This user already exists"), 400)

@app.get('/get_all_users')
def get_all_users():
    try:
        cursor.execute("SELECT id, name, cpf_cnpj, balance, is_seller FROM users")
        columns = ['id', 'name', 'cpf_cnpj', 'balance', 'is_seller']
        user_selected = cursor.fetchall()
        users = [dict(zip(columns, row)) for row in user_selected]
        return jsonify(users)
    except Exception as e:
        print(f"Error: {e}")
        abort(500)

@app.post('/transfer')
def transfer():
    authorize_service_url = r'https://util.devi.tools/api/v2/authorize'
    notify_service_url = r'https://util.devi.tools/api/v1/notify' 
    if not request.is_json:
        return make_response(jsonify("Invalid input"), 400)
    
    try:
        data = request.json
        payee_id = escape(data['payee'])
        payer_id = escape(data['payer'])
        value = float(escape(data['value']))

        if payee_id == payer_id:
            return make_response(jsonify('Payee and Payer are the same'), 400)

        authorized = requests.get(authorize_service_url).json().get('data', {}).get('authorization')
        if not authorized:
            return make_response(jsonify('Not authorized to make the transfer'), 401)
        
        cursor.execute("SELECT is_seller FROM users WHERE id = %s", [payer_id])
        is_seller = cursor.fetchone()
        if is_seller and is_seller[0]:
            return make_response(jsonify('A seller cannot make a deposit'), 400)
        
        cursor.execute('SELECT balance FROM users WHERE id = %s', [payer_id])
        payer_balance = cursor.fetchone()
        if payer_balance is None or payer_balance[0] < value:
            return make_response(jsonify('Payer does not have enough balance'), 400)

        cursor.execute('UPDATE users SET balance = balance + %s WHERE id = %s', [value, payee_id])
        cursor.execute('UPDATE users SET balance = balance - %s WHERE id = %s', [value, payer_id])
        cursor.execute('INSERT INTO log_transfers (payee, payer, value) VALUES (%s, %s, %s)', [payee_id, payer_id, value])
        conn.commit()
        requests.post(notify_service_url)
        return make_response(jsonify('Transfer completed successfully'), 200)
    except psy2.DatabaseError as e:
        print(f"Database error: {e}")
        conn.rollback()
        return make_response(jsonify("Internal server error"), 500)
    except Exception as e:
        print(f"Error: {e}")
        return make_response(jsonify("Internal server error"), 500)

if __name__ == "__main__":
    app.run(debug=True)
