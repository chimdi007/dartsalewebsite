import platform
import subprocess

# Function to install dependencies based on OS
def install_dependencies():
    # Determine the OS
    client_os = platform.system()
    
    # Install dependencies based on OS
    if client_os == 'Windows':
        subprocess.call(['pip', 'install', '-r', 'requirements.txt'])
    elif client_os == 'Linux':
        subprocess.call(['pip3', 'install', '-r', 'requirements.txt'])
    elif client_os == 'Darwin':  # macOS
        subprocess.call(['pip3', 'install', '-r', 'requirements.txt'])
    else:
        print("Unsupported OS. Please install dependencies manually.")

# Run the function to install dependencies
#install_dependencies()


#IMPORTS##########################################################################################
from flask import Flask, request, url_for, render_template, redirect, flash, session, jsonify, make_response, json
import jwt
import os
import mysql.connector
import requests
import time
from datetime import datetime, timedelta
import uuid
import hashlib
from flask_mail import Mail
from flask_mail import Message
from urllib.parse import urlparse, parse_qs
from werkzeug.middleware.proxy_fix import ProxyFix
from comms import comms_bp

app = Flask(__name__)
app.register_blueprint(comms_bp, url_prefix='/comms')
app.secret_key = os.urandom(24)

# Configure ProxyFix with the appropriate number of proxies
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['TRUSTED_PROXIES'] = ['127.0.0.1']
app.config['PREFERRED_URL_SCHEME'] = 'https'
#app.config['SERVER_NAME'] = 'dartfox.org'
app.config['MAIL_SERVER'] = 'mail.privateemail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'mail@dartfox.org'
app.config['MAIL_PASSWORD'] = 'Blackcat111@'
app.config['MAIL_DEFAULT_SENDER'] = 'mail@dartfox.org'





mail = Mail(app)

#SPECIAL FUNCTIONS BANK
######################################################################################################

def generate_unique_id():
    # Generate a unique ID starting with 'df'
    unique_id = 'df' + str(uuid.uuid4())[:9]
    return unique_id

def hashed_password(password):
    # Hash the password using SHA-256 algorithm
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    return hashed_password



def send_email(subject, recipient, body):
    msg = Message(subject, recipients=[recipient])
    msg.body = body
    mail.send(msg)
    return 'Success!'


def generate_reset_token(email):
    timestamp = time.time()
    expiry = timestamp + 300
    data = f"{email}{timestamp}"
    token = hashlib.sha256(data.encode()).hexdigest()
    return token, expiry

def verify_reset_token(email, token, expiry):
    current_time = time.time()
    if current_time > expiry:
        return "token has expired"
    else:
        data = f"{email}{expiry-300}"
        regenerated_token = hashlib.sha256(data.encode()).hexdigest()
        return token == regenerated_token
    
@app.route('/email_verification', methods=['POST','GET'])
def email_verification():
    token = request.args.get('token')
    email = request.args.get('email')
    expiry = float(request.args.get('expiry'))
    if verify_reset_token(email, token, expiry) == True:
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("UPDATE users SET verification_status = 'verified' WHERE email =%s", (email,))
        connection.commit()
        cursor.close()
        connection.close()
        return f"Email verified! <a href='{url_for('auth')}'>Login</a>"
    else:
        return "Invalid or expired link."
    
@app.route('/verify_email/<email>', methods=['GET'])
def send_verification_email(email):
    email = email
    token, expiry = generate_reset_token(email)
    verification_link = url_for('email_verification', token=token, expiry=expiry, email=email, _external=True)
    msg = Message('EMAIL VERIFICATION', recipients=[email])
    msg.body = f'''To reset your password, click the following link:
    {verification_link}

    This link expires in 5minutes.
            '''
    mail.send(msg)
    return f"Email verification link sent to your email"
    
    
    
    
    
@app.route('/update_password', methods=['POST'])
def update_password():
    if request.method == 'POST':
        email = request.form['email']
        token = request.form['token']
        expiry = float(request.form['expiry'])
        password = request.form['new_password']
        hash_password = hashed_password(password)
        if verify_reset_token(email, token, expiry) ==True:
            try: 
                connection = config_db()
                cursor = connection.cursor()
                cursor.execute("UPDATE users SET hash_password =%s WHERE email = %s", (hash_password, email))
                connection.commit()
                cursor.close()
                connection.close()
                event_time = lambda: datetime.utcfromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M')
                tt = event_time()
                subject = 'Password Change Alert!'
                recipient = email
                body = f"Your password was changed on {tt}. If you did not make this change, please contact us."
                return send_email(subject, recipient, body)
            except Exception as e:
                return f"Error updating password:{e}"
        else:
            return f"Session has expired, <a href='{url_for('auth')}'>resend new password link</a>"



@app.route('/reset_password', methods=['GET'])    
def reset_password():
    token = request.args.get('token')
    email = request.args.get('email')
    expiry = float(request.args.get('expiry'))
    if verify_reset_token(email, token, expiry) == True:
            # Redirect to the reset password page
            return render_template('reset_password.html', email=email, token=token, expiry=expiry)
    else:
        return "Invalid or expired reset link."
    
    
    
@app.route('/forgot_password', methods=['POST'])
def send_reset_email():
    if request.method == 'POST':
        email = request.form['email']
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM users WHERE email =%s", (email,))
        user = cursor.fetchone()
        if user:
            
            try:
                token, expiry = generate_reset_token(email)
                reset_link = url_for('reset_password', token=token, expiry=expiry, email=email, _external=True)
                msg = Message('Password Reset Request', recipients=[email])
                msg.body = f'''To reset your password, click the following link:
                {reset_link}

            If you did not make this request, simply ignore this email.
            '''
                mail.send(msg)
                return f"password reset link sent to your email"
            except Exception as e:
                return f"Erro sending reset link {str(e)}"
        else:
            return f"email not in our records, do you want to <a href='/auth'>sign up</a> instead?"

#####################################################################################################

@app.route('/auth')
def auth():
    return render_template('login.html')

#AUTHENTICATION##############################################
@app.route('/config_db', methods=['POST', 'GET'])
def config_db():
# Establish database connection
        connection = mysql.connector.connect(
            host='192.168.1.100',
            user='dartboss',
            password='Blackcat111@',
            database='dartsale'
        )
        print("Database open")
        
        # Return the database connection object
        return connection



#creating users table
@app.route('/create_user_table', methods =['GET'])
def create_users_table():
   try:
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            unique_id VARCHAR(255) NOT NULL,
            name VARCHAR(255),
            email VARCHAR(255) NOT NULL,
            hash_password VARCHAR(255) NOT NULL,
            verification_status ENUM('unverified', 'verified') DEFAULT 'unverified',
            CONSTRAINT unique_unique UNIQUE (unique_id, email)
        )
    """)
        connection.commit()
        cursor.close()
        connection.close()
        return f"Usertable creation successful!"
   except Exception as e:
       return f"user table creation unsuccessful {e}"
   


#UNAUTHENTICATED PAGES##########################


#_________________________________AUTHENTICATION__________________________________
@app.route('/signup', methods=['POST'])
def signup():
    #Create users table if not exists
    create_users_table()
    if 'name' not in request.form or 'email' not in request.form or 'password' not in request.form:
                return 'Please provide all required information.', 400
    try:

        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            hash_password = hashed_password(password)  
            unique_id = generate_unique_id()

            #Open database and create a cursor connection
            connection = config_db()
            cursor = connection.cursor()

            #Check if user already exists
            cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                return f"User already exists, <a href=\"{url_for('auth')}\">Login</a>", 400

            # Execute SQL command to insert user data into users table
            else:
                cursor.execute("""
                    INSERT INTO users (unique_id, name, email, hash_password)
                    VALUES (%s, %s, %s, %s)
                    """, (unique_id, name, email, hash_password))

            # Commit changes and close cursor and connection
            connection.commit()
            cursor.close()
            connection.close()
            send_verification_email(email)
            
            return f"Signup successful! Proceed to <a href=\"{url_for('auth')}\">Login</a>", 200


    except Exception as e:
        print("Error:", e)
        return "Error: Could not sign up user"

    


@app.route('/login', methods=['POST'])
def login():
    if request.method== 'POST':
        try:
            connection = config_db()
            cursor = connection.cursor()
            email = request.form['email']
            password = request.form['password']
            hash_password = hashed_password(password)

            # Execute SQL command to retrieve user data from clients table
            cursor.execute("SELECT unique_id, name, email, verification_status FROM users WHERE email = %s AND hash_password = %s", (email, hash_password))
            user = cursor.fetchone()

            if user:
                session['email'] = email
                session['unique_id'] = user[0]
                session['name'] = user[1]
                session['verification_status']= user[3]
                flash('login successful!')
                return redirect(url_for('dashboard'))
            else:
                return f"Invalid email or password! Login or signup <a href=\"{url_for('auth')}\">here</a>", 401

        except Exception as e:
            print("Error:", e)
            return "Error: Could not log in user"

        finally:
            # Close cursor and connection
            cursor.close()
            connection.close()
    
    else:
        return f"method not allowed"
    
#LOGOUT#########
@app.route('/logout')
def logout():
    shops.clear()
    session.clear()
    return render_template('index.html')


#_______________________________________________________________________
#_____________________________GLOBAL PARAMETERS_________________________

shops = []
client = []


#_________________________________PAGES_________________________________

@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')


@app.route('/auth')
def join():
    return render_template('login.html')

 

@app.route('/dashboard')
def dashboard():
    global client, shops
    shops.clear()
    page_parameters()
    if 'email' in session:
        
        return render_template('dashboard.html', client=client, shops=shops)
    else:
        return f"session expire! Please <a href=\"{url_for('auth')}\">login again</a>!", 401
    

def page_parameters():
    global client, shops
    if 'email' in session:
        try:
           
            unique_id = session['unique_id']
            name = session['name']
            email = session['email']
            verification_status = session['verification_status']
            
            connection = config_db()
            cursor = connection.cursor(dictionary=True)
            cursor.execute("SELECT * FROM shops WHERE user_unique_id = %s", (unique_id,))
            fetched_shops = cursor.fetchall()
            for shop in fetched_shops:
                shop_name = shop['shop_name']
                shop_key = shop['shop_key']
                expiry = shop['expiry']
                today = datetime.now().date()
                status = 'active' if expiry > today else 'inactive'
                shop_password = shop['shop_password']
                shops.append({'shop_name': shop_name, 'shop_key': shop_key, 'expiry': expiry, "status":status, 'shop_password': shop_password})
            
            client = {'name': name, 'email': email, 'unique_id': unique_id, 'verification_status': verification_status}
            return
        except Exception as e:
            return f"Error {str(e)}", 500





#_____________________________SHOP MANAGEMENT SECTION__________________________________________

def generate_shop_key(length=6):
    # Generate a random UUID
    random_uuid = uuid.uuid4().hex.upper()
    # Take the first 'length' characters of the UUID
    key = "SK"+random_uuid[:length]
    return key



    
@app.route('/create_shop', methods=['POST'])
def create_shop():
    try:
        data = request.get_json()
        email = data.get('email')
        user_unique_id = data.get('unique_id')
        subscription = int(data.get('subscription'))
        shop_name = data.get('shop_name')
        shop_key = generate_shop_key()
        shop_password = data.get('shop_password') 
        promo_code = data.get('promo_code')
        expiry = datetime.now() + timedelta(days=subscription)
        
        username = "admin"  #for creation of admin staff access to 
        access_level = "admin"
        name = "admin"

        connection = config_db()
        cursor = connection.cursor()

        #print("email:", email, "id:", user_unique_id, "sub:", subscription, "shop name:", shop_name, "shop key:", shop_key, "promo code:", promo_code, "expiry:", expiry)
            
        # Allow only verified accounts to create shops
        cursor.execute("SELECT 1 FROM users WHERE verification_status = 'verified' AND unique_id = %s", (user_unique_id,))
        verified = cursor.fetchone()

        if verified:
            #print("We got up to this far")
            #print(f"Creating shop with data: {data}")
            # Check if user already has a shop or if shop name is already taken
            cursor.execute("SELECT 1 FROM shops WHERE shop_name = %s AND user_unique_id = %s", (shop_name, user_unique_id))
            existing_shop = cursor.fetchone()

            if existing_shop:
                return jsonify(message="Shop already exists! Choose a different 'shop name'."), 400
            else:
                cursor.execute("""INSERT INTO shops (user_unique_id, shop_key, shop_name, subscription, expiry, shop_password) 
                                  VALUES (%s, %s, %s, %s, %s, %s)""", 
                               (user_unique_id, shop_key, shop_name, subscription, expiry, shop_password))
                connection.commit()
                
                #create first user
                cursor.execute("""INSERT INTO staffing (user_unique_id, shop_key, shop_name, username, access_level, password, name)
                               VALUES(%s, %s, %s, %s, %s, %s, %s)""", (user_unique_id, shop_key, shop_name, username, access_level, shop_password, name))
                connection.commit()
                #print("Shop and admin user created successfully")
                cursor.close()
                connection.close()
                return jsonify(message="Shop creation successful!"), 200
        else:
            return jsonify(message=f"You must <a href='{url_for('send_verification_email', email=email)}'>verify your email</a> before you can use this service"), 403
    except Exception as e:
        print(f"Error creating shop: {str(e)}")
        return jsonify(error=f"Error creating shop: {str(e)}"), 500
    


    
    
@app.route('/change_password', methods=['POST'])
def change_password():
    data = request.get_json()
    email = data.get('email')
    old_password= data.get('old_password')
    new_password= data.get('new_password')
    print(email, old_password, new_password)
    hash_old_password = hashed_password(old_password)
    hash_new_password = hashed_password(new_password)
    connection=config_db()
    cursor=connection.cursor()
        #verify old password
    cursor.execute("SELECT 1 FROM users WHERE email=%s AND hash_password=%s", (email, hash_old_password))
    verified_user=cursor.fetchone()
    if verified_user:
        try:
            cursor.execute("UPDATE users SET hash_password=%s",(hash_new_password,))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify(message="Password successfully updated!"), 200
        except Exception as e:
            return jsonify(message=f"Error: {str(e)}"), 500
            
    else:
        return jsonify(message="incorrect old password!"), 401

#______________________________SHOP SETTINGS__________________________________


@app.route('/shop_settings', methods=['POST'])
def shop_settings():
    try:
        data = request.get_json()
        user_unique_id = data.get('user_unique_id')
        shop_key = data.get('shop_key')
        shop_name = data.get('shop_name')
        shop_password = data.get('shop_password')
        vat = data.get('vat')
        currency = data.get('currency')
        
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("""UPDATE shops SET shop_password=%s, vat=%s, currency=%s WHERE user_unique_id=%s AND shop_key=%s AND shop_name=%s""",
                    (shop_password, vat, currency, user_unique_id, shop_key, shop_name))
        connection.commit()
        cursor.close()
        connection.close()
        #print("Data: ", data)
        return jsonify(message="Settings saved!"), 200
    except Exception as e:
        return jsonify(message="Error saving settings"), 500

#____________________________________________________________________________



@app.route('/manage_shop', methods=['POST'])
def manage_shop():
    global client
    if 'unique_id' in session and request.method == 'POST':
        inventory = []
        users = []
        logs =[]
        user_unique_id = session['unique_id']
        shop_name = request.form['shop_name']
        shop_key = request.form['shop_key']
        #shop_password = request.form['shop_password']

        connection = config_db()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT * FROM inventory 
            WHERE user_unique_id = %s AND shop_key = %s
        """, (user_unique_id, shop_key))
        
        fetched_inventory = cursor.fetchall()
        for i in fetched_inventory:
            item = i['item']
            description = i['description']
            sku = i['sku']
            upc = i['upc']
            quantity = i['quantity']
            price = i['price']
            inventory.append({
                'item': item, 
                'description': description, 
                'sku': sku, 
                'upc': upc, 
                'quantity': quantity, 
                'price': price
            })

        # Fetch shop config        
        
        cursor.execute("""
            SELECT * FROM shops 
            WHERE user_unique_id = %s AND shop_key = %s AND shop_name = %s
        """, (user_unique_id, shop_key, shop_name))
        
        shop = cursor.fetchone()
        if shop:
            date = shop['date']
            subscription =shop['subscription']
            subscription_type = "6 monthly" if subscription == 183 else "yearly"
            expiry = shop['expiry']
            today = datetime.now().date()
            status = 'active' if expiry > today else 'inactive'
            currency = shop['currency']
            vat = shop['vat']
            shop_password = shop['shop_password']
            last_backup = shop['last_backup']
            
            
            cursor.execute("SELECT * FROM staffing where user_unique_id=%s AND shop_key=%s", (user_unique_id, shop_key))
            staffs = cursor.fetchall()
            if staffs:
                for staff in staffs:
                    name = staff['name']
                    username = staff['username']
                    access_level = staff['access_level']
                    password = staff['password']
                    staff_date = staff['date']
                    users.append({
                        "name":name,
                        "username":username,
                        "access_level":access_level,
                        "password":password,
                        "staff_date":staff_date})
            else:
                users = None
                
            config = {
                "user_unique_id": user_unique_id,
                "shop_name":shop_name,
                "shop_key": shop_key,
                "date":date,
                "subscription_type": subscription_type,
                "status": status,
                "expiry": expiry,
                "currency": currency,
                "vat": vat,
                "shop_password": shop_password,
                "last_backup":last_backup
                }

            
            cursor.execute("SELECT * FROM inv_sync WHERE user_unique_id=%s AND shop_key=%s", (user_unique_id, shop_key))
            activity_log = cursor.fetchall()
            if not activity_log:
                logs =[]
            for l in activity_log:
                date = l['date']
                status = l['status']
                action = l['action']
                activity = 'added new stock' if action == 'add' else 'updated inventory' if action == 'update' else 'removed item from inventory'
                sku = l['sku']
                item = l['item']
                price = l['price']
                quantity = l['quantity']
                logs.append({
                    'date':date,
                    'activity':activity,
                    'sku':sku,
                    'item':item,
                    'quantity':quantity,
                    'price':price,
                    'status':status
                })
            return render_template('manageshop.html', config=config, users=users, inventory=inventory, client=client, logs=logs)
        else:
            return f"details does not match our records!", 400
            
        
    else:
        return f"session expire! Please <a href=\"{url_for('auth')}\">login again</a>!", 401
    

    

    




@app.route('/create_new_user', methods=['POST'])
def create_new_user():
    try:
        data = request.get_json()
        name = data.get('name')
        username = data.get('username')
        access_level = data.get('access_level')
        password = data.get('password')
        user_unique_id = data.get('user_unique_id')
        shop_key = data.get('shop_key')
        shop_password = data.get('shop_password')
        shop_name = data.get('shop_name')

        connection = config_db()
        cursor = connection.cursor()

        # Authenticate shop
        cursor.execute("SELECT 1 FROM shops WHERE user_unique_id = %s AND shop_key = %s AND shop_password = %s", (user_unique_id, shop_key, shop_password))
        authenticated = cursor.fetchone()

        if authenticated:
            # Insert new user
            cursor.execute("""INSERT INTO staffing (user_unique_id, shop_key, shop_name, name, username, access_level, password)
                              VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                           (user_unique_id, shop_key, shop_name, name, username, access_level, password))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify({"message": "User created successfully!", "ok": True}), 200
        else:
            return jsonify({"message": "Authentication failed. Invalid shop credentials.", "ok": False}), 403
    except Exception as e:
        print(f"Error creating user: {str(e)}")
        return jsonify({"message": f"Error creating user: {str(e)}", "ok": False}), 500


@app.route('/delete_user', methods=['POST'])
def delete_user():
    try:
        data = request.get_json()
        
        if not data:
            return jsonify(message="missing details missing"), 400
        
        user_unique_id = data.get('user_unique_id')
        shop_key = data.get('shop_key')
        name = data.get('name')
        username = data.get('username')
        print("Data: ", data)
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("""DELETE FROM staffing WHERE user_unique_id=%s AND shop_key=%s AND name=%s AND username=%s""",
                    (user_unique_id, shop_key, name, username))
        connection.commit()
        cursor.close()
        connection.close()
        return jsonify(message="User deleted!!!"), 200
    except Exception as e:
        return jsonify(message=f"Error: {str(e)}"), 500




@app.route('/update_stock', methods=['POST']) #END POINT FOR ADDING NEW STOCK, AND FOR UPDATING PRICE/QUANTITY
def update_stock():
    print("WE GOT HERE!")
    data = request.get_json()
    user_unique_id = data.get('user_unique_id')
    shop_key = data.get('shop_key')
    #shop_password = data.get('shop_password')
    #shop_name = data.get('shop_name')
    item = data.get('item')
    description = data.get('description')
    sku = data.get('sku')
    upc = data.get('upc')
    price = data.get('price')
    quantity = data.get('quantity')
    action = data.get('action')
    status = 'pending'
    print("Data: ", data)
    try:
        connection = config_db()
        cursor = connection.cursor()
        cursor.execute("SELECT 1 FROM shops WHERE user_unique_id=%s AND shop_key=%s", (user_unique_id, shop_key))
        user = cursor.fetchone()
        if user:
            cursor.execute("""INSERT INTO inv_sync(user_unique_id, shop_key, item, description, sku, upc, price, quantity, status, action)
                           VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", (user_unique_id, shop_key, item, description, sku, upc, price, quantity, status, action))
            connection.commit()
            cursor.close()
            connection.close()
            return jsonify(message=f"Inventory Data successfully sent!"), 200
        else:
            return jsonify({"message": "Authentication failed. Invalid shop credentials.", "ok": False}), 403
    except Exception as e:
        print(str(e))
        return f"Error: {e}"
    
    
@app.route('/remove_stock', methods=['POST']) #END POINT FOR REMOVING ITEMS FROM INVENTORY
def remove_stock():
    try:
        data = request.get_json()
        sku = data.get('sku')
        user_unique_id = data.get('user_unique_id')
        shop_key = data.get('shop_key')
        shop_password = data.get('shop_password')
        status = 'pending'
        action = 'remove'

        if not sku or not user_unique_id or not shop_key:
            return jsonify(message="Missing required fields (sku, user_unique_id, shop_key)."), 400
        
        connection = config_db()
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT 1 FROM shops
            WHERE user_unique_id = %s AND shop_key = %s AND shop_password = %s
            """, (user_unique_id, shop_key, shop_password))
        authenticated = cursor.fetchone()

        if not authenticated:
            return jsonify(message="Unauthorized user!"), 401

        cursor.execute("""
            SELECT item, description, upc, price, quantity FROM inventory
            WHERE sku = %s AND user_unique_id = %s AND shop_key = %s
            """, (sku, user_unique_id, shop_key))
        item = cursor.fetchone()

        if not item:
            return jsonify(message="Item does not exist in your inventory!"), 400

        cursor.execute("""
            INSERT INTO inv_sync (user_unique_id, shop_key, item, description, sku, upc, price, quantity, status, action)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (user_unique_id, shop_key, item[0], item[1], sku, item[2], item[3], item[4], status, action))

        connection.commit()

        return jsonify(message="Item removal in progress."), 200
    
    except Exception as e:
        print(str(e))
        return jsonify(message="An error occurred while processing your request."), 500

    finally:
        cursor.close()
        connection.close()
#_______________________________________________________________________
    
    
#________________________RECORD EXPENSES__________________________
@app.route('/report_expenditure', methods=['POST'])
def report_expenditure():
    try:
        data = request.get_json()
        #print ("DATA: ", data)      #debug print
        user_unique_id = data.get('user_unique_id')
        shop_key = data.get('shop_key')
        attendant = data.get('reporter')
        location = data.get('location')
        category = data.get('category')
        description = data.get('description')
        price = data.get('amount')
        items = json.dumps([{"description": description, "category": category, "location": location, "price": price}])
        receipt_number =111
        transaction_type = 'debit'
        vat = 0.0
        date = datetime.now().strftime('%Y-%m-%d %H:%M')
        connection = config_db()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT 1 FROM shops WHERE user_unique_id=%s AND shop_key=%s", (user_unique_id, shop_key))
        user = cursor.fetchone()
        if user:
            cursor.execute("""INSERT INTO sales (user_unique_id, shop_key, receipt_number, date, items, transaction_type, attendant, price, vat, total)
                                  VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                               (user_unique_id, shop_key, receipt_number, date, items, transaction_type, attendant, price, vat, price))
            connection.commit()
        else:
            return jsonify(message="Invalid user or shop details"), 400
        
        cursor.close()
        connection.close()
        
        return jsonify(message="Expenditure recorded"), 200
    except Exception as e:
        print(f"Error: {e}")
        return jsonify(message=f"{str(e)}"), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=4004)