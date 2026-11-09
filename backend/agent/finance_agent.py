# backend/agent/finance_agent.py — Personal Finance Agent
# Expense tracking (BDT), budgets, monthly reports and anomaly detection.
from __future__ import annotations

import re
import sqlite3
import statistics
from datetime import datetime
from typing import Any, Dict, List, Optional

import config
from backend.analytics.spending_analytics import spending_analytics
from .advanced_common import (
    bn_to_en_digits,
    clean_text,
    data_file,
    extract_amount,
    fail,
    ok,
    read_json,
    write_json,
)

BUDGET_FILE = data_file("finance_budgets.json")
CATEGORY_KEYWORDS = {
    "food": ("food", "lunch", "dinner", "breakfast", "snack", "restaurant", "খাবার", "লাঞ্চ", "ডিনার", "নাস্তা", "রেস্টুরেন্ট"),
    "transport": ("transport", "bus", "rickshaw", "uber", "pathao", "cng", "fuel", "যাতায়াত", "বাস", "রিকশা", "উবার", "তেল"),
    "bills": ("bill", "electricity", "water", "gas", "internet", "wifi", "mobile", "recharge", "বিল", "বিদ্যুৎ", "গ্যাস", "ইন্টারনেট", "রিচার্জ"),
    "shopping": ("shopping", "clothes", "shoe", "gift", "কেনাকাটা", "শপিং", "জামা", "জুতা", "গিফট"),
    "health": ("medicine", "doctor", "hospital", "health", "pharmacy", "ঔষধ", "ডাক্তার", "হাসপাতাল", "স্বাস্থ্য"),
    "education": ("book", "course", "tuition", "exam", "study", "বই", "কোর্স", "টিউশন", "পরীক্ষা", "শিক্ষা"),
    "entertainment": ("movie", "game", "netflix", "spotify", "concert", "সিনেমা", "গেম", "বিনোদন"),
    "rent": ("rent", "house", "flat", "ভাড়া", "বাসা"),
}
CATEGORY_LABELS = {
    "food": "🍔 Food", "transport": "🚌 Transport", "bills": "🧾 Bills", "shopping": "🛍️ Shopping",
    "health": "💊 Health", "education": "📚 Education", "entertainment": "🎬 Entertainment",
    "rent": "🏠 Rent", "other": "📦 Other",
}


class FinanceAgent:
    name = "Personal Finance Agent"

    def get_capabilities(self) -> List[str]:
        return ["finance_add", "finance_summary", "finance_budget", "finance_set_budget", "finance_anomalies"]

    def handle(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        entities = entities or {}
        command = str(entities.get("_command", ""))
        intent_lower = str(intent or "").lower()
        lower = command.lower()

        try:
            if "set_budget" in intent_lower or "budget set" in lower or "বাজেট সেট" in command:
                amount = float(entities.get("amount") or extract_amount(command) or 0)
                category = str(entities.get("category") or self._category(command) or "other")
                return self.set_budget(category, amount)
            if "budget" in intent_lower or "budget" in lower or "বাজেট" in command:
                return self.budget_report()
            if any(word in intent_lower for word in ("summary", "report", "anomaly")) or any(
                word in lower for word in ("summary", "report", "anomaly", "hisab")
            ) or any(
                word in command for word in ("কত খরচ", "খরচ কত", "রিপোর্ট", "হিসাব")
            ):
                return self.summary(int(entities.get("days") or 30))
            return self.add_expense(
                float(entities.get("amount") or extract_amount(command) or 0),
                str(entities.get("category") or self._category(command) or "other"),
                str(entities.get("note") or self._note(command) or ""),
            )
        except Exception as exc:
            return fail("finance", f"Finance Agent error: {exc}")

    # ---------------- actions ----------------
    def add_expense(self, amount: float, category: str = "other", note: str = "") -> Dict[str, Any]:
        if not amount or amount <= 0:
            return fail("finance", "কত টাকা খরচ হয়েছে বলুন, যেমন: “expense 250 lunch”।")

        category = self._normalize_category(category)
        category = self._normalize_category(self._category(f"{category} {note}") or category)
        result = spending_analytics.add(amount, category, note or None)
        summary = self.summary(days=30, include_list=False)
        budget = self._budget_status(category, summary.get("by_category", []))

        message = f"💸 ৳{amount:,.0f} added under {CATEGORY_LABELS.get(category, category)}."
        if budget.get("over"):
            message += f" ⚠️ {category} budget exceeded by ৳{budget['over']:,.0f}."
        elif budget.get("remaining") is not None:
            message += f" Budget remaining: ৳{budget['remaining']:,.0f}."

        return ok(
            "finance",
            message,
            expense=result,
            category=category,
            budget=budget,
            month_total=summary.get("total"),
        )

    def summary(self, days: int = 30, include_list: bool = True) -> Dict[str, Any]:
        days = max(1, min(int(days), 365))
        result = spending_analytics.summary(days=days)
        budgets = self._budgets()
        budget_rows = []
        category_totals = {item["category"]: float(item["total"]) for item in result.get("by_category", [])}
        for category, limit in (budgets.get("categories") or {}).items():
            spent = category_totals.get(category, 0)
            budget_rows.append({
                "category": category,
                "label": CATEGORY_LABELS.get(category, category),
                "limit": limit,
                "spent": round(spent, 2),
                "remaining": round(limit - spent, 2),
                "percent": round(spent / limit * 100, 1) if limit else 0,
            })
        if budgets.get("total_monthly"):
            spent = result.get("total", 0)
            budget_rows.append({
                "category": "total",
                "label": "Total",
                "limit": budgets["total_monthly"],
                "spent": spent,
                "remaining": round(budgets["total_monthly"] - spent, 2),
                "percent": round(spent / budgets["total_monthly"] * 100, 1),
            })

        anomalies = self._anomalies(days)
        payload = {
            **result,
            "budgets": budget_rows,
            "anomalies": anomalies,
            "top_category": (result.get("by_category") or [{}])[0].get("category") if result.get("by_category") else None,
        }
        if include_list:
            payload["recent"] = self._recent_expenses(days, limit=10)

        if not result.get("count"):
            return ok("finance", "এই সময়ে কোনো expense নেই। “expense 250 lunch” দিয়ে যোগ করুন।", **payload)
        return ok(
            "finance",
            f"💰 Last {days} days: ৳{result['total']:,.0f} across {result['count']} expense(s).",
            **payload,
        )

    def set_budget(self, category: str, amount: float) -> Dict[str, Any]:
        if not amount or amount <= 0:
            return fail("finance", "Budget amount দিন, যেমন: “set budget food 5000”।")
        category = self._normalize_category(category)
        budgets = self._budgets()
        if category == "total":
            budgets["total_monthly"] = float(amount)
        else:
            budgets.setdefault("categories", {})[category] = float(amount)
        budgets["updated_at"] = datetime.now().isoformat(timespec="seconds")
        write_json(BUDGET_FILE, budgets)
        return ok("finance", f"🎯 {CATEGORY_LABELS.get(category, category)} budget: ৳{amount:,.0f}/month.", budgets=budgets)

    def budget_report(self) -> Dict[str, Any]:
        summary = self.summary(days=30, include_list=False)
        return ok(
            "finance",
            f"🎯 {len(summary.get('budgets', []))} budget(s) configured.",
            budgets=summary.get("budgets", []),
            month_total=summary.get("total"),
        )

    # ---------------- storage helpers ----------------
    @staticmethod
    def _budgets() -> Dict[str, Any]:
        data = read_json(BUDGET_FILE, {"categories": {}, "total_monthly": 0})
        if not isinstance(data, dict):
            data = {"categories": {}, "total_monthly": 0}
        data.setdefault("categories", {})
        return data

    def _budget_status(self, category: str, by_category: List[Dict[str, Any]]) -> Dict[str, Any]:
        budgets = self._budgets()
        limit = (budgets.get("categories") or {}).get(category)
        if not limit:
            return {}
        spent = next((float(item["total"]) for item in by_category if item.get("category") == category), 0)
        return {
            "limit": limit,
            "spent": round(spent, 2),
            "remaining": round(limit - spent, 2),
            "over": round(spent - limit, 2) if spent > limit else 0,
        }

    @staticmethod
    def _recent_expenses(days: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            connection = sqlite3.connect(str(config.DB_ANALYTICS))
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT amount, category, note, ts FROM expenses "
                "WHERE ts >= datetime('now', ?) ORDER BY ts DESC LIMIT ?",
                (f"-{int(days)} days", int(limit)),
            ).fetchall()
            connection.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    @staticmethod
    def _anomalies(days: int) -> List[Dict[str, Any]]:
        rows = FinanceAgent._recent_expenses(days, limit=300)
        if len(rows) < 5:
            return []
        amounts = [float(row["amount"]) for row in rows]
        mean = statistics.mean(amounts)
        stdev = statistics.pstdev(amounts)
        if stdev == 0:
            return []
        threshold = mean + 2 * stdev
        return [
            {"amount": row["amount"], "category": row["category"], "note": row["note"], "ts": row["ts"], "reason": "2σ above average"}
            for row in rows if float(row["amount"]) > threshold
        ][:5]

    # ---------------- parsing ----------------
    @staticmethod
    def _category(text: str) -> str:
        lower = str(text or "").lower()
        for category, words in CATEGORY_KEYWORDS.items():
            if any(word.lower() in lower for word in words):
                return category
        return ""

    @staticmethod
    def _normalize_category(category: str) -> str:
        category = clean_text(category).lower()
        aliases = {
            "খাবার": "food", "যাতায়াত": "transport", "বিল": "bills", "কেনাকাটা": "shopping",
            "স্বাস্থ্য": "health", "শিক্ষা": "education", "বিনোদন": "entertainment",
            "ভাড়া": "rent", "total": "total", "all": "total",
        }
        return aliases.get(category, category if category in CATEGORY_LABELS or category == "total" else "other")

    @staticmethod
    def _note(command: str) -> str:
        text = re.sub(r"(?i)\b(?:expense|add|khoro?ch|khoroch|খরচ|টাকা|taka|tk|৳)\b", " ", command)
        text = re.sub(r"\d+(?:[.,]\d+)?", " ", text)
        return clean_text(text).strip(" -:,")

    def test(self) -> Dict[str, Any]:
        summary = spending_analytics.summary(days=30)
        return {
            "success": True,
            "agent": "finance",
            "expenses": summary.get("count", 0),
            "total_bdt": summary.get("total", 0),
            "budgets": len(self._budgets().get("categories") or {}),
            "message": "Finance Agent ready (BDT).",
        }


finance_agent = FinanceAgent()
