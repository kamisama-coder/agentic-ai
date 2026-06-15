from unit_saas.loader import loader,load_user_functions
import pandas as pd

if __name__ == "__main__":

    rules =  "Show me the total revenue for each product, sorted from highest to lowest"

    data = {
    "orderID": [1001, 1002, 1003, 1004, 1005, 1006, 1007],
    "customerID": [501, 502, 503, 501, 504, 505, 502],
    "customerName": ["Alice", "Bob", "Charlie", "Alice", "David", "Eve", "Bob"],
    "product": ["Laptop", "Phone", "Tablet", "Laptop", "Monitor", "Phone", "Tablet"],
    "Category": ["Electronics", "Electronics", "Electronics", "Electronics", "Electronics", "Electronics", "Electronics"],
    "units": [2, 5, 3, 1, 4, 2, 1],
    "unitPrice": [1200, 500, 300, 1200, 250, 500, 300],
    "revenue": [2400, 2500, 900, 1200, 1000, 1000, 300],
    "orderDate": pd.to_datetime([
        "2025-01-01", "2025-01-02", "2025-01-03",
        "2025-01-05", "2025-01-07", "2025-01-08", "2025-01-09"
    ]),
    "region": ["North", "South", "East", "North", "West", "South", "South"]
}

    security_token = "9b233321eb50c643d31d9643e2099bba823f3b2ddfb88219a604148f9c74b318"
    hello,world = loader(data=data,rules=rules,security_token=security_token,gemini_key="AQ.Ab8RN6I8oG9SxnwedHHhKtfAHJSwq_DXtPPB9Jggu_wHKTAm5g",address="https://agentic-ai-nt21.onrender.com/call")
    print(hello)
    print(world)

