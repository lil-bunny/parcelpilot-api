CREATE TABLE accounts (
    account_id VARCHAR(50) PRIMARY KEY,
    account_name VARCHAR(255) NOT NULL,
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,
    csm VARCHAR(255),
    contract_file VARCHAR(255),
    premium_support BOOLEAN,
    notes TEXT
);
