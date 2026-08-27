# SPDX-FileCopyrightText: Copyright (c) 2026 lkr.dev. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import argparse
import random
import string
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

import data_designer.config as dd
from data_designer.interface import DataDesigner


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate synthetic banking relational dataset")
    parser.add_argument("--num-customers", type=int, default=500, help="Number of customer rows to generate")
    parser.add_argument("--num-merchants", type=int, default=50, help="Number of merchant rows to generate")
    parser.add_argument("--num-transactions", type=int, default=15000, help="Number of transaction rows to generate")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="artifacts/banking_system",
        help="Directory where Parquet files will be stored",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return parser.parse_args()


def generate_customers_dataset(num_customers: int, seed: int = 42) -> pd.DataFrame:
    """Generate customer profiles using DataDesigner builder with Faker person sampler."""
    builder = dd.DataDesignerConfigBuilder()

    builder.add_column(
        dd.SamplerColumnConfig(
            name="person",
            drop=True,
            sampler_type=dd.SamplerType.PERSON_FROM_FAKER,
            params=dd.PersonFromFakerSamplerParams(locale="en_US"),
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="first_name",
            expr="{{ person.first_name }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="last_name",
            expr="{{ person.last_name }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="email",
            expr="{{ person.first_name | lower }}.{{ person.last_name | lower }}@example.com",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="phone_number",
            expr="{{ person.phone_number }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="street_address",
            expr="{{ person.street_number }} {{ person.street_name }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="city",
            expr="{{ person.city }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="state",
            expr="{{ person.state }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="postal_code",
            expr="{{ person.postcode }}",
        )
    )
    builder.add_column(
        dd.ExpressionColumnConfig(
            name="country",
            expr="US",
        )
    )
    builder.add_column(
        dd.SamplerColumnConfig(
            name="customer_segment",
            sampler_type=dd.SamplerType.CATEGORY,
            params=dd.CategorySamplerParams(
                values=["RETAIL_STANDARD", "RETAIL_PREMIER", "SMALL_BUSINESS", "WEALTH_MANAGEMENT"],
                weights=[0.60, 0.25, 0.10, 0.05],
            ),
        )
    )
    builder.add_column(
        dd.SamplerColumnConfig(
            name="credit_score",
            sampler_type=dd.SamplerType.UNIFORM,
            params=dd.UniformSamplerParams(low=580, high=850, decimal_places=0),
            convert_to="int",
        )
    )
    builder.add_column(
        dd.SamplerColumnConfig(
            name="kyc_status",
            sampler_type=dd.SamplerType.CATEGORY,
            params=dd.CategorySamplerParams(
                values=["VERIFIED", "PENDING_REVIEW", "ENHANCED_DILIGENCE"],
                weights=[0.93, 0.05, 0.02],
            ),
        )
    )
    builder.add_column(
        dd.SamplerColumnConfig(
            name="customer_since",
            sampler_type=dd.SamplerType.DATETIME,
            params=dd.DatetimeSamplerParams(
                start="2018-01-01 00:00:00",
                end="2025-12-31 23:59:59",
                unit="s",
            ),
        )
    )

    designer = DataDesigner()
    res = designer.create(builder, num_records=num_customers)
    df = res.load_dataset()

    # Assign distinct, deterministic, non-colliding customer_ids
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    cust_ids = [f"CUST-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}" for _ in range(len(df))]
    df["customer_id"] = cust_ids

    # Calculate realistic income and risk rating based on segment and credit score
    incomes = []
    risk_ratings = []

    for _, row in df.iterrows():
        segment = row["customer_segment"]
        credit = row["credit_score"]

        if segment == "RETAIL_STANDARD":
            income = round(float(np_rng.uniform(35000, 95000)), 2)
        elif segment == "RETAIL_PREMIER":
            income = round(float(np_rng.uniform(95000, 220000)), 2)
        elif segment == "SMALL_BUSINESS":
            income = round(float(np_rng.uniform(120000, 450000)), 2)
        else:  # WEALTH_MANAGEMENT
            income = round(float(np_rng.uniform(300000, 1500000)), 2)
        incomes.append(income)

        if credit < 620 or row["kyc_status"] == "ENHANCED_DILIGENCE":
            risk = "HIGH"
        elif credit < 700 or row["kyc_status"] == "PENDING_REVIEW":
            risk = "MEDIUM"
        else:
            risk = "LOW"
        risk_ratings.append(risk)

    df["annual_income"] = incomes
    df["risk_rating"] = risk_ratings

    cols = [
        "customer_id",
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "street_address",
        "city",
        "state",
        "postal_code",
        "country",
        "customer_segment",
        "annual_income",
        "credit_score",
        "kyc_status",
        "risk_rating",
        "customer_since",
    ]
    df["customer_since"] = pd.to_datetime(df["customer_since"])
    return df[cols]


def generate_accounts_and_cards_dataset(
    customers_df: pd.DataFrame, seed: int = 42
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate accounts and cards ensuring strictly each customer has between 1 and 3 cards."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    account_rows: list[dict] = []
    card_rows: list[dict] = []

    def make_masked_pan(network: str) -> str:
        bin_prefix = {
            "VISA": "4" + "".join(rng.choices(string.digits, k=3)),
            "MASTERCARD": "5" + "".join(rng.choices(string.digits, k=3)),
            "AMEX": "37" + "".join(rng.choices(string.digits, k=2)),
            "DISCOVER": "6011",
        }[network]
        last4 = "".join(rng.choices(string.digits, k=4))
        return f"{bin_prefix}********{last4}"

    for _, cust in customers_df.iterrows():
        cust_id = cust["customer_id"]
        segment = cust["customer_segment"]
        opened_base = cust["customer_since"]

        balance_scale = {
            "RETAIL_STANDARD": 5000.0,
            "RETAIL_PREMIER": 25000.0,
            "SMALL_BUSINESS": 65000.0,
            "WEALTH_MANAGEMENT": 250000.0,
        }[segment]

        daily_limit = {
            "RETAIL_STANDARD": 1500.0,
            "RETAIL_PREMIER": 5000.0,
            "SMALL_BUSINESS": 15000.0,
            "WEALTH_MANAGEMENT": 25000.0,
        }[segment]

        # 1. Primary Checking Account (Guaranteed)
        chk_id = f"ACCT-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
        chk_balance = round(float(np_rng.exponential(scale=balance_scale * 0.6) + 500), 2)
        account_rows.append(
            {
                "account_id": chk_id,
                "customer_id": cust_id,
                "account_type": "BUSINESS_CHECKING" if segment == "SMALL_BUSINESS" else "CHECKING",
                "account_status": "ACTIVE",
                "currency": "USD",
                "current_balance": chk_balance,
                "available_balance": round(chk_balance * rng.uniform(0.92, 0.99), 2),
                "credit_limit": 0.0,
                "interest_rate_pct": 0.05,
                "opened_at": opened_base,
            }
        )

        # Card 1: Primary Debit Card on Checking (Guaranteed for every customer)
        card1_id = f"CARD-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
        net1 = rng.choices(["VISA", "MASTERCARD"], weights=[0.60, 0.40], k=1)[0]
        exp_date1 = f"{rng.randint(1, 12):02d}/{rng.randint(27, 31)}"
        card_rows.append(
            {
                "card_id": card1_id,
                "account_id": chk_id,
                "customer_id": cust_id,
                "card_number_masked": make_masked_pan(net1),
                "card_network": net1,
                "card_type": "DEBIT",
                "card_status": "ACTIVE",
                "expiration_date": exp_date1,
                "is_contactless": True,
                "daily_limit": daily_limit,
                "issued_at": opened_base + timedelta(days=rng.randint(1, 7)),
            }
        )

        # 2. Savings or Money Market Account (for 75% of customers, deposit only, no card)
        if rng.random() < 0.75:
            sav_id = f"ACCT-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
            is_mm = segment in ["WEALTH_MANAGEMENT", "RETAIL_PREMIER"] and rng.random() < 0.6
            sav_type = "MONEY_MARKET" if is_mm else "SAVINGS"
            sav_rate = 5.10 if is_mm else 4.25
            sav_balance = round(float(np_rng.exponential(scale=balance_scale * 1.5) + 1000), 2)
            opened_days = rng.randint(0, 180)
            account_rows.append(
                {
                    "account_id": sav_id,
                    "customer_id": cust_id,
                    "account_type": sav_type,
                    "account_status": "ACTIVE",
                    "currency": "USD",
                    "current_balance": sav_balance,
                    "available_balance": sav_balance,
                    "credit_limit": 0.0,
                    "interest_rate_pct": sav_rate,
                    "opened_at": opened_base + timedelta(days=opened_days),
                }
            )

        # Determine total cards for this customer: strictly in {1, 2, 3}
        target_card_count = rng.choices([1, 2, 3], weights=[0.25, 0.50, 0.25], k=1)[0]

        # 3. Credit Card Account (if target_card_count >= 2)
        cc_id = None
        if target_card_count >= 2:
            cc_id = f"ACCT-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
            limit = {
                "RETAIL_STANDARD": round(float(rng.choice([2500, 5000, 7500, 10000])), 2),
                "RETAIL_PREMIER": round(float(rng.choice([12000, 15000, 20000, 25000])), 2),
                "SMALL_BUSINESS": round(float(rng.choice([25000, 35000, 50000])), 2),
                "WEALTH_MANAGEMENT": round(float(rng.choice([50000, 75000, 100000])), 2),
            }[segment]
            utilization = rng.uniform(0.05, 0.45)
            cc_balance = round(limit * utilization, 2)
            opened_days = rng.randint(10, 360)
            account_rows.append(
                {
                    "account_id": cc_id,
                    "customer_id": cust_id,
                    "account_type": "CREDIT_CARD",
                    "account_status": "ACTIVE",
                    "currency": "USD",
                    "current_balance": cc_balance,
                    "available_balance": round(limit - cc_balance, 2),
                    "credit_limit": float(limit),
                    "interest_rate_pct": round(rng.uniform(16.99, 24.99), 2),
                    "opened_at": opened_base + timedelta(days=opened_days),
                }
            )

            # Card 2: Credit Card
            card2_id = f"CARD-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
            net2 = rng.choices(["VISA", "MASTERCARD", "AMEX", "DISCOVER"], weights=[0.40, 0.35, 0.20, 0.05], k=1)[0]
            exp_date2 = f"{rng.randint(1, 12):02d}/{rng.randint(27, 31)}"
            card_rows.append(
                {
                    "card_id": card2_id,
                    "account_id": cc_id,
                    "customer_id": cust_id,
                    "card_number_masked": make_masked_pan(net2),
                    "card_network": net2,
                    "card_type": "CREDIT",
                    "card_status": "ACTIVE",
                    "expiration_date": exp_date2,
                    "is_contactless": True,
                    "daily_limit": daily_limit,
                    "issued_at": opened_base + timedelta(days=opened_days + rng.randint(1, 7)),
                }
            )

        # Card 3: Virtual / Secondary Card (if target_card_count == 3)
        if target_card_count == 3:
            card3_id = f"CARD-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
            net3 = rng.choices(["VISA", "MASTERCARD", "AMEX"], weights=[0.45, 0.40, 0.15], k=1)[0]
            exp_date3 = f"{rng.randint(1, 12):02d}/{rng.randint(27, 31)}"
            card_type3 = "VIRTUAL"
            target_acct_id = chk_id if rng.random() < 0.5 else (cc_id if cc_id else chk_id)
            card_rows.append(
                {
                    "card_id": card3_id,
                    "account_id": target_acct_id,
                    "customer_id": cust_id,
                    "card_number_masked": make_masked_pan(net3),
                    "card_network": net3,
                    "card_type": card_type3,
                    "card_status": "ACTIVE",
                    "expiration_date": exp_date3,
                    "is_contactless": True,
                    "daily_limit": daily_limit * 0.5,
                    "issued_at": opened_base + timedelta(days=rng.randint(30, 400)),
                }
            )

    acct_df = pd.DataFrame(account_rows)
    acct_df["opened_at"] = pd.to_datetime(acct_df["opened_at"])

    cards_df = pd.DataFrame(card_rows)
    cards_df["issued_at"] = pd.to_datetime(cards_df["issued_at"])
    return acct_df, cards_df


def generate_merchants_dataset(num_merchants: int, seed: int = 42) -> pd.DataFrame:
    """Generate realistic merchants dataset with standard Merchant Category Codes (MCC)."""
    rng = random.Random(seed)

    mcc_catalog = [
        ("5411", "Groceries & Supermarkets", "Whole Foods Market #102", "Austin", "Texas", False, "LOW"),
        ("5411", "Groceries & Supermarkets", "Trader Joe's #145", "Monrovia", "California", False, "LOW"),
        ("5411", "Groceries & Supermarkets", "Costco Wholesale #482", "Issaquah", "Washington", False, "LOW"),
        ("5411", "Groceries & Supermarkets", "Kroger Supermarket #712", "Cincinnati", "Ohio", False, "LOW"),
        ("5411", "Groceries & Supermarkets", "Safeway Groceries #921", "Pleasanton", "California", False, "LOW"),
        ("5812", "Dining & Restaurants", "The French Laundry", "Yountville", "California", False, "LOW"),
        ("5812", "Dining & Restaurants", "Olive Garden Italian #410", "Orlando", "Florida", False, "LOW"),
        ("5812", "Dining & Restaurants", "Cheesecake Factory #88", "Calabasas", "California", False, "LOW"),
        ("5814", "Fast Food Restaurants", "Chipotle Mexican Grill #284", "Newport Beach", "California", False, "LOW"),
        ("5814", "Fast Food Restaurants", "Starbucks Coffee #8921", "Seattle", "Washington", False, "LOW"),
        ("5814", "Fast Food Restaurants", "McDonald's Fast Food #104", "Chicago", "Illinois", False, "LOW"),
        ("5814", "Fast Food Restaurants", "Sweetgreen Healthy Salads", "Los Angeles", "California", False, "LOW"),
        ("5541", "Gas & Fuel Stations", "Shell Oil #4910", "Houston", "Texas", False, "LOW"),
        ("5541", "Gas & Fuel Stations", "Chevron Service #3210", "San Ramon", "California", False, "LOW"),
        ("5541", "Gas & Fuel Stations", "ExxonMobil Express #512", "Irving", "Texas", False, "LOW"),
        ("4121", "Taxicabs & Rideshare", "Uber Technologies Inc", "San Francisco", "California", True, "LOW"),
        ("4121", "Taxicabs & Rideshare", "Lyft Rideshare Direct", "San Francisco", "California", True, "LOW"),
        ("4511", "Airlines & Travel", "Delta Air Lines 006", "Atlanta", "Georgia", True, "MEDIUM"),
        ("4511", "Airlines & Travel", "United Airlines 016", "Chicago", "Illinois", True, "MEDIUM"),
        ("4511", "Airlines & Travel", "American Airlines 001", "Fort Worth", "Texas", True, "MEDIUM"),
        ("7011", "Hotels & Lodging", "Marriott International Resort", "Bethesda", "Maryland", False, "MEDIUM"),
        ("7011", "Hotels & Lodging", "Hilton Hotels & Resorts", "Tysons Corner", "Virginia", False, "MEDIUM"),
        ("7011", "Hotels & Lodging", "Airbnb Global Lodging", "San Francisco", "California", True, "MEDIUM"),
        ("5732", "Electronics Stores", "Apple Store #R142", "Cupertino", "California", False, "MEDIUM"),
        ("5732", "Electronics Stores", "Best Buy #882", "Richfield", "Minnesota", False, "MEDIUM"),
        ("5732", "Electronics Stores", "B&H Photo & Electronics", "New York", "New York", True, "MEDIUM"),
        ("5999", "General Retail & Ecommerce", "Amazon Marketplace US", "Seattle", "Washington", True, "LOW"),
        ("5999", "General Retail & Ecommerce", "Target Superstore #1092", "Minneapolis", "Minnesota", False, "LOW"),
        ("5999", "General Retail & Ecommerce", "Walmart Supercenter #2041", "Bentonville", "Arkansas", False, "LOW"),
        ("5999", "General Retail & Ecommerce", "Nordstrom Department Store", "Seattle", "Washington", False, "LOW"),
        ("4814", "Telecommunication Services", "Verizon Wireless Direct", "New York", "New York", True, "LOW"),
        ("4814", "Telecommunication Services", "AT&T Mobility Billing", "Dallas", "Texas", True, "LOW"),
        ("4900", "Utilities & Power", "Pacific Gas & Electric", "San Francisco", "California", True, "LOW"),
        ("4900", "Utilities & Power", "ConEdison Power & Gas", "New York", "New York", True, "LOW"),
        ("6011", "Automated Cash / ATM", "Chase Bank ATM #4019", "New York", "New York", False, "MEDIUM"),
        ("6011", "Automated Cash / ATM", "Bank of America 24Hr ATM", "Charlotte", "North Carolina", False, "MEDIUM"),
        ("6011", "Automated Cash / ATM", "Wells Fargo Express ATM", "San Francisco", "California", False, "MEDIUM"),
        ("7995", "Betting & Casino Gaming", "Bellagio Casino & Sportsbook", "Las Vegas", "Nevada", False, "HIGH"),
        ("7995", "Betting & Casino Gaming", "DraftKings Online Wagering", "Boston", "Massachusetts", True, "HIGH"),
        ("7995", "Betting & Casino Gaming", "FanDuel Sports Betting", "New York", "New York", True, "HIGH"),
        (
            "6051",
            "Cryptocurrency & Quasi-Cash",
            "Coinbase Digital Currency",
            "San Francisco",
            "California",
            True,
            "HIGH",
        ),
        ("6051", "Cryptocurrency & Quasi-Cash", "Kraken Crypto Exchange", "San Francisco", "California", True, "HIGH"),
        ("6051", "Cryptocurrency & Quasi-Cash", "Binance US Trading", "Miami", "Florida", True, "HIGH"),
        ("5944", "Jewelry & Luxury Goods", "Tiffany & Co Flagship", "New York", "New York", False, "MEDIUM"),
        ("5944", "Jewelry & Luxury Goods", "Cartier Luxury Boutique", "Beverly Hills", "California", False, "MEDIUM"),
    ]

    selected = []
    for i in range(num_merchants):
        base = mcc_catalog[i % len(mcc_catalog)]
        m_id = f"MRCH-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
        suffix = f" #{i + 100}" if i >= len(mcc_catalog) else ""
        selected.append(
            {
                "merchant_id": m_id,
                "merchant_name": f"{base[2]}{suffix}",
                "merchant_category_code": base[0],
                "merchant_category_name": base[1],
                "merchant_city": base[3],
                "merchant_state": base[4],
                "merchant_country": "US",
                "is_online_only": base[5],
                "risk_level": base[6],
            }
        )

    return pd.DataFrame(selected)


def generate_transactions_dataset(
    customers_df: pd.DataFrame,
    accounts_df: pd.DataFrame,
    cards_df: pd.DataFrame,
    merchants_df: pd.DataFrame,
    num_transactions: int,
    fraud_rate: float = 0.035,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate transactional fact table with both standard spend patterns and labeled fraud scenarios."""
    rng = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    transactions: list[dict] = []
    base_time = datetime(2026, 6, 1, 8, 0, 0)
    end_time = datetime(2026, 8, 27, 18, 0, 0)
    total_seconds = int((end_time - base_time).total_seconds())

    card_lookup = {row["card_id"]: row for _, row in cards_df.iterrows()}
    card_ids = list(card_lookup.keys())

    cust_lookup = {row["customer_id"]: row for _, row in customers_df.iterrows()}
    merchants_list = merchants_df.to_dict(orient="records")

    high_risk_merchants = [m for m in merchants_list if m["risk_level"] == "HIGH"]
    normal_merchants = [m for m in merchants_list if m["risk_level"] != "HIGH"]

    for i in range(num_transactions):
        txn_id = f"TXN-{uuid.UUID(int=rng.getrandbits(128)).hex[:10].upper()}"
        txn_time = base_time + timedelta(seconds=rng.randint(0, total_seconds))

        is_fraud = rng.random() < fraud_rate

        c_id = rng.choice(card_ids)
        card_obj = card_lookup[c_id]
        a_id = card_obj["account_id"]
        cust_id = card_obj["customer_id"]
        cust_obj = cust_lookup[cust_id]

        auth_code = "".join(rng.choices(string.ascii_uppercase + string.digits, k=6))

        if not is_fraud:
            # 1. NORMAL TRANSACTION
            merchant = rng.choice(normal_merchants if normal_merchants else merchants_list)
            is_online = merchant["is_online_only"] or rng.random() < 0.25

            if is_online:
                channel = rng.choice(["ECOMMERCE_ONLINE", "MOBILE_APP"])
                is_card_present = False
                device_type = rng.choice(["IOS_APP", "ANDROID_APP", "WEB_BROWSER"])
                distance_km = 0.0
                loc_city = cust_obj["city"]
                loc_state = cust_obj["state"]
                loc_country = "US"
            else:
                channel = rng.choice(
                    ["POS_CONTACTLESS", "POS_CHIP", "ATM"]
                    if merchant["merchant_category_code"] == "6011"
                    else ["POS_CONTACTLESS", "POS_CHIP"]
                )
                is_card_present = True
                device_type = "ATM_KIOSK" if channel == "ATM" else "POS_TERMINAL"
                distance_km = round(float(np_rng.exponential(scale=6.5)), 2)
                loc_city = cust_obj["city"]
                loc_state = cust_obj["state"]
                loc_country = "US"

            mcc = merchant["merchant_category_code"]
            if mcc in ["5814", "5812"]:
                amount = round(float(np_rng.uniform(4.50, 85.00)), 2)
            elif mcc == "5411":
                amount = round(float(np_rng.uniform(25.00, 240.00)), 2)
            elif mcc == "5541":
                amount = round(float(np_rng.uniform(20.00, 75.00)), 2)
            elif mcc in ["4511", "7011"]:
                amount = round(float(np_rng.uniform(150.00, 950.00)), 2)
            elif mcc in ["5732", "5944"]:
                amount = round(float(np_rng.uniform(50.00, 650.00)), 2)
            elif mcc == "6011":
                amount = round(float(rng.choice([40, 60, 100, 200, 300])), 2)
            else:
                amount = round(float(np_rng.uniform(12.00, 180.00)), 2)

            status = rng.choices(["SETTLED", "PENDING", "DECLINED"], weights=[0.93, 0.05, 0.02], k=1)[0]
            decline_reason = "INSUFFICIENT_FUNDS" if status == "DECLINED" else "NONE"
            risk_score = round(float(np_rng.beta(1.5, 25.0)), 4)
            fraud_type = "NONE"
            is_international = False

        else:
            # 2. FRAUD TRANSACTION SCENARIOS
            fraud_scenario = rng.choice(
                [
                    "CARD_NOT_PRESENT",
                    "ACCOUNT_TAKEOVER",
                    "CARD_CLONING_SKIMMING",
                    "VELOCITY_ATTACK",
                    "HIGH_RISK_MERCHANT_EXPLOIT",
                ]
            )

            if fraud_scenario == "CARD_NOT_PRESENT":
                merchant = rng.choice(merchants_list)
                channel = "ECOMMERCE_ONLINE"
                is_card_present = False
                device_type = "WEB_BROWSER"
                distance_km = 0.0
                loc_city = rng.choice(["Miami", "Las Vegas", "Atlanta", "Dallas", "Phoenix"])
                loc_state = rng.choice(["Florida", "Nevada", "Georgia", "Texas", "Arizona"])
                loc_country = "US"
                amount = round(float(np_rng.uniform(350.00, 2800.00)), 2)
                status = rng.choices(["SETTLED", "DECLINED"], weights=[0.70, 0.30], k=1)[0]
                decline_reason = "SUSPECTED_FRAUD" if status == "DECLINED" else "NONE"
                risk_score = round(float(np_rng.uniform(0.75, 0.98)), 4)
                fraud_type = "CARD_NOT_PRESENT"
                is_international = False

            elif fraud_scenario == "CARD_CLONING_SKIMMING":
                merchant = rng.choice(merchants_list)
                channel = "POS_CHIP"
                is_card_present = True
                device_type = "POS_TERMINAL"
                distance_km = round(float(np_rng.uniform(650.0, 4200.0)), 2)
                loc_city = rng.choice(["London", "Cancun", "Paris", "Toronto", "Dubai"])
                loc_state = "International"
                loc_country = rng.choice(["UK", "MX", "FR", "CA", "AE"])
                amount = round(float(np_rng.uniform(200.00, 1500.00)), 2)
                status = rng.choices(["SETTLED", "DECLINED"], weights=[0.60, 0.40], k=1)[0]
                decline_reason = "SUSPECTED_FRAUD" if status == "DECLINED" else "NONE"
                risk_score = round(float(np_rng.uniform(0.82, 0.99)), 4)
                fraud_type = "CARD_CLONING_SKIMMING"
                is_international = True

            elif fraud_scenario == "HIGH_RISK_MERCHANT_EXPLOIT":
                merchant = rng.choice(high_risk_merchants if high_risk_merchants else merchants_list)
                channel = "ECOMMERCE_ONLINE"
                is_card_present = False
                device_type = "WEB_BROWSER"
                distance_km = 0.0
                loc_city = cust_obj["city"]
                loc_state = cust_obj["state"]
                loc_country = "US"
                amount = round(float(np_rng.uniform(500.00, 4500.00)), 2)
                status = rng.choices(["SETTLED", "DECLINED"], weights=[0.55, 0.45], k=1)[0]
                decline_reason = "DAILY_LIMIT_EXCEEDED" if status == "DECLINED" else "NONE"
                risk_score = round(float(np_rng.uniform(0.80, 0.97)), 4)
                fraud_type = "HIGH_RISK_MERCHANT_EXPLOIT"
                is_international = False

            else:
                merchant = rng.choice(merchants_list)
                channel = "MOBILE_APP" if fraud_scenario == "ACCOUNT_TAKEOVER" else "ECOMMERCE_ONLINE"
                is_card_present = False
                device_type = "ANDROID_APP" if fraud_scenario == "ACCOUNT_TAKEOVER" else "WEB_BROWSER"
                distance_km = round(float(np_rng.uniform(250.0, 1200.0)), 2)
                loc_city = rng.choice(["New York", "Chicago", "Los Angeles", "Houston"])
                loc_state = rng.choice(["New York", "Illinois", "California", "Texas"])
                loc_country = "US"
                amount = round(float(np_rng.uniform(150.00, 3200.00)), 2)
                status = rng.choices(["SETTLED", "DECLINED"], weights=[0.65, 0.35], k=1)[0]
                decline_reason = "SUSPECTED_FRAUD" if status == "DECLINED" else "NONE"
                risk_score = round(float(np_rng.uniform(0.85, 0.99)), 4)
                fraud_type = fraud_scenario
                is_international = False

        m_name_clean = merchant["merchant_name"].upper().replace("'", "").replace("#", "")[:22]
        descriptor = f"{m_name_clean} {loc_city.upper()} {loc_state.upper()[:2]}"

        ip_addr = f"{rng.randint(11, 215)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}.{rng.randint(1, 254)}"
        dev_id = f"DEV-{uuid.UUID(int=rng.getrandbits(128)).hex[:12].upper()}"

        txn_type = "ATM_WITHDRAWAL" if channel == "ATM" else "PURCHASE"

        transactions.append(
            {
                "transaction_id": txn_id,
                "account_id": a_id,
                "card_id": c_id,
                "customer_id": cust_id,
                "merchant_id": merchant["merchant_id"],
                "timestamp": txn_time,
                "transaction_type": txn_type,
                "payment_channel": channel,
                "amount": amount,
                "currency": "USD",
                "status": status,
                "decline_reason": decline_reason,
                "auth_code": auth_code,
                "statement_descriptor": descriptor,
                "location_city": loc_city,
                "location_state": loc_state,
                "location_country": loc_country,
                "distance_from_home_km": distance_km,
                "is_international": is_international,
                "is_card_present": is_card_present,
                "ip_address": ip_addr,
                "device_type": device_type,
                "device_id": dev_id,
                "risk_score": risk_score,
                "is_fraud": is_fraud,
                "fraud_type": fraud_type,
            }
        )

    df = pd.DataFrame(transactions)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values(by="timestamp").reset_index(drop=True)
    return df


def main() -> None:
    args = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating banking dataset with seed {args.seed}...")
    print(
        f"Target row counts: {args.num_customers} customers, {args.num_merchants} merchants, {args.num_transactions} transactions"
    )

    # 1. Customers
    print("\n1. Generating customers...")
    customers_df = generate_customers_dataset(args.num_customers, seed=args.seed)
    cust_path = out_dir / "customers.parquet"
    customers_df.to_parquet(cust_path, index=False)
    print(f"Saved {len(customers_df)} customers to {cust_path}")

    # 2 & 3. Accounts and Cards (with 1-3 cards per customer guarantee)
    print("\n2 & 3. Generating accounts and cards...")
    accounts_df, cards_df = generate_accounts_and_cards_dataset(customers_df, seed=args.seed)
    acct_path = out_dir / "accounts.parquet"
    accounts_df.to_parquet(acct_path, index=False)
    print(f"Saved {len(accounts_df)} accounts to {acct_path}")

    cards_path = out_dir / "cards.parquet"
    cards_df.to_parquet(cards_path, index=False)
    print(f"Saved {len(cards_df)} cards to {cards_path}")

    # 4. Merchants
    print("\n4. Generating merchants...")
    merchants_df = generate_merchants_dataset(args.num_merchants, seed=args.seed)
    merch_path = out_dir / "merchants.parquet"
    merchants_df.to_parquet(merch_path, index=False)
    print(f"Saved {len(merchants_df)} merchants to {merch_path}")

    # 5. Transactions
    print("\n5. Generating transactions...")
    transactions_df = generate_transactions_dataset(
        customers_df=customers_df,
        accounts_df=accounts_df,
        cards_df=cards_df,
        merchants_df=merchants_df,
        num_transactions=args.num_transactions,
        seed=args.seed,
    )
    txn_path = out_dir / "transactions.parquet"
    transactions_df.to_parquet(txn_path, index=False)
    print(f"Saved {len(transactions_df)} transactions to {txn_path}")

    print("\n================ DATASET SUMMARY ================")
    print(f"1. customers:    {len(customers_df)} rows, {len(customers_df.columns)} columns")
    print(f"2. accounts:     {len(accounts_df)} rows, {len(accounts_df.columns)} columns")
    print(f"3. cards:        {len(cards_df)} rows, {len(cards_df.columns)} columns")
    print(f"4. merchants:    {len(merchants_df)} rows, {len(merchants_df.columns)} columns")
    print(f"5. transactions: {len(transactions_df)} rows, {len(transactions_df.columns)} columns")
    print("=================================================\n")


if __name__ == "__main__":
    main()
