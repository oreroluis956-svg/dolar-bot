from flask import Flask, render_template, jsonify
import logging
import os
import json
from datetime import datetime
from rate_storage import RateStorage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
storage = RateStorage()

# Global variable to store bot instance (will be set from main)
bot_instance = None

def set_bot_instance(bot):
    """Set the bot instance for web interface"""
    global bot_instance
    bot_instance = bot

@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('index.html')

@app.route('/api/status')
def api_status():
    """API endpoint for bot status"""
    try:
        if bot_instance:
            status = bot_instance.get_status()
        else:
            status = {
                'last_update': None,
                'last_rates': None,
                'scheduler_running': False,
                'chat_id': os.getenv('CHAT_ID', 'Not set')
            }
        
        # Add storage stats
        stats = storage.get_stats()
        if stats:
            status['stats'] = stats
        
        return jsonify({
            'success': True,
            'data': status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/history')
def api_history():
    """API endpoint for rate history"""
    try:
        days = int(request.args.get('days', 7))
        history = storage.get_history(days)
        
        return jsonify({
            'success': True,
            'data': history,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/logs')
def api_logs():
    """API endpoint for recent logs"""
    try:
        log_file = 'bot.log'
        logs = []
        
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                # Get last 50 lines
                lines = f.readlines()
                logs = lines[-50:] if len(lines) > 50 else lines
        
        return jsonify({
            'success': True,
            'data': [line.strip() for line in logs],
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting logs: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0'
    })

def start_web_interface():
    """Start the web interface"""
    try:
        logger.info("Starting web interface on port 5000...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        logger.error(f"Failed to start web interface: {e}")
        raise

if __name__ == "__main__":
    start_web_interface()
