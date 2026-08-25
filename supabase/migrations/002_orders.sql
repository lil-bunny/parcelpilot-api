CREATE TABLE orders (
    order_id VARCHAR(50) PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    carrier VARCHAR(100),
    status VARCHAR(50),
    booked_at TIMESTAMP,
    pickup_window_start TIMESTAMP,
    pickup_window_end TIMESTAMP,
    pickup_actual_at TIMESTAMP,
    shipment_fee_inr NUMERIC(12, 2),
    carrier_fault BOOLEAN,
    customer_fault BOOLEAN,
    cancellation_requested_at TIMESTAMP,
    notes TEXT,

    CONSTRAINT fk_orders_account
        FOREIGN KEY (account_id)
        REFERENCES accounts(account_id)
);
