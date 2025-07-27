#!/usr/bin/env python3
"""
Export sentiment analysis data from the application
"""
import sys
import json
import requests
from datetime import datetime

sys.path.append('.')

def export_sentiment_data():
    """Export sentiment analysis data via API"""
    
    # Create a test client to access the API
    from app import create_app
    
    app = create_app()
    
    with app.test_client() as client:
        # Login first
        login_data = {
            'username': 'baptiste',
            'password': 'Palermo1990'
        }
        login_response = client.post('/login', data=login_data, follow_redirects=True)
        
        if login_response.status_code != 200:
            print("❌ Login failed")
            return
        
        print("✅ Logged in successfully")
        
        # Call the export API
        response = client.get('/api/sentiment-analysis/export')
        
        if response.status_code == 200:
            data = response.get_json()
            
            if data.get('success'):
                # Save to file
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f'sentiment_analysis_export_{timestamp}.json'
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(data['data'], f, ensure_ascii=False, indent=2)
                
                stats = data['data']['stats']
                print(f"\n✅ Export successful!")
                print(f"📄 Data saved to: {filename}")
                print(f"\n📊 Statistics:")
                print(f"   Total videos analyzed: {stats['total_videos_analyzed']}")
                print(f"   Positive: {stats['positive_count']}")
                print(f"   Negative: {stats['negative_count']}")
                print(f"   Neutral: {stats['neutral_count']}")
                
                return filename
            else:
                print(f"❌ Export failed: {data.get('error')}")
        else:
            print(f"❌ API request failed with status: {response.status_code}")
            print(response.get_data(as_text=True))
    
    return None

if __name__ == "__main__":
    export_sentiment_data()