import os
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import logging
import string
import qrcode
import io
import base64
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import mysql.connector
from database import create_connection
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)
app.secret_key = 'e5b9d6a7fa12dcf7e9b745e3784f0a6d10c5b9d6e3c9a123'

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
# Museum information
MUSEUM_INFO = {
    'name': 'City Art Museum',
    'address': 'Sector-12, Moshi, Pune',
    'hours': '9:00 AM - 5:00 PM, Tuesday through Sunday (Closed on Mondays)',
    'phone': '7083850807'
}

# Ticket prices
TICKET_PRICES = {
    "Child (under 12)": 50,
    "Adult (12-60)": 100,
    "Senior Citizen (60+)": 70
}

sessions = {}


def get_or_create_session(session_id):
    if session_id not in sessions:
        sessions[session_id] = {'state': 'greeting'}
    return sessions[session_id]


def generate_booking_id():
    return random.randint(100000, 999999)


def generate_ticket_id():
    return random.randint(1000000, 9999999)


def get_ticket_type(age):
    if age < 12:
        return "Child (under 12)"
    elif 12 <= age < 60:
        return "Adult (12-60)"
    else:
        return "Senior Citizen (60+)"


def generate_upi_qr(amount):
    upi_id = "your-upi-id@upi"  # Replace with your actual UPI ID
    upi_url = f"upi://pay?pa={upi_id}&pn=Museum&am={amount}&cu=INR"
    
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(upi_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    
    return img_str


def send_confirmation_email(to_email, booking_id, visit_date, visitors, total_price):
    try:
        from_email = os.getenv('EMAIL_ADDRESS')
        password = os.getenv('EMAIL_PASSWORD')
        museum_name = "City Art Museum"
        museum_address = "Sector-12, Moshi, Pune"
        museum_phone = "7083850807"

        logger.debug(f"Attempting to send email to {to_email}")
        logger.debug(f"From email: {from_email}")

        if not from_email or not password:
            logger.error("Email credentials are not set. Skipping email send.")
            return

        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"{museum_name} - Booking Confirmation"

        # Prepare visitors list
        visitors_list = ""
        if isinstance(visitors, list):
            visitors_list = "".join([
                f"<li>{v.get('name', 'Unknown')} - {v.get('ticket_type', 'Unknown').split('(')[0].strip()}</li>"
                for v in visitors
            ])
        else:
            logger.error(f"Unexpected visitors format: {type(visitors)}")
            visitors_list = "<li>Visitor information unavailable</li>"

        # Replace placeholders in the template
        html_content = EMAIL_TEMPLATE.format(
            name=visitors[0]['name'] if isinstance(visitors, list) and len(visitors) > 0 else "Visitor",
            museum_name=museum_name,
            booking_id=booking_id,
            visit_date=visit_date,
            visitors_list=visitors_list,
            total_price=total_price,
            museum_address=museum_address,
            museum_phone=museum_phone
        )

        msg.attach(MIMEText(html_content, 'html'))

        # Attach logo
        try:
            with open('static/museum.png', 'rb') as f:
                img_data = f.read()
                img = MIMEImage(img_data)
                img.add_header('Content-ID', '<museum_logo>')
                msg.attach(img)
        except FileNotFoundError:
            logger.error("museum_logo.png not found. Sending email without logo.")

        logger.debug("Connecting to SMTP server...")
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            logger.debug("Logging in to email account...")
            server.login(from_email, password)
            logger.debug("Sending email...")
            server.send_message(msg)

        logger.info(f"Confirmation email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}", exc_info=True)


def save_to_database(booking_id, transaction_id, names, ages, ticket_types, quantity, total_price, visit_date, email):
    connection = None
    try:
        connection = create_connection()
        cursor = connection.cursor()

        # Log database name
        cursor.execute("SELECT DATABASE()")
        db_name = cursor.fetchone()[0]
        logger.info(f"Connected to database: {db_name}")

        # Save booking information in the bookings table
        booking_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        visit_date_str = visit_date.strftime('%Y-%m-%d %H:%M:%S')

        booking_query = """
        INSERT INTO bookings 
        (booking_id, visit_date, booking_date, total_quantity, total_price, transaction_id, email) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        booking_values = (booking_id, visit_date_str, booking_date, quantity, total_price, transaction_id, email)
        cursor.execute(booking_query, booking_values)
        logger.info(f"Inserted booking: {booking_id}")

        # Save each ticket in the tickets table
        ticket_query = """
        INSERT INTO tickets 
        (ticket_id, booking_id, name, age, ticket_type, price) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        for i in range(quantity):
            ticket_id = generate_ticket_id()
            ticket_values = (
                ticket_id,
                booking_id,
                names[i],
                ages[i],
                ticket_types[i],
                TICKET_PRICES[ticket_types[i]]
            )
            cursor.execute(ticket_query, ticket_values)
            logger.info(f"Inserted ticket: {ticket_id}")

        # Commit the transaction
        connection.commit()
        logger.info("Transaction committed successfully")

        # Verify data was saved
        cursor.execute("SELECT * FROM bookings WHERE booking_id = %s", (booking_id,))
        booking_result = cursor.fetchone()
        logger.info(f"Verified booking: {booking_result}")

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE booking_id = %s", (booking_id,))
        ticket_count = cursor.fetchone()[0]
        logger.info(f"Verified tickets: {ticket_count} tickets found")

    except mysql.connector.Error as err:
        logger.error(f"Database error: {err}")
        if connection:
            connection.rollback()
        raise
    finally:
        if connection:
            if connection.is_connected():
                cursor.close()
                connection.close()
                logger.info("Database connection closed")

    logger.info("Data saved successfully!")


EMAIL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Booking Confirmation</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ width: 100%; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .logo {{ max-width: 150px; }}
        h1 {{ color: #0056b3; }}
        .booking-details {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .footer {{ margin-top: 20px; text-align: center; font-size: 0.9em; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <img src="cid:museum_logo" alt="Museum Logo" class="logo">
            <h1>Booking Confirmation</h1>
        </div>
        <p>Dear {name},</p>
        <p>Thank you for booking with {museum_name}. Your reservation has been confirmed.</p>
        <div class="booking-details">
            <p><strong>Booking ID:</strong> {booking_id}</p>
            <p><strong>Visit Date:</strong> {visit_date}</p>
            <p><strong>Visitors:</strong></p>
            <ul>
                {visitors_list}
            </ul>
            <p><strong>Total Price:</strong> ₹{total_price}</p>
        </div>
        <p>We look forward to welcoming you to our museum. If you have any questions, please don't hesitate to contact us.</p>
        <p>Best regards,<br>The {museum_name} Team</p>
        <div class="footer">
            <p>{museum_name} | {museum_address} | {museum_phone}</p>
        </div>
    </div>
</body>
</html>
"""

def chatbot_response(user_input, session):
    state = session.get('state', 'greeting')
    response = {'type': 'text', 'content': {'message': 'Sorry, I encountered an error.'}}

    try:
        if state == 'greeting':
            response = {
                'type': 'options',
                'content': {
                    'title': f"Welcome to {MUSEUM_INFO['name']}!",
                    'message': "How can I assist you today?",
                    'options': ["Book tickets", "Get museum information"]
                }
            }
            session['state'] = 'main_menu'
        elif state == 'main_menu':
            if 'book' in user_input.lower() or 'ticket' in user_input.lower():
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Great! Let's book your tickets. How many tickets do you need?"
                    }
                }
                session['state'] = 'get_ticket_quantity'
            elif 'information' in user_input.lower() or 'about' in user_input.lower():
                response = {
                    'type': 'info',
                    'content': {
                        'title': "Museum Information",
                        'message': "Here's some information about our museum:",
                        'details': [
                            f"Name: {MUSEUM_INFO['name']}",
                            f"Address: {MUSEUM_INFO['address']}",
                            f"Hours: {MUSEUM_INFO['hours']}",
                            f"Phone: {MUSEUM_INFO['phone']}"
                        ],
                        'question': "Would you like to book tickets now?",
                        'options': ["Yes", "No"]
                    }
                }
            else:
                response = {
                    'type': 'options',
                    'content': {
                        'message': "I'm sorry, I didn't understand. Would you like to book tickets or get information about our museum?",
                        'options': ["Book tickets", "Get museum information"]
                    }
                }
        elif state == 'get_ticket_quantity':
            try:
                quantity = int(user_input)
                if 1 <= quantity <= 10:
                    session['quantity'] = quantity
                    session['visitors'] = []
                    response = {
                        'type': 'text',
                        'content': {
                            'message': f"Great! Now, please provide the name and age for visitor 1 in the format 'Name: Age'."
                        }
                    }
                    session['state'] = 'get_visitor_details'
                    session['current_visitor'] = 1
                else:
                    response = {
                        'type': 'text',
                        'content': {
                            'message': "I'm sorry, we can only process bookings for 1-10 people at a time. Please enter a number between 1 and 10."
                        }
                    }
            except ValueError:
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Please enter a valid number for the quantity of tickets."
                    }
                }
        elif state == 'get_visitor_details':
            if ':' in user_input:
                name, age = user_input.split(':')
                name = name.strip()
                try:
                    age = int(age.strip())
                    ticket_type = get_ticket_type(age)
                    session['visitors'].append({'name': name, 'age': age, 'ticket_type': ticket_type})

                    if len(session['visitors']) < session['quantity']:
                        session['current_visitor'] += 1
                        response = {
                            'type': 'text',
                            'content': {
                                'message': f"Thank you. Now, please provide the name and age for visitor {session['current_visitor']} in the format 'Name: Age'."
                            }
                        }
                    else:
                        total_price = sum(TICKET_PRICES[visitor['ticket_type']] for visitor in session['visitors'])
                        session['total_price'] = total_price
                        response = {
                            'type': 'text',
                            'content': {
                                'message': f"Thank you for providing all visitor details. The total price for your tickets is ₹{total_price}. Please provide your email address for the booking confirmation."
                            }
                        }
                        session['state'] = 'get_email'
                except ValueError:
                    response = {
                        'type': 'text',
                        'content': {
                            'message': "Please enter a valid age as a number."
                        }
                    }
            else:
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Please provide the visitor's name and age in the format 'Name: Age'."
                    }
                }
        elif state == 'get_email':
            if '@' in user_input and '.' in user_input:
                session['email'] = user_input
                response = {
                    'type': 'text',
                    'content': {
                        'message': f"Thank you. Please enter the date of your visit (YYYY-MM-DD):"
                    }
                }
                session['state'] = 'get_visit_date'
            else:
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Please provide a valid email address."
                    }
                }
        elif state == 'get_visit_date':
            try:
                visit_date = datetime.strptime(user_input, '%Y-%m-%d')
                session['visit_date'] = visit_date
                response = {
                    'type': 'options',
                    'content': {
                        'message': f"Thank you. Your visit is scheduled for {visit_date.strftime('%B %d, %Y')}. Would you like to proceed with the payment?",
                        'options': ["Yes", "No"]
                    }
                }
                session['state'] = 'confirm_payment'
            except ValueError:
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Please enter a valid date in the format YYYY-MM-DD."
                    }
                }
        elif state == 'confirm_payment':
            if 'yes' in user_input.lower():
                total_price = session['total_price']
                booking_id = generate_booking_id()
                session['booking_id'] = booking_id
                
                qr_code = generate_upi_qr(total_price)
                
                response = {
                    'type': 'payment',
                    'content': {
                        'title': "Payment",
                        'message': f"Great! Please scan the QR code to make the payment of ₹{total_price}. Your booking ID is {booking_id}.",
                        'qr_code': qr_code,
                        'input_type': 'text',
                        'input_message': "After completing the payment, please enter the UPI transaction ID:"
                    }
                }
                session['state'] = 'payment_confirmation'
            else:
                response = {
                    'type': 'options',
                    'content': {
                        'message': "No problem. Would you like to start over with a new booking or get more information about our museum?",
                        'options': ["Start new booking", "Get museum information"]
                    }
                }
                session['state'] = 'main_menu'
        elif state == 'payment_confirmation':
            if user_input.strip():  # Assuming any non-empty input is a valid transaction ID
                booking_id = session.get('booking_id', 'Unknown')
                email = session.get('email', '')
                total_price = session.get('total_price', 0)
                visitors = session.get('visitors', [])
                visit_date = session.get('visit_date', 'Unknown')
                transaction_id = user_input.strip()

                logger.debug(f"Booking details: ID={booking_id}, Email={email}, Price={total_price}, Visitors={visitors}, Date={visit_date}")

                # Save booking to database
                try:
                    save_to_database(
                        booking_id,
                        transaction_id,
                        [v['name'] for v in visitors],
                        [v['age'] for v in visitors],
                        [v['ticket_type'] for v in visitors],
                        len(visitors),
                        total_price,
                        visit_date,
                        email
                    )
                    logger.info(f"Booking {booking_id} saved to database successfully")
                except Exception as e:
                    logger.error(f"Failed to save booking to database: {str(e)}")
                    return jsonify({
                        'type': 'text',
                        'content': {
                            'message': "An error occurred while processing your booking. Please try again or contact support."
                        }
                    }), 500

                # Send confirmation email
                send_confirmation_email(email, booking_id, visit_date, visitors, total_price)

                response = {
                    'type': 'confirmation',
                    'content': {
                        'title': "Booking Confirmed",
                        'message': f"Thank you for your payment! Your booking is confirmed. Your booking ID is {booking_id}. A confirmation email has been sent to {email}."
                    }
                }
                session.clear()  # Clear the session after successful booking
                session['state'] = 'main_menu'  # Reset to main menu for new interactions
            else:
                response = {
                    'type': 'text',
                    'content': {
                        'message': "Please enter a valid UPI transaction ID to confirm your payment."
                    }
                }
    except Exception as e:
        logger.error(f"Error in chatbot_response: {str(e)}", exc_info=True)
        response = {
            'type': 'text',
            'content': {
                'message': 'Sorry, I encountered an error.'
            }
        }

    logger.debug(f"Chatbot response: {response}")
    return response


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_input = data.get('message', '')
        session_id = data.get('session_id', '')

        app.logger.info(f"Received message: {user_input} for session: {session_id}")

        session = get_or_create_session(session_id)
        response = chatbot_response(user_input, session)

        app.logger.info(f"Sending response: {response}")

        return jsonify(response)
    except Exception as e:
        app.logger.error(f"Error in chat route: {str(e)}")
        return jsonify({"error": "An internal error occurred"}), 500


@app.route('/test_db')
def test_db():
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        connection.close()
        return f"Database connection successful. Result: {result}"
    except Exception as e:
        return f"Database connection failed: {str(e)}"

@app.route('/test_env')
def test_env():
    env_vars = ['DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME', 'EMAIL_ADDRESS', 'EMAIL_PASSWORD']
    results = {}
    for var in env_vars:
        value = os.getenv(var)
        results[var] = 'Set' if value else 'Not set'
    return jsonify(results)

@app.route('/test_static')
def test_static():
    return send_from_directory('static', 'museum.png')

@app.route('/health')
def health_check():
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
