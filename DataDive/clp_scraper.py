import requests
import trafilatura
import re
import logging

logger = logging.getLogger(__name__)

class CLPTodayScraper:
    """Scraper for @clptoday exchange rates"""
    
    def __init__(self):
        self.base_url = "https://clptoday.com"
        
    def get_rates(self):
        """Extract exchange rates from CLP Today website"""
        try:
            # Fetch the website content
            downloaded = trafilatura.fetch_url(self.base_url)
            if not downloaded:
                logger.error("Failed to download CLP Today website")
                return None
                
            text = trafilatura.extract(downloaded)
            if not text:
                logger.error("Failed to extract text from CLP Today website")
                return None
            
            rates = {}
            
            # Look for USD rates (Zelle, PayPal, etc.)
            usd_patterns = {
                'zelle': r'zelle.*?(\d+[,.]?\d*)',
                'paypal': r'paypal.*?(\d+[,.]?\d*)',
                'usd': r'dólar.*?(\d+[,.]?\d*)',
                'dollar': r'dollar.*?(\d+[,.]?\d*)'
            }
            
            # Look for EUR rates
            eur_patterns = {
                'euro': r'euro.*?(\d+[,.]?\d*)',
                'eur': r'eur.*?(\d+[,.]?\d*)',
                '€': r'€.*?(\d+[,.]?\d*)'
            }
            
            text_lower = text.lower()
            
            # Extract USD-related rates
            for key, pattern in usd_patterns.items():
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    try:
                        # Take the first valid number found
                        rate_str = matches[0].replace(',', '.')
                        rate = float(rate_str)
                        if rate > 0:
                            rates[f'usd_{key}'] = rate
                            logger.info(f"Found {key} rate: {rate}")
                    except (ValueError, IndexError):
                        continue
            
            # Extract EUR rates
            for key, pattern in eur_patterns.items():
                matches = re.findall(pattern, text_lower, re.IGNORECASE)
                if matches:
                    try:
                        rate_str = matches[0].replace(',', '.')
                        rate = float(rate_str)
                        if rate > 0:
                            rates[f'eur_{key}'] = rate
                            logger.info(f"Found EUR rate: {rate}")
                    except (ValueError, IndexError):
                        continue
            
            return rates if rates else None
            
        except Exception as e:
            logger.error(f"Error scraping CLP Today: {e}")
            return None
    
    def get_specific_rates(self):
        """Get structured rates for USD and EUR"""
        raw_rates = self.get_rates()
        if not raw_rates:
            return None
            
        structured_rates = {
            'usd': {},
            'eur': {}
        }
        
        # Process USD rates
        usd_keys = [k for k in raw_rates.keys() if k.startswith('usd_')]
        if usd_keys:
            # Try to find Zelle rate
            zelle_rate = raw_rates.get('usd_zelle')
            if zelle_rate:
                structured_rates['usd']['zelle'] = zelle_rate
            
            # Try to find PayPal rate  
            paypal_rate = raw_rates.get('usd_paypal')
            if paypal_rate:
                structured_rates['usd']['paypal'] = paypal_rate
            
            # If no specific rates found, use general USD rate
            if not structured_rates['usd']:
                general_usd = raw_rates.get('usd_usd') or raw_rates.get('usd_dollar')
                if general_usd:
                    structured_rates['usd']['general'] = general_usd
        
        # Process EUR rates
        eur_keys = [k for k in raw_rates.keys() if k.startswith('eur_')]
        if eur_keys:
            eur_rate = raw_rates.get('eur_euro') or raw_rates.get('eur_eur') or raw_rates.get('eur_€')
            if eur_rate:
                structured_rates['eur']['rate'] = eur_rate
        
        return structured_rates if (structured_rates['usd'] or structured_rates['eur']) else None