import json
import requests
import os
import random
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response, session, jsonify
from werkzeug.utils import secure_filename
from items import items


app = Flask(__name__)
app.secret_key = 'shopmodern_secret_key_12345'

# --- FILE UPLOAD CONFIGURATION ---
UPLOAD_FOLDER = os.path.join('static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- USER STORAGE HELPERS ---
USER_FILE = 'order_history.json'

import ast

def load_cart_cookie(cookie_val):
    if not cookie_val:
        return {}
    try:
        return json.loads(cookie_val)
    except Exception:
        try:
            data = ast.literal_eval(cookie_val)
            if isinstance(data, dict):
                return {str(k): v for k, v in data.items()}
            return {}
        except Exception:
            return {}

def load_users():
    credentials = []
    info = []
    orders = []
    
    if os.path.exists('user.json'):
        try:
            with open('user.json', 'r') as f:
                credentials = json.load(f)
        except Exception:
            pass
    if os.path.exists('information.json'):
        try:
            with open('information.json', 'r') as f:
                info = json.load(f)
        except Exception:
            pass
    if os.path.exists('order_history.json'):
        try:
            with open('order_history.json', 'r') as f:
                orders = json.load(f)
        except Exception:
            pass
            
    users_map = {}
    
    # 1. Load credentials
    for cred in credentials:
        email = cred.get('email', '')
        if email:
            users_map[email.lower()] = {
                'email': email,
                'password': cred.get('password', ''),
                'full_name': '',
                'phone': '+855 12 345 678',
                'created_at': '',
                'addresses': [],
                'payment_methods': [],
                'orders': []
            }
            
    # 2. Load information
    for inf in info:
        email = inf.get('email', '')
        key = email.lower()
        if key in users_map:
            users_map[key].update({
                'full_name': inf.get('full_name', ''),
                'phone': inf.get('phone', '+855 12 345 678'),
                'created_at': inf.get('created_at', ''),
                'addresses': inf.get('addresses', []),
                'payment_methods': inf.get('payment_methods', [])
            })
        else:
            users_map[key] = {
                'email': email,
                'password': '',
                'full_name': inf.get('full_name', ''),
                'phone': inf.get('phone', '+855 12 345 678'),
                'created_at': inf.get('created_at', ''),
                'addresses': inf.get('addresses', []),
                'payment_methods': inf.get('payment_methods', []),
                'orders': []
            }
            
    # 3. Load order history
    for ords in orders:
        email = ords.get('email', '')
        key = email.lower()
        if key in users_map:
            users_map[key]['orders'] = ords.get('orders', [])
        else:
            users_map[key] = {
                'email': email,
                'password': '',
                'full_name': '',
                'phone': '+855 12 345 678',
                'created_at': '',
                'addresses': [],
                'payment_methods': [],
                'orders': ords.get('orders', [])
            }
            
    return list(users_map.values())

def save_users(users):
    users_credentials = []
    users_info = []
    users_orders = []

    for u in users:
        email = u.get('email', '')
        users_credentials.append({
            'email': email,
            'password': u.get('password', '')
        })
        users_info.append({
            'email': email,
            'full_name': u.get('full_name', ''),
            'phone': u.get('phone', '+855 12 345 678'),
            'created_at': u.get('created_at', ''),
            'addresses': u.get('addresses', []),
            'payment_methods': u.get('payment_methods', [])
        })
        users_orders.append({
            'email': email,
            'orders': u.get('orders', [])
        })

    try:
        with open('user.json', 'w') as f:
            json.dump(users_credentials, f, indent=4)
    except Exception as e:
        print(f"Error saving to user.json: {e}")

    try:
        with open('information.json', 'w') as f:
            json.dump(users_info, f, indent=4)
    except Exception as e:
        print(f"Error saving to information.json: {e}")

    try:
        with open('order_history.json', 'w') as f:
            json.dump(users_orders, f, indent=4)
    except Exception as e:
        print(f"Error saving to order_history.json: {e}")
# --- TELEGRAM BOT CONFIGURATION ---
BOT_TOKEN = "8922443132:AAHOnR3EwkekjBiftr58oRRJ4PD3KI1yqOI"
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CHAT_ID = -1004385819802
@app.route('/')
def home():
    # This looks for index.html inside the 'templates' folder
    return render_template('customer/index.html',item=items)

@app.route('/product')
def products():
    return render_template('customer/products.html',item=items)

@app.route('/contact')
def contact():
    return render_template('customer/contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('username')
        password = request.form.get('password')

        users = load_users()
        user = next((u for u in users if u['email'].lower() == email.lower() and u['password'] == password), None)

        if user:
            user_created_at = user.get('created_at')
            if not user_created_at or user_created_at == 'Jan 2023':
                user_created_at = datetime.now().strftime("%b %Y")
                user['created_at'] = user_created_at
                save_users(users)
            session['user'] = {
                'email': user['email'],
                'full_name': user['full_name'],
                'profile_pic': user.get('profile_pic'),
                'phone': user.get('phone', '+855 12 345 678'),
                'created_at': user_created_at
            }
            return redirect(url_for('home'))
        else:
            error = "Invalid email or password"

    return render_template('share/login.html', error=error)

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if not full_name or not email or not password:
            error = "Please fill in all fields"
        elif password != confirm_password:
            error = "Passwords do not match"
        else:
            users = load_users()
            if any(u['email'].lower() == email.lower() for u in users):
                error = "An account with this email already exists"
            else:
                new_user = {
                    'full_name': full_name,
                    'email': email,
                    'password': password,
                    'orders': [],
                    'phone': '+855 12 345 678',
                    'created_at': datetime.now().strftime("%b %Y")
                }
                users.append(new_user)
                save_users(users)
                return redirect(url_for('login', registered='1'))

    return render_template('share/register.html', error=error)

@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect(url_for('login'))
    
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    now_str = datetime.now().strftime("%b %Y")
    
    # Setup addresses and payment methods defaults
    default_addresses = [
        {
            "id": "addr_1",
            "label": "Home",
            "recipient_name": session['user'].get('full_name', 'Alice Smith'),
            "recipient_phone": session['user'].get('phone', '+855 12 345 678'),
            "street": "#123, Street 271, Sangkat Boeung Keng Kang III",
            "city": "Phnom Penh",
            "country": "Cambodia",
            "is_default": True
        }
    ]
    
    default_payment_methods = [
        {
            "id": "pay_1",
            "type": "card",
            "card_brand": "Visa",
            "card_number": "•••• •••• •••• 4582",
            "cardholder_name": session['user'].get('full_name', 'Alice Smith'),
            "expiry": "12/28",
            "is_default": True
        },
        {
            "id": "pay_2",
            "type": "bakong",
            "account_name": session['user'].get('full_name', 'Alice Smith').lower().replace(" ", "_") + "@bakong",
            "wallet_label": "Bakong KHQR Wallet",
            "is_default": False
        }
    ]
    
    if current_user:
        orders = current_user.get('orders', [])
        created_at = current_user.get('created_at')
        if not created_at or created_at == 'Jan 2023':
            created_at = now_str
            current_user['created_at'] = now_str
            save_users(users)
        
        addresses = current_user.get('addresses')
        if not addresses:
            addresses = default_addresses
            current_user['addresses'] = addresses
            save_users(users)
            
        payment_methods = current_user.get('payment_methods')
        if not payment_methods:
            payment_methods = default_payment_methods
            current_user['payment_methods'] = payment_methods
            save_users(users)
            
        if session['user'].get('created_at') != created_at:
            session['user']['created_at'] = created_at
            session.modified = True
        member_since = created_at
    else:
        orders = []
        created_at = session['user'].get('created_at')
        if not created_at or created_at == 'Jan 2023':
            created_at = now_str
            session['user']['created_at'] = now_str
            session.modified = True
        member_since = created_at
        
        addresses = default_addresses
        payment_methods = default_payment_methods
        
        # Save to database to preserve fallback session
        new_user = {
            'full_name': session['user'].get('full_name', 'Alice Smith'),
            'email': email,
            'password': 'password123',
            'orders': orders,
            'phone': session['user'].get('phone', '+855 12 345 678'),
            'created_at': created_at,
            'addresses': addresses,
            'payment_methods': payment_methods
        }
        users.append(new_user)
        save_users(users)
        
    total_spent = sum(order.get('amount', 0.0) for order in orders)
    active_orders = sum(1 for order in orders if order.get('status') in ['Processing', 'In Transit'])
    reward_points = int(total_spent * 0.5)
    
    return render_template(
        'customer/profile.html',
        orders=orders,
        total_spent=total_spent,
        active_orders=active_orders,
        reward_points=reward_points,
        member_since=member_since,
        addresses=addresses,
        payment_methods=payment_methods
    )

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request data"}), 400
        
    new_name = data.get('full_name', '').strip()
    new_email = data.get('email', '').strip()
    new_phone = data.get('phone', '').strip()
    
    if not new_phone and 'user' in session:
        new_phone = session['user'].get('phone', '+855 12 345 678')
        
    if not new_name or not new_email or not new_phone:
        return jsonify({"status": "error", "message": "Name, email, and phone number are required"}), 400
        
    current_email = session['user']['email']
    users = load_users()
    
    # Check email collision
    if new_email.lower() != current_email.lower():
        if any(u['email'].lower() == new_email.lower() for u in users):
            return jsonify({"status": "error", "message": "An account with this email already exists"}), 400
            
    # Find and update the user record
    user_updated = False
    for u in users:
        if u['email'].lower() == current_email.lower():
            u['full_name'] = new_name
            u['email'] = new_email
            u['phone'] = new_phone
            user_updated = True
            break
            
    if not user_updated:
        # Fallback: recreate the user record if they are in the session but missing in storage
        session_created_at = session['user'].get('created_at')
        if not session_created_at or session_created_at == 'Jan 2023':
            session_created_at = datetime.now().strftime("%b %Y")
            session['user']['created_at'] = session_created_at
            session.modified = True
            
        new_user = {
            'full_name': new_name,
            'email': new_email,
            'password': 'password123',
            'orders': [],
            'phone': new_phone,
            'created_at': session_created_at
        }
        users.append(new_user)
        user_updated = True
        
    save_users(users)
    
    # Update the session
    session['user']['full_name'] = new_name
    session['user']['email'] = new_email
    session['user']['phone'] = new_phone
    session_created_at = session['user'].get('created_at')
    if not session_created_at or session_created_at == 'Jan 2023':
        session['user']['created_at'] = datetime.now().strftime("%b %Y")
    session.modified = True
    
    return jsonify({"status": "success", "message": "Profile updated successfully!"})

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request data"}), 400
        
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    confirm_password = data.get('confirm_password', '').strip()
    
    if not current_password or not new_password or not confirm_password:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    if new_password != confirm_password:
        return jsonify({"status": "error", "message": "New passwords do not match"}), 400
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    if current_user.get('password') != current_password:
        return jsonify({"status": "error", "message": "Incorrect current password"}), 400
        
    # Update password
    current_user['password'] = new_password
    save_users(users)
    
    return jsonify({"status": "success", "message": "Password updated successfully!"})

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/upload_profile_pic', methods=['POST'])
def upload_profile_pic():
    if 'user' not in session:
        response = make_response(json.dumps({"status": "error", "message": "Unauthorized"}))
        response.headers['Content-Type'] = 'application/json'
        return response, 401

    if 'profile_pic' not in request.files:
        response = make_response(json.dumps({"status": "error", "message": "No file uploaded"}))
        response.headers['Content-Type'] = 'application/json'
        return response, 400

    file = request.files['profile_pic']
    if file.filename == '':
        response = make_response(json.dumps({"status": "error", "message": "No file selected"}))
        response.headers['Content-Type'] = 'application/json'
        return response, 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        user_email = session['user']['email']
        safe_email = "".join([c if c.isalnum() else "_" for c in user_email])
        ext = filename.rsplit('.', 1)[1].lower()
        new_filename = f"profile_{safe_email}.{ext}"

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
        file.save(file_path)

        profile_pic_url = f"/static/uploads/{new_filename}"

        # Update user in order_history.json
        users = load_users()
        for user in users:
            if user['email'].lower() == user_email.lower():
                user['profile_pic'] = profile_pic_url
                break
        save_users(users)

        # Update session
        session['user']['profile_pic'] = profile_pic_url

        # Force session update flag
        session.modified = True

        response = make_response(json.dumps({
            "status": "success",
            "profile_pic_url": profile_pic_url
        }))
        response.headers['Content-Type'] = 'application/json'
        return response

    response = make_response(json.dumps({"status": "error", "message": "File type not allowed"}))
    response.headers['Content-Type'] = 'application/json'
    return response, 400

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    error = None
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        if not new_password or not confirm_password:
            error = "Password fields are required"
        elif new_password != confirm_password:
            error = "Passwords do not match"
        else:
            users = load_users()
            user = next((u for u in users if u['email'].lower() == email.lower()), None)
            
            if not user:
                # Fallback: auto-recreate the user record with the new password
                new_user = {
                    'full_name': 'Sinat Noun',
                    'email': email,
                    'password': new_password,
                    'orders': [],
                    'phone': '+855 12 345 678',
                    'created_at': datetime.now().strftime("%b %Y")
                }
                users.append(new_user)
                save_users(users)
                return redirect(url_for('login', reset_success='1'))
            else:
                user['password'] = new_password
                save_users(users)
                return redirect(url_for('login', reset_success='1'))
                
    return render_template('share/reset_password.html', error=error)

@app.route('/favorites')
def favorites():
    # Read favorites list from cookie
    fav_cookie = request.cookies.get('favorites')
    try:
        fav_ids = json.loads(fav_cookie) if fav_cookie else []
        if not isinstance(fav_ids, list):
            fav_ids = []
        else:
            fav_ids = [int(x) for x in fav_ids]
    except Exception:
        fav_ids = []
    
    # Filter catalog items matching IDs
    favorite_items = [itm for itm in items if itm['id'] in fav_ids]
    print(f"[FAVORITES ROUTE] cookie: {fav_cookie}, ids: {fav_ids}, count: {len(favorite_items)}")
    
    return render_template('customer/wishlist.html', favorite_items=favorite_items)

@app.route('/about')
def about():
    return render_template('customer/about.html')


@app.route('/view_product/<int:item_id>')
def view_product(item_id):
    # 1. Find the current product
    current_item = next((item for item in items if item['id'] == item_id), None)

    if not current_item:
        return "Product not found 404"

    # 2. Filter for related products (same category, exclude current product)
    related_products = [
        item for item in items
        if item['category'] == current_item['category'] and item['id'] != item_id
    ]



    # Pass both variables to the template
    return render_template(
        'customer/view_product.html',
        item=current_item,
        related_products=related_products
    )

# --- NEW: ADD TO CART ROUTE ---
@app.route('/add_to_cart/<int:item_id>', methods=['POST'])
def add_to_cart(item_id):
    # 1. Get the existing cart from cookies, or create an empty dict if it doesn't exist
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    # 2. Update the quantity of the item
    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1
    else:
        cart[str_item_id] = 1

    # 3. Handle response (traditional redirect or JSON AJAX)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1'
    if is_ajax:
        total_items_count = sum(cart.values())
        response = make_response(json.dumps({"status": "success", "cart_count": total_items_count}))
        response.headers['Content-Type'] = 'application/json'
    else:
        response = make_response(redirect(url_for('cart')))

    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)  # Lasts for 7 days
    return response

# --- UPDATED: CART ROUTE ---
@app.route('/cart')
def cart():
    # 1. Get the cart cookie
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    cart_items = []
    total_price = 0

    # 2. Match cookie item IDs with actual product details
    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    return render_template(
        'customer/cart.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )


# --- NEW: INCREASE QUANTITY ROUTE ---
@app.route('/increase_cart/<int:item_id>', methods=['POST'])
def increase_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart[str_item_id] += 1  # Add 1 to quantity

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


# --- NEW: DECREASE QUANTITY ROUTE ---
@app.route('/decrease_cart/<int:item_id>', methods=['POST'])
def decrease_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    str_item_id = str(item_id)
    if str_item_id in cart:
        if cart[str_item_id] > 1:
            cart[str_item_id] -= 1  # Reduce by 1 if greater than 1
        else:
            cart.pop(str_item_id)  # Remove entirely if quantity drops below 1

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response


# --- NEW: REMOVE SINGLE PRODUCT ROUTE ---
@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    str_item_id = str(item_id)
    if str_item_id in cart:
        cart.pop(str_item_id)  # Deletes this item key from the dictionary entirely

    response = make_response(redirect(url_for('cart')))
    response.set_cookie('cart', json.dumps(cart), max_age=60 * 60 * 24 * 7)
    return response

# --- BONUS: CLEAR CART ROUTE ---
@app.route('/clear_cart')
def clear_cart():
    response = make_response(redirect(url_for('cart')))
    response.delete_cookie('cart')
    return response


# --- NEW: CHECKOUT ROUTE ---
@app.route('/checkout')
def checkout():
    # 1. Read the cart from the cookie to calculate the final amount
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    cart_items = []
    total_price = 0

    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total
            cart_items.append({
                'product': product,
                'quantity': quantity,
                'item_total': round(item_total, 2)
            })

    # If the cart is empty, don't let them checkout; redirect back to home
    if not cart_items:
        return redirect(url_for('cart'))

    return render_template(
        'customer/checkout.html',
        cart_items=cart_items,
        total_price=round(total_price, 2)
    )


# --- NEW: PLACE ORDER ROUTE (Clears cart after fake payment) ---
# --- UPDATED: PLACE ORDER ROUTE WITH TELEGRAM NOTIFICATION ---
@app.route('/place_order', methods=['POST'])
def place_order():
    # 1. Grab buyer details directly from the submitted HTML form fields
    buyer_name = request.form.get('buyer_name')
    buyer_phone = request.form.get('buyer_phone')
    buyer_email = request.form.get('buyer_email')
    buyer_address = request.form.get('buyer_address')
    order_notes = request.form.get('order_notes', 'N/A')

    # 2. Re-read the cart from cookies to build the items list for Telegram
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)

    cart_items = []
    total_price = 0
    first_product_image = "https://www.stubbleandco.com/cdn/shop/files/the-tote-bag-black-front.jpg"  # Default Fallback

    # Loop to compile items list text
    item_list_text = ""
    for item_id_str, quantity in cart.items():
        product = next((item for item in items if str(item['id']) == item_id_str), None)
        if product:
            item_total = product['price'] * quantity
            total_price += item_total

            # Keep track of the first product's image to use as the main Telegram photo
            if not item_list_text:
                first_product_image = product['image']

            item_list_text += f"📦 <b>{product['title'][:25]}...</b>\n"
            item_list_text += f"   └ Qty: {quantity} × ${product['price']:.2f} = <b>${item_total:.2f}</b>\n\n"

    # If the cart was empty somehow, stop here
    if not cart_items and total_price == 0:
        return redirect(url_for('cart'))

    # 3. Construct clean, professional HTML formatted Telegram text
    telegram_text = f"<b>🔔 NEW KHQR ORDER RECEIVED</b>\n"
    telegram_text += f"<b>----------------------------------</b>\n\n"
    telegram_text += f"👤 <b>Customer:</b> {buyer_name}\n"
    telegram_text += f"📞 <b>Phone:</b> <code>{buyer_phone}</code>\n"
    telegram_text += f"📧 <b>Email:</b> <code>{buyer_email}</code>\n"
    telegram_text += f"📍 <b>Address:</b> {buyer_address}\n"
    telegram_text += f"📝 <b>Notes:</b> <i>{order_notes}</i>\n\n"
    telegram_text += f"<b>🛒 ORDER ITEMS:</b>\n"
    telegram_text += item_list_text
    telegram_text += f"<b>----------------------------------</b>\n"
    telegram_text += f"💰 <b>TOTAL PAID (KHQR): ${total_price:.2f} USD</b>"

    # 4. Fire payload to the Telegram Channel
    # Use text instead of photo + caption
    payload = {
        "text": telegram_text,
        "parse_mode": "HTML",
        "chat_id": CHAT_ID
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        telegram_response = requests.post(TELEGRAM_URL, json=payload, headers=headers)
        print(f"Telegram Bot Status: {telegram_response.status_code}")
    except Exception as e:
        print(f"Failed to push notification to Telegram: {e}")

    # 4.5 Save the order to order_history.json if user is logged in
    if 'user' in session:
        user_email = session['user']['email']
        users = load_users()
        user_found = False
        order_id = f"#ORD-{random.randint(10000, 99999)}"
        date_str = datetime.now().strftime("%b %d, %Y")
        new_order = {
            "order_id": order_id,
            "date": date_str,
            "amount": round(total_price, 2),
            "status": "Processing"
        }
        for u in users:
            if u['email'].lower() == user_email.lower():
                if 'orders' not in u:
                    u['orders'] = []
                u['orders'].append(new_order)
                user_found = True
                break
        if not user_found:
            # Fallback: recreate the user record if they are in session but missing in database file
            session_created_at = session['user'].get('created_at')
            if not session_created_at or session_created_at == 'Jan 2023':
                session_created_at = datetime.now().strftime("%b %Y")
                session['user']['created_at'] = session_created_at
                session.modified = True
            new_user = {
                'full_name': session['user'].get('full_name', buyer_name),
                'email': user_email,
                'password': 'password123',
                'orders': [new_order],
                'phone': session['user'].get('phone', buyer_phone),
                'created_at': session_created_at
            }
            users.append(new_user)
        save_users(users)

    # 5. Clear their shopping cart cookie and redirect to the order success page
    response = redirect(url_for('order_success'))
    response.delete_cookie('cart')
    return response

@app.route('/order_success')
def order_success():
    return render_template('customer/order_success.html')


# --- GLOBAL CONTEXT PROCESSOR FOR CART AND FAVORITES ---
@app.context_processor
def inject_global_data():
    # 1. Get the cart cookie from the browser
    cart_cookie = request.cookies.get('cart')
    cart = load_cart_cookie(cart_cookie)
    total_items_count = sum(cart.values())

    # 2. Get the favorites cookie from the browser
    fav_cookie = request.cookies.get('favorites')
    try:
        fav_list = json.loads(fav_cookie) if fav_cookie else []
        if not isinstance(fav_list, list):
            fav_list = []
        else:
            fav_list = [int(x) for x in fav_list]
    except Exception:
        fav_list = []

    # 3. Return it as global dictionary variables available in all templates
    return dict(
        cart_count=total_items_count,
        fav_count=len(fav_list),
        fav_list=fav_list
    )


# --- NEW: ADD/TOGGLE FAVORITES ROUTE ---
@app.route('/add_to_favorites/<int:item_id>', methods=['POST'])
def add_to_favorites(item_id):
    fav_cookie = request.cookies.get('favorites')
    try:
        fav_list = json.loads(fav_cookie) if fav_cookie else []
        if not isinstance(fav_list, list):
            fav_list = []
        else:
            fav_list = [int(x) for x in fav_list]
    except Exception:
        fav_list = []

    action = 'added'
    if item_id in fav_list:
        fav_list.remove(item_id)
        action = 'removed'
        msg = "Product removed from favorites!"
    else:
        fav_list.append(item_id)
        msg = "Product added to favorites!"

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1'
    if is_ajax:
        response = make_response(json.dumps({
            "status": "success",
            "action": action,
            "fav_count": len(fav_list),
            "message": msg
        }))
        response.headers['Content-Type'] = 'application/json'
    else:
        response = make_response(redirect(request.referrer or url_for('products')))

    response.set_cookie('favorites', json.dumps(fav_list), max_age=60 * 60 * 24 * 30)  # Lasts for 30 days
    return response


# --- NEW: REMOVE FROM FAVORITES ROUTE ---
@app.route('/remove_from_favorites/<int:item_id>', methods=['POST'])
def remove_from_favorites(item_id):
    fav_cookie = request.cookies.get('favorites')
    try:
        fav_list = json.loads(fav_cookie) if fav_cookie else []
        if not isinstance(fav_list, list):
            fav_list = []
        else:
            fav_list = [int(x) for x in fav_list]
    except Exception:
        fav_list = []

    if item_id in fav_list:
        fav_list.remove(item_id)

    msg = "Product removed from favorites!"
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1'
    if is_ajax:
        response = make_response(json.dumps({
            "status": "success",
            "action": "removed",
            "fav_count": len(fav_list),
            "message": msg
        }))
        response.headers['Content-Type'] = 'application/json'
    else:
        response = make_response(redirect(request.referrer or url_for('favorites')))

    response.set_cookie('favorites', json.dumps(fav_list), max_age=60 * 60 * 24 * 30)
    return response


# --- ADDRESSES BACKEND ENDPOINTS ---

@app.route('/add_address', methods=['POST'])
def add_address():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
        
    label = data.get('label', 'Home').strip()
    recipient_name = data.get('recipient_name', '').strip()
    recipient_phone = data.get('recipient_phone', '').strip()
    street = data.get('street', '').strip()
    city = data.get('city', '').strip()
    country = data.get('country', 'Cambodia').strip()
    is_default = data.get('is_default', False)
    
    if not recipient_name or not recipient_phone or not street or not city:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    addresses = current_user.get('addresses', [])
    
    # Generate ID
    addr_id = f"addr_{random.randint(10000, 99999)}"
    
    if is_default:
        # Unset previous default
        for addr in addresses:
            addr['is_default'] = False
            
    new_addr = {
        "id": addr_id,
        "label": label,
        "recipient_name": recipient_name,
        "recipient_phone": recipient_phone,
        "street": street,
        "city": city,
        "country": country,
        "is_default": is_default or len(addresses) == 0
    }
    
    addresses.append(new_addr)
    current_user['addresses'] = addresses
    save_users(users)
    
    return jsonify({"status": "success", "addresses": addresses})

@app.route('/edit_address/<address_id>', methods=['POST'])
def edit_address(address_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
        
    label = data.get('label', 'Home').strip()
    recipient_name = data.get('recipient_name', '').strip()
    recipient_phone = data.get('recipient_phone', '').strip()
    street = data.get('street', '').strip()
    city = data.get('city', '').strip()
    country = data.get('country', 'Cambodia').strip()
    is_default = data.get('is_default', False)
    
    if not recipient_name or not recipient_phone or not street or not city:
        return jsonify({"status": "error", "message": "All fields are required"}), 400
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    addresses = current_user.get('addresses', [])
    addr_to_edit = next((a for a in addresses if a['id'] == address_id), None)
    
    if not addr_to_edit:
        return jsonify({"status": "error", "message": "Address not found"}), 404
        
    if is_default:
        for addr in addresses:
            addr['is_default'] = False
            
    addr_to_edit['label'] = label
    addr_to_edit['recipient_name'] = recipient_name
    addr_to_edit['recipient_phone'] = recipient_phone
    addr_to_edit['street'] = street
    addr_to_edit['city'] = city
    addr_to_edit['country'] = country
    addr_to_edit['is_default'] = is_default or addr_to_edit['is_default']
    
    current_user['addresses'] = addresses
    save_users(users)
    
    return jsonify({"status": "success", "addresses": addresses})

@app.route('/delete_address/<address_id>', methods=['POST'])
def delete_address(address_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    addresses = current_user.get('addresses', [])
    addr_to_remove = next((a for a in addresses if a['id'] == address_id), None)
    
    if not addr_to_remove:
        return jsonify({"status": "error", "message": "Address not found"}), 404
        
    was_default = addr_to_remove.get('is_default', False)
    addresses.remove(addr_to_remove)
    
    if was_default and len(addresses) > 0:
        addresses[0]['is_default'] = True
        
    current_user['addresses'] = addresses
    save_users(users)
    
    return jsonify({"status": "success", "addresses": addresses})

@app.route('/set_default_address/<address_id>', methods=['POST'])
def set_default_address(address_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    addresses = current_user.get('addresses', [])
    addr_to_default = next((a for a in addresses if a['id'] == address_id), None)
    
    if not addr_to_default:
        return jsonify({"status": "error", "message": "Address not found"}), 404
        
    for addr in addresses:
        addr['is_default'] = (addr['id'] == address_id)
        
    current_user['addresses'] = addresses
    save_users(users)
    
    return jsonify({"status": "success", "addresses": addresses})


# --- PAYMENT METHODS BACKEND ENDPOINTS ---

@app.route('/add_payment_method', methods=['POST'])
def add_payment_method():
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
        
    pay_type = data.get('type', 'card').strip()
    is_default = data.get('is_default', False)
    
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    payment_methods = current_user.get('payment_methods', [])
    pay_id = f"pay_{random.randint(10000, 99999)}"
    
    if is_default:
        for pm in payment_methods:
            pm['is_default'] = False
            
    if pay_type == 'card':
        card_brand = data.get('card_brand', 'Visa').strip()
        card_number = data.get('card_number', '').strip()
        cardholder_name = data.get('cardholder_name', '').strip()
        expiry = data.get('expiry', '').strip()
        
        if not card_number or not cardholder_name or not expiry:
            return jsonify({"status": "error", "message": "Card details are required"}), 400
            
        digits_only = "".join(c for c in card_number if c.isdigit())
        if len(digits_only) < 12:
            return jsonify({"status": "error", "message": "Invalid card number"}), 400
            
        masked_number = f"•••• •••• •••• {digits_only[-4:]}"
        
        new_pm = {
            "id": pay_id,
            "type": "card",
            "card_brand": card_brand,
            "card_number": masked_number,
            "cardholder_name": cardholder_name.upper(),
            "expiry": expiry,
            "is_default": is_default or len(payment_methods) == 0
        }
    elif pay_type == 'bakong':
        account_name = data.get('account_name', '').strip()
        if not account_name:
            return jsonify({"status": "error", "message": "Bakong account ID is required"}), 400
            
        if not account_name.endswith('@bakong'):
            account_name += '@bakong'
            
        new_pm = {
            "id": pay_id,
            "type": "bakong",
            "account_name": account_name.lower(),
            "wallet_label": "Bakong KHQR Wallet",
            "is_default": is_default or len(payment_methods) == 0
        }
    else:
        return jsonify({"status": "error", "message": "Unsupported payment type"}), 400
        
    payment_methods.append(new_pm)
    current_user['payment_methods'] = payment_methods
    save_users(users)
    
    return jsonify({"status": "success", "payment_methods": payment_methods})

@app.route('/delete_payment_method/<method_id>', methods=['POST'])
def delete_payment_method(method_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    payment_methods = current_user.get('payment_methods', [])
    pm_to_remove = next((pm for pm in payment_methods if pm['id'] == method_id), None)
    
    if not pm_to_remove:
        return jsonify({"status": "error", "message": "Payment method not found"}), 404
        
    was_default = pm_to_remove.get('is_default', False)
    payment_methods.remove(pm_to_remove)
    
    if was_default and len(payment_methods) > 0:
        payment_methods[0]['is_default'] = True
        
    current_user['payment_methods'] = payment_methods
    save_users(users)
    
    return jsonify({"status": "success", "payment_methods": payment_methods})

@app.route('/set_default_payment_method/<method_id>', methods=['POST'])
def set_default_payment_method(method_id):
    if 'user' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    email = session['user']['email']
    users = load_users()
    current_user = next((u for u in users if u['email'].lower() == email.lower()), None)
    
    if not current_user:
        return jsonify({"status": "error", "message": "User not found"}), 404
        
    payment_methods = current_user.get('payment_methods', [])
    pm_to_default = next((pm for pm in payment_methods if pm['id'] == method_id), None)
    
    if not pm_to_default:
        return jsonify({"status": "error", "message": "Payment method not found"}), 404
        
    for pm in payment_methods:
        pm['is_default'] = (pm['id'] == method_id)
        
    current_user['payment_methods'] = payment_methods
    save_users(users)
    
    return jsonify({"status": "success", "payment_methods": payment_methods})

if __name__ == '__main__':
    # Start the server with debugging enabled
    app.run(debug=False, port=5000)