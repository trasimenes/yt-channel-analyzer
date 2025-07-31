-- Corrections des données après les améliorations du workflow
-- Ce fichier peut être exécuté pour corriger les données existantes

-- 1. Classer Disneyland Paris comme concurrent français
UPDATE concurrent 
SET country = 'France' 
WHERE name = 'Disneyland Paris' AND (country IS NULL OR country = '');

-- 2. Vérification des résultats
SELECT 'Disneyland Paris country:' as check_type, country 
FROM concurrent 
WHERE name = 'Disneyland Paris';

-- 3. Statistiques par pays après correction
SELECT 
    country,
    COUNT(*) as competitors,
    SUM((SELECT COUNT(*) FROM video WHERE concurrent_id = c.id)) as total_videos
FROM concurrent c 
GROUP BY country 
ORDER BY total_videos DESC;