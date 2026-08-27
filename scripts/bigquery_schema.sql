-- SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
-- SPDX-License-Identifier: Apache-2.0

-- =====================================================================
-- BigQuery Schema DDL for Synthetic Banking System
-- Project: looker-demo-392616
-- Dataset: synthetic_banking
-- =====================================================================

CREATE SCHEMA IF NOT EXISTS `looker-demo-392616.synthetic_banking`
OPTIONS (
  location = 'US',
  description = 'Synthetic Banking transactional system with fraud analytics markers'
);

-- ---------------------------------------------------------------------
-- 1. Dim Customers
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `looker-demo-392616.synthetic_banking.customers`
(
  customer_id STRING NOT NULL OPTIONS(description="Unique primary identifier for the banking customer"),
  first_name STRING OPTIONS(description="Customer first name"),
  last_name STRING OPTIONS(description="Customer last name"),
  email STRING OPTIONS(description="Customer primary email address"),
  phone_number STRING OPTIONS(description="Customer contact telephone"),
  street_address STRING OPTIONS(description="Customer residential street address"),
  city STRING OPTIONS(description="Customer residential city"),
  state STRING OPTIONS(description="Customer residential state"),
  postal_code STRING OPTIONS(description="Customer residential postal code"),
  country STRING OPTIONS(description="Customer country of residence (ISO 2-letter)"),
  customer_segment STRING OPTIONS(description="Tiering segment: RETAIL_STANDARD, RETAIL_PREMIER, SMALL_BUSINESS, WEALTH_MANAGEMENT"),
  annual_income FLOAT64 OPTIONS(description="Estimated or declared annual gross income in USD"),
  credit_score INT64 OPTIONS(description="Customer FICO credit score (300-850)"),
  kyc_status STRING OPTIONS(description="KYC compliance status: VERIFIED, PENDING_REVIEW, ENHANCED_DILIGENCE"),
  risk_rating STRING OPTIONS(description="Customer risk rating: LOW, MEDIUM, HIGH"),
  customer_since TIMESTAMP OPTIONS(description="Timestamp when customer profile was created")
)
CLUSTER BY customer_segment, risk_rating;

-- ---------------------------------------------------------------------
-- 2. Dim Accounts
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `looker-demo-392616.synthetic_banking.accounts`
(
  account_id STRING NOT NULL OPTIONS(description="Unique primary identifier for the financial account"),
  customer_id STRING NOT NULL OPTIONS(description="Foreign key referencing customers.customer_id"),
  account_type STRING OPTIONS(description="Account product: CHECKING, SAVINGS, MONEY_MARKET, CREDIT_CARD, BUSINESS_CHECKING"),
  account_status STRING OPTIONS(description="Status: ACTIVE, DORMANT, FROZEN, CLOSED"),
  currency STRING OPTIONS(description="3-letter currency code (e.g. USD)"),
  current_balance FLOAT64 OPTIONS(description="Ledger posted balance"),
  available_balance FLOAT64 OPTIONS(description="Available balance excluding pending holds"),
  credit_limit FLOAT64 OPTIONS(description="Assigned credit limit or overdraft limit"),
  interest_rate_pct FLOAT64 OPTIONS(description="Annual percentage rate / yield (APY/APR)"),
  opened_at TIMESTAMP OPTIONS(description="Timestamp when account was opened")
)
CLUSTER BY customer_id, account_type;

-- ---------------------------------------------------------------------
-- 3. Dim Cards
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `looker-demo-392616.synthetic_banking.cards`
(
  card_id STRING NOT NULL OPTIONS(description="Unique primary identifier for the payment card"),
  account_id STRING NOT NULL OPTIONS(description="Foreign key referencing accounts.account_id"),
  customer_id STRING NOT NULL OPTIONS(description="Foreign key referencing customers.customer_id"),
  card_number_masked STRING OPTIONS(description="Masked Primary Account Number (PAN)"),
  card_network STRING OPTIONS(description="Card network brand: VISA, MASTERCARD, AMEX, DISCOVER"),
  card_type STRING OPTIONS(description="Card type: DEBIT, CREDIT, VIRTUAL"),
  card_status STRING OPTIONS(description="Status: ACTIVE, BLOCKED, EXPIRED, REPORTED_STOLEN"),
  expiration_date STRING OPTIONS(description="Card expiration date formatted MM/YY"),
  is_contactless BOOLEAN OPTIONS(description="Whether card supports NFC / contactless payments"),
  daily_limit FLOAT64 OPTIONS(description="Maximum authorized daily spending limit"),
  issued_at TIMESTAMP OPTIONS(description="Timestamp when card was issued")
)
CLUSTER BY customer_id, account_id, card_network;

-- ---------------------------------------------------------------------
-- 4. Dim Merchants
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `looker-demo-392616.synthetic_banking.merchants`
(
  merchant_id STRING NOT NULL OPTIONS(description="Unique primary identifier for merchant"),
  merchant_name STRING OPTIONS(description="Commercial brand or legal merchant name"),
  merchant_category_code STRING OPTIONS(description="4-digit ISO 18245 Merchant Category Code (MCC)"),
  merchant_category_name STRING OPTIONS(description="Industry / category name for the MCC"),
  merchant_city STRING OPTIONS(description="Merchant headquarters or store city"),
  merchant_state STRING OPTIONS(description="Merchant state"),
  merchant_country STRING OPTIONS(description="Merchant country"),
  is_online_only BOOLEAN OPTIONS(description="Whether merchant operates exclusively digitally"),
  risk_level STRING OPTIONS(description="Inherent industry risk level: LOW, MEDIUM, HIGH")
)
CLUSTER BY merchant_category_code, risk_level;

-- ---------------------------------------------------------------------
-- 5. Fact Transactions
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE `looker-demo-392616.synthetic_banking.transactions`
(
  transaction_id STRING NOT NULL OPTIONS(description="Unique primary identifier for transaction event"),
  account_id STRING NOT NULL OPTIONS(description="Foreign key referencing accounts.account_id"),
  card_id STRING NOT NULL OPTIONS(description="Foreign key referencing cards.card_id"),
  customer_id STRING NOT NULL OPTIONS(description="Foreign key referencing customers.customer_id"),
  merchant_id STRING NOT NULL OPTIONS(description="Foreign key referencing merchants.merchant_id"),
  timestamp TIMESTAMP NOT NULL OPTIONS(description="Transaction event UTC timestamp"),
  transaction_type STRING OPTIONS(description="Event classification: PURCHASE, ATM_WITHDRAWAL, etc."),
  payment_channel STRING OPTIONS(description="Channel: POS_CHIP, POS_CONTACTLESS, ECOMMERCE_ONLINE, MOBILE_APP, ATM"),
  amount FLOAT64 NOT NULL OPTIONS(description="Transaction amount in local currency"),
  currency STRING OPTIONS(description="3-letter currency code (USD)"),
  status STRING OPTIONS(description="Processing status: SETTLED, PENDING, DECLINED"),
  decline_reason STRING OPTIONS(description="Reason for decline: NONE, INSUFFICIENT_FUNDS, SUSPECTED_FRAUD, DAILY_LIMIT_EXCEEDED"),
  auth_code STRING OPTIONS(description="6-character card authorization approval code"),
  statement_descriptor STRING OPTIONS(description="Uppercase ledger description on bank statements"),
  location_city STRING OPTIONS(description="Transaction terminal or IP location city"),
  location_state STRING OPTIONS(description="Transaction terminal or IP location state"),
  location_country STRING OPTIONS(description="Transaction country"),
  distance_from_home_km FLOAT64 OPTIONS(description="Geographic distance between customer home and transaction terminal"),
  is_international BOOLEAN OPTIONS(description="Whether transaction occurred outside customer home country"),
  is_card_present BOOLEAN OPTIONS(description="Whether physical payment card was present at terminal"),
  ip_address STRING OPTIONS(description="Client IP address for online/mobile channels"),
  device_type STRING OPTIONS(description="Device category: IOS_APP, ANDROID_APP, WEB_BROWSER, POS_TERMINAL, ATM_KIOSK"),
  device_id STRING OPTIONS(description="Fingerprinted client hardware identifier"),
  risk_score FLOAT64 OPTIONS(description="Model evaluated risk anomaly probability (0.00 - 1.00)"),
  is_fraud BOOLEAN NOT NULL OPTIONS(description="Ground truth binary fraud label"),
  fraud_type STRING OPTIONS(description="Fraud category: NONE, CARD_NOT_PRESENT, ACCOUNT_TAKEOVER, CARD_CLONING_SKIMMING, VELOCITY_ATTACK, HIGH_RISK_MERCHANT_EXPLOIT")
)
PARTITION BY DATE(timestamp)
CLUSTER BY customer_id, merchant_id, is_fraud;
