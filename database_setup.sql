create database museum_tickets;
USE museum_tickets;

CREATE TABLE bookings (
    booking_id INT PRIMARY KEY,
    visit_date DATETIME,
    booking_date DATETIME,
    total_quantity INT,
    total_price DECIMAL(10, 2),
    transaction_id BIGINT,
    email VARCHAR(255)
);


CREATE TABLE tickets (
    ticket_id INT PRIMARY KEY,
    booking_id INT(255),
    name VARCHAR(255),
    age INT,
    ticket_type VARCHAR(50),
    price DECIMAL(10, 2),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

select * from tickets;
select * from bookings;