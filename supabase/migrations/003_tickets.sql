CREATE TABLE tickets (
    ticket_id VARCHAR(50) PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    created_at TIMESTAMP,
    status VARCHAR(50),
    subject TEXT,
    description TEXT,
    channel VARCHAR(50),
    assigned_to VARCHAR(255),
    last_customer_message_at TIMESTAMP,
    historical_resolution TEXT,

    CONSTRAINT fk_tickets_account
        FOREIGN KEY (account_id)
        REFERENCES accounts(account_id)
);
