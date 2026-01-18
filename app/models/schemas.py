from pydantic import BaseModel, Field
from typing import Optional, List, Dict

class TechnicalChecklist(BaseModel):
    weekly_trend_up: bool = False
    above_sma_200: bool = False
    above_sma_50: bool = False
    price_below_ema_20: bool = False  # Pullback indication
    rsi_value: float
    rsi_ok: bool = False  # 40-70 range
    rel_volume_ok: bool = False
    structure_shift_h4: bool = False # FxAlexG Style

class TradePlan(BaseModel):
    entry_range: str
    stop_loss: float
    take_profit_1: float
    take_profit_2: Optional[float] = None
    risk_reward: float
    position_size: float  # מחושב לפי 1% סיכון

class AnalysisResult(BaseModel):
    ticker: str
    price_at_analysis: float
    timeframe: str = "Daily/H4"
    checklist: TechnicalChecklist
    plan: TradePlan
    ai_fundamental_summary: Optional[str] = None
    score: int = Field(ge=0, le=10) # ציון סופי 0-10
    is_valid: bool = False # האם לשלוח מייל?