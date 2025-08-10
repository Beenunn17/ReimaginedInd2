# agent-python-backend/create_dummy_data.py
import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
output_dir = os.path.join(HERE, "data")
os.makedirs(output_dir, exist_ok=True)

def create_all_datasets():
    num_records = 1000
    start_date = datetime(2022, 1, 1)

    # 1) MMM
    dates = [start_date + timedelta(weeks=i) for i in range(156)]
    num_weeks = len(dates)
    mmm_data = {
        "Date": dates,
        "Sales": np.random.uniform(150000, 500000, num_weeks).round(2),
        "TV_Spend": np.random.uniform(20000, 70000, num_weeks).round(2),
        "Radio_Spend": np.random.uniform(10000, 30000, num_weeks).round(2),
        "Social_Media_Spend": np.random.uniform(15000, 50000, num_weeks).round(2),
        "Search_Spend": np.random.uniform(25000, 60000, num_weeks).round(2),
        "OOH_Spend": np.random.uniform(5000, 25000, num_weeks).round(2),
        "Print_Spend": np.random.uniform(2000, 15000, num_weeks).round(2),
        "Affiliate_Spend": np.random.uniform(8000, 20000, num_weeks).round(2),
        "Direct_Mail_Spend": np.random.uniform(3000, 18000, num_weeks).round(2),
        "Podcast_Spend": np.random.uniform(4000, 22000, num_weeks).round(2),
        "Influencer_Spend": np.random.uniform(6000, 35000, num_weeks).round(2),
        "Competitor_Spend": np.random.uniform(50000, 150000, num_weeks).round(2),
        "Inflation_Index": np.linspace(1.0, 1.08, num_weeks).round(3),
    }
    pd.DataFrame(mmm_data).to_csv(os.path.join(output_dir, "mmm_advanced_data.csv"), index=False)

    # 2) Churn
    churn_data = {
        "CustomerID": range(1, num_records + 1),
        "TenureMonths": np.random.randint(1, 72, num_records),
        "MonthlyCharge": np.random.uniform(20, 120, num_records).round(2),
        "FeaturesUsed": np.random.randint(1, 8, num_records),
        "SupportTickets": np.random.randint(0, 10, num_records),
        "Churn": np.random.choice([0, 1], num_records, p=[0.7, 0.3]),
    }
    pd.DataFrame(churn_data).to_csv(os.path.join(output_dir, "customer_churn.csv"), index=False)

    # 3) Campaign performance
    campaign_dates = [start_date + timedelta(days=i) for i in range(365)]
    campaign_ids = ["A", "B", "C"]
    campaign_data = {
        "Date": np.random.choice(campaign_dates, num_records),
        "CampaignID": np.random.choice(campaign_ids, num_records),
        "Impressions": np.random.randint(10000, 100000, num_records),
        "Clicks": np.random.randint(100, 5000, num_records),
        "Spend": np.random.uniform(500, 5000, num_records).round(2),
        "Conversions": np.random.randint(10, 200, num_records),
    }
    pd.DataFrame(campaign_data).sort_values("Date").to_csv(os.path.join(output_dir, "campaign_performance.csv"), index=False)

    # 4) Retail sales
    products = {
        "SKU-101": {"Name": "Pro Carbon Stick", "Category": "Sticks", "Cost": 150.0},
        "SKU-201": {"Name": "Vapor Flex Skates", "Category": "Skates", "Cost": 300.0},
        "SKU-301": {"Name": "AeroLite Helmet", "Category": "Helmets", "Cost": 80.0},
        "SKU-401": {"Name": "Stealth Pro Gloves", "Category": "Gloves", "Cost": 90.0},
    }
    skus = list(products.keys())
    transaction_skus = np.random.choice(skus, num_records)
    retail_data = {
        "Date": [start_date + timedelta(days=np.random.randint(0, 730)) for _ in range(num_records)],
        "SKU": transaction_skus,
        "ProductName": [products[sku]["Name"] for sku in transaction_skus],
        "Category": [products[sku]["Category"] for sku in transaction_skus],
        "Cost": [products[sku]["Cost"] for sku in transaction_skus],
        "Sales": [products[sku]["Cost"] * np.random.uniform(1.5, 2.5) for sku in transaction_skus],
        "Promotion": np.random.choice(["None", "10% Off"], num_records, p=[0.8, 0.2]),
        "Weather": np.random.choice(["Sunny", "Rain", "Snow"], num_records),
        "Holiday": np.random.choice([0, 1], num_records, p=[0.95, 0.05]),
    }
    df_retail = pd.DataFrame(retail_data)
    df_retail["Profit"] = df_retail["Sales"] - df_retail["Cost"]
    df_retail[["Sales", "Profit"]] = df_retail[["Sales", "Profit"]].round(2)
    df_retail.sort_values("Date").to_csv(os.path.join(output_dir, "retail_sales.csv"), index=False)

    # 5) CLTV
    cltv_data = {
        "CustomerID": np.random.randint(1, 200, num_records),
        "TransactionDate": [start_date + timedelta(days=np.random.randint(0, 730)) for _ in range(num_records)],
        "TransactionValue": np.random.uniform(25, 500, num_records).round(2),
    }
    pd.DataFrame(cltv_data).sort_values("TransactionDate").to_csv(os.path.join(output_dir, "cltv_data.csv"), index=False)

    # 6) Recommendations
    reco_data = {
        "UserID": np.random.randint(1, 100, num_records),
        "ProductID": np.random.randint(1, 50, num_records),
        "Category": np.random.choice(["Electronics", "Apparel", "Gear", "Accessories"], num_records),
        "Rating": np.random.randint(1, 6, num_records),
    }
    pd.DataFrame(reco_data).to_csv(os.path.join(output_dir, "product_recommendations.csv"), index=False)

    # 7) Behavior
    behavior_data = {
        "SessionID": range(1, num_records + 1),
        "PagesViewed": np.random.randint(1, 25, num_records),
        "TimeOnSiteMinutes": np.random.uniform(0.5, 45, num_records).round(1),
        "Device": np.random.choice(["Mobile", "Desktop"], num_records, p=[0.6, 0.4]),
        "Converted": np.random.choice([0, 1], num_records, p=[0.9, 0.1]),
    }
    pd.DataFrame(behavior_data).to_csv(os.path.join(output_dir, "customer_behavior.csv"), index=False)

if __name__ == "__main__":
    create_all_datasets()
    print("Data creation script finished successfully:", output_dir)
