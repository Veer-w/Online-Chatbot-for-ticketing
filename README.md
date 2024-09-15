# Museum Ticket Booking Chatbot

A Flask-based chatbot system for streamlined museum ticket booking.

## Features

- Conversational interface for ticket booking
- Dynamic pricing based on visitor age
- UPI payment integration with QR code generation
- Email confirmation system
- MySQL database for data storage
- Session management for concurrent users

## Prerequisites

- Python 3.9+
- MySQL database

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Veer-w/Online-Chatbot-for-ticketing.git
   cd museum-chatbot
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Fill in your database and email credentials in `.env`

4. Initialize the database:
   - Run the SQL scripts in `database_setup.sql` to create necessary tables

## Usage

1. Start the Flask server:
   ```
   python main.py
   ```

2. Open a web browser and navigate to `http://localhost:5000`

3. Click "Start Chat" to begin the booking process

## Deployment

This project is configured for deployment on Render. See `render.yaml` for configuration details.

## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.

## License

[MIT](https://choosealicense.com/licenses/mit/)