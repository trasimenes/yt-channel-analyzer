#!/usr/bin/env python3
"""
Script de démonstration du classificateur intelligent
"""

from yt_channel_analyzer.ai_classifier import industry_classifier

def demo_classification():
    """Démonstration de la classification intelligente"""
    print("🤖 Démonstration du Classificateur Intelligent")
    print("=" * 50)
    
    # Exemples de noms de chaînes à tester
    test_channels = [
        ("McDonald's France", ""),
        ("Club Med", "Travel and vacation experiences"),
        ("ClubMed", ""),
        ("Marriott Bonvoy", "Hotel loyalty program"),
        ("HILTON", "Luxury hotels worldwide"),
        ("Booking.com", "Hotel booking platform"),
        ("Airbnb", "Home sharing platform"),
        ("Apple", "Technology and innovation"),
        ("Tesla", "Electric vehicles and sustainable energy"),
        ("Nike", "Sports and fitness apparel"),
        ("Netflix", "Streaming entertainment"),
        ("Starbucks", "Coffee and café culture"),
        ("Gordon Ramsay", "Cooking shows and restaurants"),
        ("TechCrunch", "Technology news and startups"),
        ("Vogue", "Fashion and lifestyle magazine"),
    ]
    
    print("🔍 Test de classification automatique:\n")
    
    for channel_name, description in test_channels:
        print(f"📺 Chaîne: {channel_name}")
        
        # Classification de l'industrie
        industry = industry_classifier.classify_industry(channel_name, description, [])
        print(f"   🏢 Industrie détectée: {industry or 'Aucune'}")
        
        # Détection de la région
        region = industry_classifier.get_region_from_name(channel_name)
        print(f"   🌍 Région détectée: {region}")
        
        print()
    
    print("=" * 50)
    print("✅ Démonstration terminée!")
    print("\nLe classificateur utilise:")
    print("• Base de données de marques connues")
    print("• Analyse de mots-clés intelligente")
    print("• Détection géographique automatique")
    print("• Suggestion d'industrie par défaut si aucune détectée")

if __name__ == "__main__":
    demo_classification() 