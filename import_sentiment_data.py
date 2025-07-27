#!/usr/bin/env python3
"""
Import sentiment analysis data into the application
"""
import sys
import json
import argparse

sys.path.append('.')

def import_sentiment_data(filename):
    """Import sentiment analysis data via API"""
    
    # Load the data from file
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in file: {e}")
        return False
    
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
            return False
        
        print("✅ Logged in successfully")
        
        # Prepare data for import
        import_data = {
            'videos': data.get('videos', [])
        }
        
        print(f"📥 Importing {len(import_data['videos'])} videos...")
        
        # Call the import API
        response = client.post('/api/sentiment-analysis/import',
                             json=import_data,
                             content_type='application/json')
        
        if response.status_code == 200:
            result = response.get_json()
            
            if result.get('success'):
                stats = result['stats']
                print(f"\n✅ Import successful!")
                print(f"\n📊 Import Statistics:")
                print(f"   Total videos: {stats['total']}")
                print(f"   Imported: {stats['imported']}")
                print(f"   Skipped: {stats['skipped']}")
                
                if result.get('errors'):
                    print(f"\n⚠️ Errors encountered:")
                    for error in result['errors']:
                        print(f"   - {error}")
                
                return True
            else:
                print(f"❌ Import failed: {result.get('error')}")
        else:
            print(f"❌ API request failed with status: {response.status_code}")
            print(response.get_data(as_text=True))
    
    return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Import sentiment analysis data')
    parser.add_argument('filename', help='JSON file to import')
    args = parser.parse_args()
    
    import_sentiment_data(args.filename)