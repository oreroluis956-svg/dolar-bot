import json
import os
import datetime
import logging

logger = logging.getLogger(__name__)

class RateStorage:
    """Handle persistent storage of exchange rates"""
    
    def __init__(self, storage_file="rates_data.json"):
        self.storage_file = storage_file
        self.data = self._load_data()
    
    def _load_data(self):
        """Load data from storage file"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    logger.info("Rate data loaded from storage")
                    return data
            else:
                logger.info("No existing storage file, creating new data structure")
                return {"anterior": 0.0, "history": []}
        except Exception as e:
            logger.error(f"Error loading storage file: {e}")
            return {"anterior": 0.0, "history": []}
    
    def _save_data(self):
        """Save data to storage file"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.debug("Rate data saved to storage")
        except Exception as e:
            logger.error(f"Error saving storage file: {e}")
    
    def get_previous_rate(self):
        """Get the previous rate for comparison"""
        return self.data.get("anterior", 0.0)
    
    def save_rate(self, rate):
        """Save current rate and add to history"""
        try:
            now = datetime.datetime.now()
            
            # Update previous rate
            self.data["anterior"] = rate
            
            # Add to history
            if "history" not in self.data:
                self.data["history"] = []
            
            # Keep only last 30 days of history
            self.data["history"].append({
                "rate": rate,
                "timestamp": now.isoformat(),
                "date": now.strftime("%Y-%m-%d")
            })
            
            # Limit history to last 30 entries
            if len(self.data["history"]) > 30:
                self.data["history"] = self.data["history"][-30:]
            
            self._save_data()
            logger.debug(f"Rate saved: {rate}")
            
        except Exception as e:
            logger.error(f"Error saving rate: {e}")
    
    def get_history(self, days=7):
        """Get rate history for specified number of days"""
        try:
            history = self.data.get("history", [])
            # Return last N entries
            return history[-days:] if len(history) >= days else history
        except Exception as e:
            logger.error(f"Error getting history: {e}")
            return []
    
    def get_stats(self):
        """Get statistics about rates"""
        try:
            history = self.data.get("history", [])
            if not history:
                return None
            
            rates = [entry["rate"] for entry in history]
            
            return {
                "count": len(rates),
                "min": min(rates),
                "max": max(rates),
                "avg": sum(rates) / len(rates),
                "current": self.data.get("anterior", 0.0),
                "first_date": history[0]["date"] if history else None,
                "last_date": history[-1]["date"] if history else None
            }
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            return None
