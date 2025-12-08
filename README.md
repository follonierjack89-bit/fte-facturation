# FTE Facturation

Application de facturation suisse avec QR-facture (Python + Tkinter + FPDF2).

## Architecture
```
/app
  /database   # Persistance SQLite (clients, articles, factures, paramètres)
  /logic      # Modèles métiers (Client, Item, Invoice, Settings)
  /pdf        # Génération des PDF avec FPDF2
  /qr         # Génération du payload Swiss QR Bill
  /ui         # Interface Tkinter (navigation, formulaires)
main.py       # Point d'entrée
```

SQLite est utilisé pour une persistance locale robuste sans dépendance serveur. Les paramètres (nom de l'entreprise, QR-IBAN, TVA, numérotation) sont stockés dans la table `settings` sous forme JSON.

## Fonctionnalités MVP
- Gestion des clients et des articles (saisie rapide, stockage SQLite).
- Création de factures avec lignes, calcul sous-total / TVA / total.
- Génération d'un PDF contenant la facture et la section QR-facture conforme à la structure SPC 0200.
- Paramétrage de l'entreprise (coordonnées, QR-IBAN, logo optionnel, TVA, numérotation).

## Utilisation
1. Installer les dépendances :
   ```bash
   pip install fpdf2
   ```
2. Lancer l'application :
   ```bash
   python main.py
   ```
3. Créer au moins un client puis saisir une facture. Le PDF est exporté dans le dossier `Factures/` avec un QR code bancaire prêt à être scanné.
