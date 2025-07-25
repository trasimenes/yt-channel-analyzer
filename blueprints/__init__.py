"""
Blueprints Module
Modular architecture for YT Channel Analyzer
Replaces the monolithic 10,122-line app.py with clean, maintainable blueprints.

Architecture:
- auth.py: Authentication and user management (152 lines)
- main.py: Core application routes and dashboard (172 lines)  
- api.py: All API endpoints and JSON responses (418 lines)
- competitors.py: Competitor management and analysis (346 lines)
- insights.py: Analytics, insights, and data visualization (416 lines)
- admin.py: Administrative functions and settings (550 lines)
- utils.py: Common utilities and helper functions (300 lines)

Total: ~2,354 lines across 7 organized modules
Previously: 10,122 lines in a single monolithic file

Benefits:
✅ Separation of concerns
✅ Improved maintainability
✅ Easier unit testing
✅ Better team collaboration
✅ Conditional module loading
✅ Scalable architecture
"""

__version__ = "2.0.0"
__author__ = "YT Channel Analyzer Team"
__description__ = "Modular Flask blueprint architecture"

# Blueprint registry for documentation
BLUEPRINTS = {
    'auth': {
        'file': 'auth.py',
        'description': 'Authentication and user management',
        'routes': 15,
        'lines': 152
    },
    'main': {
        'file': 'main.py', 
        'description': 'Core application routes and dashboard',
        'routes': 10,
        'lines': 172
    },
    'api': {
        'file': 'api.py',
        'description': 'All API endpoints and JSON responses', 
        'routes': 50,
        'lines': 418
    },
    'competitors': {
        'file': 'competitors.py',
        'description': 'Competitor management and analysis',
        'routes': 30, 
        'lines': 346
    },
    'insights': {
        'file': 'insights.py',
        'description': 'Analytics, insights, and data visualization',
        'routes': 25,
        'lines': 416
    },
    'admin': {
        'file': 'admin.py',
        'description': 'Administrative functions and settings',
        'routes': 20,
        'lines': 550
    }
}

def get_blueprint_info():
    """Get information about all blueprints"""
    total_routes = sum(bp['routes'] for bp in BLUEPRINTS.values())
    total_lines = sum(bp['lines'] for bp in BLUEPRINTS.values())
    
    return {
        'total_blueprints': len(BLUEPRINTS),
        'total_routes': total_routes,
        'total_lines': total_lines,
        'blueprints': BLUEPRINTS
    }