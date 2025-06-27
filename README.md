# YouTube Channel Analyzer

Ce projet fournit un petit dashboard pour analyser des chaînes YouTube publiques. 
Il est possible d'ajouter des concurrents à analyser et de filtrer les résultats 
par dates de début et de fin. Pour chaque concurrent, la matrice **Hero/Hub/Help**
est affichée avec le nombre de vidéos et le total de vues par thématique.

Le projet est modulaire afin de pouvoir évoluer facilement.

## Installation

```bash
pip install flask
```

## Utilisation

```bash
python app.py
```

Le dashboard sera disponible sur `http://localhost:5000`. Vous pouvez choisir des dates
de début et de fin pour filtrer l'analyse.

## Tests

```bash
pytest
```
