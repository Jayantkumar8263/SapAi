import pandas as pd
from pathlib import Path


data = [
    {
        "A": "ABC",
        "C": "MAT00123456789",
        "E": "1000XXXX1",
        "Quantity": 100,
    },
    {
        "A": "XYZ",
        "C": "MAT00987654321",
        "E": "2000YYYY2",
        "Quantity": 250,
    },
    {
        "A": "DEF",
        "C": "MAT00555555555",
        "E": "3000ZZZZ3",
        "Quantity": 75,
    },
]

df = pd.DataFrame(data)

output = Path(__file__).parent / "data" / "mock_sap_inventory.xlsx"

output.parent.mkdir(parents=True, exist_ok=True)

df.to_excel(output, index=False)

print(f"Mock SAP data created: {output}")