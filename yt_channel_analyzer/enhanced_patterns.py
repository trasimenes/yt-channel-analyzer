"""
Patterns enrichis pour la classification vidéo avec focus sur les descriptions
🎯 Amélioration spécifique pour utiliser le contexte des descriptions
"""

# Patterns spécifiques pour les descriptions
DESCRIPTION_PATTERNS = {
    'fr': {
        'hero': [
            # Expressions marketing/promotional dans les descriptions
            'nouveau concept', 'innovation majeure', 'annonce exclusive', 'révélation surprise',
            'première mondiale', 'lancement officiel', 'découverte inédite', 'événement spécial',
            'offre limitée', 'édition spéciale', 'collection exclusive', 'avant-première',
            'campagne publicitaire', 'brand activation', 'marketing campaign', 'product launch',
            'grand opening', 'inauguration', 'ouverture officielle', 'événement média',
            'présentation produit', 'showcase', 'démo exclusive', 'preview',
            'teaser', 'trailer', 'bande annonce', 'aperçu exclusif',
            # Call-to-action typiques HERO
            'découvrez notre', 'explorez notre', 'laissez-vous séduire', 'plongez dans',
            'vivez l\'expérience', 'participez à', 'rejoignez-nous', 'réservez maintenant',
            # Superlatifs marketing
            'le plus grand', 'la plus belle', 'jamais vu', 'sans précédent', 'révolutionnaire',
            'extraordinaire expérience', 'moment magique', 'souvenir inoubliable'
        ],
        'hub': [
            # Expressions lifestyle/communautaires
            'série documentaire', 'collection de vidéos', 'chaîne thématique', 'contenu régulier',
            'épisode de la série', 'suite de l\'histoire', 'continuation', 'prochaine partie',
            'rendez-vous hebdomadaire', 'format récurrent', 'programme régulier', 'émission',
            'témoignage client', 'retour d\'expérience', 'avis utilisateur', 'feedback',
            'voyage immersif', 'expérience authentique', 'découverte culturelle', 'exploration',
            'behind the scenes', 'coulisses', 'making of', 'processus créatif',
            'communauté', 'partage d\'expérience', 'échange', 'discussion',
            'lifestyle content', 'contenu lifestyle', 'mode de vie', 'quotidien',
            # Expressions d'appartenance
            'notre communauté', 'nos membres', 'famille', 'ensemble', 'partageons',
            'suivez-nous', 'abonnez-vous', 'restez connectés', 'prochaine vidéo',
            # Storytelling
            'notre histoire', 'voici comment', 'laissez-moi vous raconter', 'découvrons ensemble'
        ],
        'help': [
            # Expressions techniques/éducatives
            'problème courant', 'erreur fréquente', 'difficulté rencontrée', 'issue commune',
            'solution détaillée', 'guide complet', 'tutoriel pas à pas', 'explication claire',
            'résolution de problème', 'dépannage technique', 'aide technique', 'support client',
            'questions fréquentes', 'FAQ', 'réponses aux questions', 'clarifications',
            'mode d\'emploi', 'instructions détaillées', 'procédure complète', 'marche à suivre',
            'conseils pratiques', 'astuces utiles', 'tips', 'recommandations',
            'configuration requise', 'prérequis', 'conditions nécessaires', 'setup',
            'troubleshooting', 'diagnostic', 'identification du problème', 'analyse',
            'étape par étape', 'step by step', 'progressif', 'méthodique',
            'pour débutants', 'pour novices', 'initiation', 'apprentissage de base',
            # Expressions pédagogiques
            'apprenez à', 'découvrez comment', 'voici comment', 'je vous montre',
            'suivez ces étapes', 'dans cette vidéo', 'vous allez apprendre', 'explication simple',
            'résoudre rapidement', 'solution efficace', 'méthode éprouvée', 'technique simple'
        ]
    },
    'en': {
        'hero': [
            'new concept', 'major innovation', 'exclusive announcement', 'surprise reveal',
            'world premiere', 'official launch', 'unique discovery', 'special event',
            'limited offer', 'special edition', 'exclusive collection', 'preview',
            'advertising campaign', 'brand activation', 'marketing campaign', 'product launch',
            'grand opening', 'inauguration', 'official opening', 'media event',
            'product presentation', 'showcase', 'exclusive demo', 'preview',
            'teaser', 'trailer', 'exclusive glimpse',
            'discover our', 'explore our', 'experience the', 'join us',
            'book now', 'reserve today', 'don\'t miss out', 'limited time',
            'never before seen', 'unprecedented', 'revolutionary experience',
            'magical moment', 'unforgettable memory'
        ],
        'hub': [
            'documentary series', 'video collection', 'thematic channel', 'regular content',
            'series episode', 'story continuation', 'next part',
            'weekly appointment', 'recurring format', 'regular program', 'show',
            'customer testimony', 'user experience', 'feedback',
            'immersive journey', 'authentic experience', 'cultural discovery', 'exploration',
            'behind the scenes', 'making of', 'creative process',
            'community', 'experience sharing', 'exchange', 'discussion',
            'lifestyle content',
            'our community', 'our members', 'family', 'together', 'let\'s share',
            'follow us', 'subscribe', 'stay connected', 'next video',
            'our story', 'here\'s how', 'let me tell you', 'let\'s discover together'
        ],
        'help': [
            'common problem', 'frequent error', 'common issue',
            'detailed solution', 'complete guide', 'step-by-step tutorial', 'clear explanation',
            'problem resolution', 'technical troubleshooting', 'technical help', 'customer support',
            'frequently asked questions', 'FAQ', 'answers to questions', 'clarifications',
            'user manual', 'detailed instructions', 'complete procedure', 'how to',
            'practical advice', 'useful tips', 'recommendations',
            'system requirements', 'prerequisites', 'necessary conditions', 'setup',
            'troubleshooting', 'diagnosis', 'problem identification', 'analysis',
            'step by step', 'progressive', 'methodical',
            'for beginners', 'for novices', 'basic learning',
            'learn how to', 'discover how to', 'here\'s how to', 'I\'ll show you',
            'follow these steps', 'in this video', 'you will learn', 'simple explanation',
            'quick fix', 'effective solution', 'proven method', 'simple technique'
        ]
    },
    'de': {
        'hero': [
            # Patterns HERO allemands
            'neues konzept', 'große innovation', 'exklusive ankündigung', 'überraschende enthüllung',
            'weltpremiere', 'offizieller start', 'einzigartige entdeckung', 'besonderes ereignis',
            'limitiertes angebot', 'sonderausgabe', 'exklusive kollektion', 'vorschau',
            'werbekampagne', 'markenaktivierung', 'produkteinführung',
            'große eröffnung', 'einweihung', 'offizielle eröffnung', 'medienereignis',
            'produktpräsentation', 'präsentation', 'exklusive demo', 'vorschau',
            'teaser', 'trailer', 'exklusiver einblick',
            # Call-to-action deutsch
            'entdecken sie unsere', 'erkunden sie unsere', 'lassen sie sich verführen', 'tauchen sie ein',
            'erleben sie', 'nehmen sie teil', 'werden sie teil', 'buchen sie jetzt',
            # Superlatifs allemands
            'das größte', 'das schönste', 'nie gesehen', 'beispiellos', 'revolutionär',
            'außergewöhnliche erfahrung', 'magischer moment', 'unvergessliche erinnerung'
        ],
        'hub': [
            # Patterns HUB allemands
            'dokumentarserie', 'video sammlung', 'thematischer kanal', 'regelmäßiger inhalt',
            'serienfolge', 'fortsetzung der geschichte', 'fortsetzung', 'nächster teil',
            'wöchentlicher termin', 'wiederkehrendes format', 'regelmäßiges programm', 'sendung',
            'kundenmeinung', 'erfahrungsbericht', 'nutzerbewertung', 'rückmeldung',
            'immersive reise', 'authentische erfahrung', 'kulturelle entdeckung', 'erkundung',
            'hinter den kulissen', 'making of', 'kreativer prozess',
            'gemeinschaft', 'erfahrungsaustausch', 'austausch', 'diskussion',
            'lifestyle inhalt',
            # Expressions d'appartenance allemandes
            'unsere gemeinschaft', 'unsere mitglieder', 'familie', 'zusammen', 'teilen wir',
            'folgen sie uns', 'abonnieren sie', 'bleiben sie verbunden', 'nächstes video',
            # Storytelling allemand
            'unsere geschichte', 'so geht es', 'lassen sie mich erzählen', 'entdecken wir gemeinsam'
        ],
        'help': [
            # Patterns HELP allemands
            'häufiges problem', 'häufiger fehler', 'aufgetretene schwierigkeit', 'gemeinsames problem',
            'detaillierte lösung', 'vollständiger leitfaden', 'schritt-für-schritt anleitung', 'klare erklärung',
            'problemlösung', 'technische fehlerbehebung', 'technische hilfe', 'kundensupport',
            'häufig gestellte fragen', 'FAQ', 'antworten auf fragen', 'klarstellungen',
            'benutzerhandbuch', 'detaillierte anweisungen', 'vollständiges verfahren', 'anleitung',
            'praktische tipps', 'nützliche tipps', 'empfehlungen',
            'systemanforderungen', 'voraussetzungen', 'notwendige bedingungen', 'einrichtung',
            'fehlerbehebung', 'diagnose', 'problemidentifikation', 'analyse',
            'schritt für schritt', 'schrittweise', 'methodisch',
            'für anfänger', 'für einsteiger', 'einführung', 'grundlegendes lernen',
            # Expressions pédagogiques allemandes
            'lernen sie', 'entdecken sie wie', 'so geht es', 'ich zeige ihnen',
            'folgen sie diesen schritten', 'in diesem video', 'sie werden lernen', 'einfache erklärung',
            'schnell lösen', 'effektive lösung', 'bewährte methode', 'einfache technik'
        ]
    },
    'nl': {
        'hero': [
            # Patterns HERO néerlandais
            'nieuw concept', 'grote innovatie', 'exclusieve aankondiging', 'verrassende onthulling',
            'wereldpremière', 'officiële lancering', 'unieke ontdekking', 'speciale gebeurtenis',
            'beperkt aanbod', 'speciale editie', 'exclusieve collectie', 'preview',
            'reclamecampagne', 'merkactivering', 'productlancering',
            'grote opening', 'inwijding', 'officiële opening', 'media-evenement',
            'productpresentatie', 'showcase', 'exclusieve demo', 'voorvertoning',
            'teaser', 'trailer', 'exclusieve blik',
            # Call-to-action néerlandais
            'ontdek onze', 'verken onze', 'laat je verleiden', 'duik in',
            'beleef de ervaring', 'doe mee', 'word lid', 'boek nu',
            # Superlatifs néerlandais
            'het grootste', 'het mooiste', 'nooit eerder gezien', 'ongekend', 'revolutionair',
            'buitengewone ervaring', 'magisch moment', 'onvergetelijke herinnering'
        ],
        'hub': [
            # Patterns HUB néerlandais
            'documentaireserie', 'videoverzameling', 'thematisch kanaal', 'reguliere content',
            'serie-aflevering', 'vervolg van het verhaal', 'voortzetting', 'volgend deel',
            'wekelijkse afspraak', 'terugkerend format', 'regulair programma', 'show',
            'klantgetuigenis', 'gebruikerservaring', 'feedback',
            'meeslepende reis', 'authentieke ervaring', 'culturele ontdekking', 'verkenning',
            'achter de schermen', 'making of', 'creatief proces',
            'gemeenschap', 'ervaringsdeling', 'uitwisseling', 'discussie',
            'lifestyle content',
            # Expressions d'appartenance néerlandaises
            'onze gemeenschap', 'onze leden', 'familie', 'samen', 'laten we delen',
            'volg ons', 'abonneer je', 'blijf verbonden', 'volgende video',
            # Storytelling néerlandais
            'ons verhaal', 'zo werkt het', 'laat me vertellen', 'laten we samen ontdekken'
        ],
        'help': [
            # Patterns HELP néerlandais
            'veelvoorkomend probleem', 'frequente fout', 'ondervonden moeilijkheid', 'gemeenschappelijk probleem',
            'gedetailleerde oplossing', 'complete gids', 'stap-voor-stap tutorial', 'duidelijke uitleg',
            'probleemoplossing', 'technische probleemoplossing', 'technische hulp', 'klantenondersteuning',
            'veelgestelde vragen', 'FAQ', 'antwoorden op vragen', 'verduidelijkingen',
            'gebruikershandleiding', 'gedetailleerde instructies', 'complete procedure', 'handleiding',
            'praktische tips', 'nuttige tips', 'aanbevelingen',
            'systeemvereisten', 'vereisten', 'noodzakelijke voorwaarden', 'installatie',
            'probleemoplossing', 'diagnose', 'probleemidentificatie', 'analyse',
            'stap voor stap', 'geleidelijk', 'methodisch',
            'voor beginners', 'voor nieuwelingen', 'introductie', 'basiskennis',
            # Expressions pédagogiques néerlandaises
            'leer hoe', 'ontdek hoe', 'zo doe je het', 'ik laat je zien',
            'volg deze stappen', 'in deze video', 'je zult leren', 'eenvoudige uitleg',
            'snel oplossen', 'effectieve oplossing', 'bewezen methode', 'eenvoudige techniek'
        ]
    }
}

def add_description_patterns_to_db():
    """Ajouter les patterns enrichis de description à la base de données"""
    from yt_channel_analyzer.database import add_classification_pattern
    
    patterns_added = 0
    
    for language, categories in DESCRIPTION_PATTERNS.items():
        for category, patterns in categories.items():
            for pattern in patterns:
                if add_classification_pattern(category, pattern, language):
                    patterns_added += 1
                    print(f"[ENHANCED-PATTERNS] ✅ Ajouté: {pattern} → {category.upper()} ({language})")
    
    print(f"[ENHANCED-PATTERNS] 🎯 {patterns_added} patterns enrichis ajoutés pour mieux utiliser les descriptions")
    return patterns_added

# Indicateurs contextuels spécifiques aux descriptions
CONTEXT_INDICATORS = {
    'help': {
        'problem_solving': [
            'si vous rencontrez', 'en cas de problème', 'si ça ne marche pas',
            'problème résolu', 'solution trouvée', 'voici la solution',
            'if you encounter', 'in case of problem', 'if it doesn\'t work',
            'problem solved', 'solution found', 'here\'s the solution'
        ],
        'educational': [
            'vous allez apprendre', 'dans ce tutoriel', 'étape par étape',
            'explication détaillée', 'guide complet', 'formation',
            'you will learn', 'in this tutorial', 'step by step',
            'detailed explanation', 'complete guide', 'training'
        ]
    },
    'hero': {
        'promotional': [
            'nouveau produit', 'lancement', 'exclusivité', 'première',
            'découvrez notre', 'offre spéciale', 'édition limitée',
            'new product', 'launch', 'exclusive', 'first',
            'discover our', 'special offer', 'limited edition'
        ],
        'marketing': [
            'réservez maintenant', 'disponible dès', 'ne manquez pas',
            'expérience unique', 'moments magiques', 'souvenirs inoubliables',
            'book now', 'available from', 'don\'t miss',
            'unique experience', 'magical moments', 'unforgettable memories'
        ]
    },
    'hub': {
        'series': [
            'dans cette série', 'épisode', 'suite', 'prochain épisode',
            'collection', 'chaîne', 'programme régulier',
            'in this series', 'episode', 'next', 'next episode',
            'collection', 'channel', 'regular program'
        ],
        'community': [
            'notre communauté', 'partagez vos', 'dites-nous',
            'commentez', 'abonnez-vous', 'suivez-nous',
            'our community', 'share your', 'tell us',
            'comment', 'subscribe', 'follow us'
        ]
    }
}

def get_context_score(description: str, category: str, language: str = 'fr') -> float:
    """Calcule un score contextuel basé sur les indicateurs spécifiques"""
    if not description or category not in CONTEXT_INDICATORS:
        return 0.0
    
    description_lower = description.lower()
    score = 0.0
    
    for context_type, indicators in CONTEXT_INDICATORS[category].items():
        for indicator in indicators:
            if indicator in description_lower:
                # Poids plus élevé pour les indicateurs multilingues
                weight = 2.0 if any(lang in indicator for lang in ['fr', 'en']) else 1.5
                score += weight
    
    return score 