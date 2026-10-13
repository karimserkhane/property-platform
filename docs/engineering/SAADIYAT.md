# Saadiyat Island : deuxième territoire actif

Extension du 13 octobre 2026. Saadiyat rejoint Al Reem dans la même base et les mêmes services. Le sélecteur **Area → Saadiyat Island** ouvre ses données ; le lien direct est [la carte Saadiyat](http://localhost:3102/en/explore?territory=saadiyat-island). Le port 3000 sert le développement Next.js ; 3102 sert la prévisualisation Docker compilée.

## Sources et périmètre

Le service public [DMT / Onwani](https://onwani.abudhabi.ae/arcgis/rest/services/MyLand/SMARTHUB/MapServer) déclare **AL SAADIYAT ISLAND**, district **1347**. Les requêtes utilisent ces valeurs vérifiées. La géométrie officielle s'étend approximativement de 54.386023 à 54.481150° E et de 24.488691 à 24.601854° N ; les rectangles de navigation arrondis restent des cadrages, pas des preuves cadastrales.

| Données initiales | Résultat contrôlé |
|---|---|
| Parcelles Onwani | 5 499 observées, 5 498 géométries valides enregistrées, une observation en quarantaine |
| District officiel | 1 |
| Communautés/secteurs officiels | 16 |
| Rues nommées Onwani | 7 ; cela ne représente pas toutes les routes de l'île |
| Bâtiments OSM | 1 185 |
| Lieux OSM nommés | 202 |
| Rues OSM | 287 ; 294 avec les 7 rues Onwani, sans fusion supposée |
| Observations OSM en quarantaine | 26 |
| Présentations immobilières examinées | 3 bâtiments Park View, Bloom Holding ; aucune photo ajoutée |
| Références immobilières | 8 URL examinées, issues d'Aldar, Bloom Holding et de l'Abu Dhabi Media Office |

Les références comprennent Sei Saadiyat, Grove Museum Views, Mamsha Al Saadiyat, Mamsha Gardens, Saadiyat Grove et Marsa Al Saadiyat. Une référence décrit une page capturée et son état HTTP ; elle n'est pas une unité disponible, un prix validé, une preuve d'appartenance à une parcelle ou une licence pour copier ses photographies. Trois présentations Park View sont rattachées à des identités OSM examinées ; leur page officielle Bloom décrit le projet et son promoteur. Le registre de médias reste vide faute de photographie au droit de réutilisation examiné. Cela ne constitue pas une vérification d'inventaire ni une fusion des trois bâtiments.

## Parcours des données

1. Le flow Prefect reçoit `territory=saadiyat-island`, choisit une configuration examinée et acquiert les réponses HTTPS avec des limites de taille et de durée.
2. Les réponses sont préparées avant la transaction d'écriture ; leurs octets, URL, statut HTTP, hash et dates de collecte sont conservés.
3. Django vérifie protocole, couverture complète, identités et géométries. Une géométrie invalide est conservée en quarantaine, sans réparation inventée.
4. Les services propriétaires mettent à jour les tables du schéma `real_estate`. Les observations et audits restent dans `evidence`.
5. Le site lit cette base. Changer de territoire ne déclenche aucun scraping distant.

Les identités `dmt:onwani:smarthub:plot:adm:saadiyat`, `dmt:onwani:saadiyat:<couche>` et `osm:saadiyat:osm` sont distinctes de celles de Reem. Un même `OBJECTID` fourni dans deux collections ne peut pas écraser le bien de l'autre territoire. Les contrôles de rapprochement réversible s'appliquent aussi lors d'un renouvellement d'identifiant fournisseur.

**Pas de truncate.** Les objets déjà identifiés sont conservés ou actualisés ; les captures, observations, exécutions et décisions restent historiques. L'absence d'un bâtiment dans une collecte n'est pas une preuve de démolition. Une nouvelle migration ne recollecte pas les données.

## Import OpenStreetMap initial

Les services Overpass ont retourné HTTP 406 ou n'ont pas répondu pendant la vérification locale. Le flow hebdomadaire expose son échec et conserve les données précédentes. L'[API de lecture OSM](https://wiki.openstreetmap.org/wiki/API_v0.6) permet un import initial manuel sur quatre fenêtres enregistrées. Une requête sur toute l'île a dépassé sa limite de 50 000 nœuds ; les quatre fenêtres restent bornées à 16 Mio chacune et 64 Mio au total.

Le déploiement **saadiyat-osm-bootstrap** conserve les **XML originaux**. Le parseur reconstitue les chemins uniquement à partir des coordonnées réellement reçues. Les doublons de fenêtre sont réunis seulement si identité, version, attributs et géométrie concordent ; une divergence bloque le lot. Les relations incomplètes restent en quarantaine, sans centre inventé. Les objets sont filtrés par la vraie géométrie officielle du district.

Cette opération n'a **aucun calendrier**. L'API d'édition OSM n'est pas utilisée comme service de téléchargement national ou comme solution hebdomadaire. Une couverture massive nécessite un extracteur régional isolé ou un fournisseur Overpass adapté ; les [instances publiques](https://wiki.openstreetmap.org/wiki/Overpass_API#Public_Overpass_API_instances) ont leurs politiques d'usage.

## Fichiers sur le poste

| Responsabilité | Chemin complet |
|---|---|
| Filtres et fenêtres d'acquisition par territoire | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\collection_profiles.py` |
| Protocole XML portable et fenêtres autorisées | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\osm_api_protocol.py` |
| Import OSM initial, captures et écriture auditée | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\osm_bootstrap.py` |
| Références publiques de Saadiyat | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\saadiyat_project_sources.json` |
| Flows Prefect | `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\flows.py` |
| Déploiements et horaires | `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\registry.py` |
| Territoires et cadrages publiés | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\coverage.py` |

La migration **evidence.0013_osm_bootstrap_execution** élargit la contrainte des opérations autorisées dans `evidence.ingestion_execution`. Elle ne crée pas un nouveau schéma immobilier, ne renomme aucune table et ne supprime aucune ligne.

## Lancer sur une autre installation

Ouvrir **Terminal dans PyCharm → PowerShell**, depuis la racine du dépôt :

```powershell
Set-Location C:\Users\Karim\Repositories\property-platform
docker compose -f infra/local/compose.yaml up -d --build api
docker compose -f infra/local/compose.yaml exec api python manage.py migrate --noinput
docker compose -f infra/local/compose.yaml -f infra/local/compose.ingestion.yaml --profile ingestion up -d --build ingestion
```

La première commande charge le code API, la deuxième applique les migrations, la troisième charge les flows du runner. Pour les certificats particuliers de ce poste et la prévisualisation compilée, suivre [INGESTION.md](INGESTION.md) et [DEVELOPMENT.md](DEVELOPMENT.md).

Dans [Prefect](http://localhost:4200), ouvrir **Deployments** puis lancer une fois, dans cet ordre : **saadiyat-map-district → saadiyat-map-community → saadiyat-map-street → saadiyat-parcels-onwani → saadiyat-osm-bootstrap → saadiyat-project-references → saadiyat-property-presentations**. Attendre le résultat de chaque exécution. L'import OSM a besoin de la géométrie du district pour exclure les objets extérieurs.

Pour les collectes officielles seulement, les commandes Django gardent leur compatibilité avec Reem et acceptent désormais le territoire :

```powershell
docker compose -f infra/local/compose.yaml exec api python manage.py import_onwani --territory saadiyat-island --actor Karim
docker compose -f infra/local/compose.yaml exec api python manage.py import_reem_map --territory saadiyat-island --layer district --actor Karim
```

La deuxième commande conserve son ancien nom pour ne pas casser les scripts ; `--territory` choisit réellement les requêtes, identités et validations. Préférer Prefect pour le journal opérationnel et les horaires.

## Lecture de la carte et limites

L'API conserve sa limite de 3 000 parcelles par réponse et ajoute un curseur UUID stable. Le site utilise des pages de 1 000, déduplique les identifiants et garde une limite totale de 12 000 objets / 12 pages. Une erreur de page ne produit pas silencieusement un résultat partiel. Cela couvre le volume mesuré de Saadiyat ; une carte nationale nécessitera des lectures par fenêtre ou des tuiles vectorielles.

Les couches carte et leurs rattachements aux parcelles utilisent les namespaces du territoire sélectionné, même lorsque les rectangles des deux îles se chevauchent. Les références et scènes de Reem ne sont pas proposées à Saadiyat. Les champs non disponibles restent absents : pas de photographie de promoteur copiée sans droit, de stock commercial supposé ou de scène Sentinel de Reem utilisée pour Saadiyat.


## Vérifications de la livraison

Sur PostGIS réel, 198 tests de la suite backend et un contrôle supplémentaire du retraitement des références par territoire ont réussi. Les 77 tests portables d'ingestion passent ; un test de symlink est ignoré sur Windows. Les 21 tests web, les types et contrats générés, Ruff, Biome, les frontières des modules et les liens documentaires ont été contrôlés. Le build Next.js et le test de l'artefact autonome réussissent dans les quinze langues.

Les lectures Django sur la base locale ont vérifié les 5 498 parcelles Saadiyat sur six pages sans doublon, les 1 185 bâtiments, 202 lieux, 294 rues, 17 aires administratives, huit références accessibles et trois présentations Park View. Reem conserve 2 431 parcelles, 188 bâtiments et 665 rues. Saadiyat ne reçoit aucune des scènes Sentinel de Reem.

La migration evidence.0013 est appliquée. Après redémarrage du runner, les 17 déploiements et les 14 calendriers actifs du dimanche sont conservés ; les trois autres déploiements n'ont aucun calendrier. Le contrôle visuel dans le navigateur reste à effectuer : la revue automatique a bloqué l'ouverture locale après une interruption de quota. Ces contrôles techniques ne constituent pas une validation visuelle.
