from typing import TypedDict, Any, Literal

class NormalizedTradeRecord(TypedDict):
    source_chamber: Literal["senate", "house"]
    symbol: str
    issuer: str
    politician_name: str
    transaction_type: Literal["Purchase", "Sale", "Exchange", "Other"]
    transaction_date: str  # YYYY-MM-DD
    disclosure_date: str  # YYYY-MM-DD
    amount_range: str
    owner: Literal["Self", "Spouse", "Dependent Child", "Unknown"]
    link: str | None
    raw_record: dict[str, Any]