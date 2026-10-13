# ADREC : collecte publique et données de marché

Cette intégration ajoute les ventes récentes publiées par ADREC pour Al Reem et Saadiyat, ainsi que les séries d’indices résidentiels. Elle complète les parcelles Onwani et les bâtiments OSM ; elle ne remplace pas ces données géographiques. L’onglet **Market** de la carte lit PostgreSQL, sans contacter ADREC lors des clics des visiteurs.

## Ce qui a été examiné

| Source officielle | Informations utiles | Traitement actuel |
|---|---|---|
| [Market Data](https://adrec.gov.ae/en/market-data) | Ventes récentes, prix, surfaces, typologies, indices | Trois déploiements Prefect décrits ci-dessous |
| [Market Reports](https://adrec.gov.ae/en/market_reports) | Rapports 2024, H1 2025, 2025 et H1 2026 | Référencés ici ; chiffres PDF non extraits automatiquement |
| [Carte interactive](https://adrec.gov.ae/en/property_and_index/interactive-map) | Carte et informations immobilières | Source examinée ; aucun rapprochement automatique avec nos bâtiments |
| [API Subscription](https://adrec.gov.ae/en/apisubscription) | Demande d’accès aux services API | Aucun compte, abonnement ni demande commerciale créés |

Les URLs JSON ont été observées dans les scripts du tableau de bord public, sans authentification ni clé. Ce sont des interfaces du site, pas un contrat d’API garanti : le connecteur échoue explicitement si leur structure change. L’accès public n’établit pas à lui seul une licence de redistribution commerciale. Avant publication en production, confirmer les droits et les conditions d’usage auprès d’ADREC ; la collecte et la prévisualisation locales sont déjà implémentées.

## Les trois imports

| Déploiement Prefect | Source et portée | Horaire prévu, Asia/Dubai |
|---|---|---|
| `property-platform-adrec-sales/adrec-reem-sales` | `RecentSales`, district exact `Al Reem Island` | Dimanche 09:00 |
| `property-platform-adrec-sales/adrec-saadiyat-sales` | `RecentSales`, district exact `Al Saadiyat Island` | Dimanche 09:30 |
| `property-platform-adrec-indices/adrec-price-indices` | `ResiSalePriceIndexByArea` et `ResiRentPriceIndexByArea` | Dimanche 10:00 |

Les endpoints sont sous `https://adrec.gov.ae/api/feature/MarketData/`. Les imports de ventes couvrent **90 jours calendaires complets**, jusqu’à la veille à Dubai. L’heure planifiée du flow fixe cette fenêtre pour ses reprises. Les filtres non géographiques restent `all`, la langue source `en`, chaque réponse contient au maximum 1 000 lignes. La fenêtre est divisée en trois intervalles disjoints de 30 jours ; un intervalle trop volumineux est subdivisé par jour. Aucune page à offset n’est utilisée pour matérialiser les ventes. Une journée dépassant la capacité d’une réponse complète provoque un échec explicite. Chaque collecte est bornée à 10 000 ventes et 64 Mio au total ; elle n’extrait pas silencieusement une partie d’un territoire plus volumineux.

Sur une nouvelle installation, les horaires commencent désactivés, comme les autres nouveaux déploiements. Sur le poste de Karim, leur activation intervient après la première collecte vérifiée. Redémarrer le runner conserve les horaires et leur activation modifiés dans l’interface Prefect. Docker et le runner doivent fonctionner pour exécuter le calendrier local ; cela ne crée pas un service cloud permanent.

## Où se trouve le code ?

Ajouter le préfixe `C:\Users\Karim\Repositories\property-platform\` aux chemins relatifs donne les fichiers suivants :

| Fichier complet | Rôle |
|---|---|
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\registry.py` | Déploiements, paramètres et calendrier |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\flows.py` | Flows Prefect et identité durable de l’exécution |
| `C:\Users\Karim\Repositories\property-platform\apps\ingestion\src\property_platform_ingestion\collectors\adrec.py` | Acquisition HTTPS bornée, avant transaction SQL |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\adrec.py` | Schéma source, filtres autorisés, pagination et nettoyage typé |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\adrec_import.py` | Conservation des captures puis écriture des observations avec Django |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\models.py` | Modèles SQL des snapshots, ventes et indices |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\evidence\migrations\0014_adrec_market_snapshots.py` | Création des nouvelles tables dans le schéma `evidence` |
| `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\adrec_preview.py` | Lecture du dernier snapshot complet pour l’interface |
| `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\adrec-market.tsx` | Onglet Market et pagination côté site |

Prefect programme et supervise. Le collecteur télécharge des réponses publiques avec vérification TLS, cadence, URLs autorisées et limites de taille. Le code métier Django valide ces réponses puis écrit dans PostgreSQL. Le site ne possède pas les identifiants de la base et ne déclenche aucun import.

## Tables et provenance

| Table dans la base `property_platform` | Contenu |
|---|---|
| `evidence.adrec_market_snapshot` | Une collecte complète, territoire, fenêtre, nombre de lignes et lien vers son exécution |
| `evidence.adrec_sale_observation` | Nom de projet fourni, date de vente, district/communauté, type, typologie, prix AED, surfaces, prix/m² fourni, part vendue, primaire/secondaire et off-plan |
| `evidence.adrec_index_observation` | Série vente/location, commune, catégorie de zone, type, période, valeur, état exploitable et raison de revue |
| `evidence.capture` | Réponse HTTP exacte, URL avec filtres, statut, hash, heures de début/fin de collecte et ingestion |
| `evidence.ingestion_run` | Source, opérateur, version du connecteur, bilan et état de l’import |
| `evidence.ingestion_execution` | Identité du flow, reprises et résultat durable de l’opération |

Chaque observation référence sa capture et le chemin de sa ligne dans le JSON, par exemple `content[12]`. Les prix utilisent `Decimal` en Python et `numeric` dans PostgreSQL ; l’API les transmet sous forme de chaînes pour éviter les arrondis binaires. La date de vente provient de `sale_application_datetime` : elle ne représente pas l’heure de publication de la page. Une date de publication inconnue reste `NULL`, sans être remplacée par l’heure de collecte.

Les réponses de ventes examinées ne contiennent **ni identifiant de transaction ni identifiant d’unité**. On conserve donc les lignes, même identiques, dans des snapshots séparés. Leur hash vérifie l’observation ; il ne devient pas un faux identifiant de vente. L’interface ne somme pas les snapshots qui se recouvrent. Aucun `TRUNCATE` n’efface l’historique. Un projet nommé par ADREC n’est pas associé automatiquement à un bâtiment ou une parcelle sur son seul nom.

Chaque intervalle complet est lu deux fois ; la comparaison vérifie les lignes et leur multiplicité, tout en acceptant un ordre différent. Cette règle évite les pertes liées à la pagination ADREC, dont l’ordre entre ventes datées du même jour s’est révélé instable pendant les essais réels. Les captures de découverte trop volumineuses et les captures de vérification restent conservées, sans être comptées comme ventes supplémentaires. Une modification détectée ou une réponse partielle fait échouer la collecte ; le précédent snapshot exploitable reste consultable. L’interface choisit d’abord la fenêtre terminant le plus récemment, puis sa collecte la plus récente : reprendre un ancien flow ne fait pas revenir le marché à une ancienne période. L’absence de jeton de version fournisseur ne permet toujours pas de garantir une lecture atomique entre plusieurs intervalles.


### Indices locatifs sous revue

Lors de l’examen du 13 octobre 2026, la réponse locative contient 1 440 lignes pour 720 combinaisons de dimensions. **711 combinaisons ont des valeurs différentes malgré des dimensions identiques.** Il manque une dimension ou une explication permettant de distinguer ces séries. Le pipeline conserve toute la réponse, marque la série concernée non exploitable et retourne `quarantined` avec un avertissement visible dans Prefect. Les indices de vente valides restent utilisables. L’interface ne choisit ni une moyenne ni une valeur arbitraire parmi les indices locatifs contradictoires.

Les indices montrés concernent **Abu Dhabi City**, toutes zones confondues, et non une île ou un bâtiment particulier. Les autres catégories de zone restent dans les tables. Ces indices ne constituent pas une estimation du prix d’un bien. Les ventes sont des événements passés, pas des annonces disponibles ou des offres de promoteur.

## Relancer une collecte

1. Ouvrir [Prefect local](http://localhost:4200), puis **Deployments**.
2. Sélectionner le déploiement Reem, Saadiyat ou indices dans le tableau ci-dessus.
3. Cliquer **Run**, conserver le territoire enregistré et renseigner `actor` avec son nom si souhaité.
4. Attendre la fin du flow ; consulter son bilan et ses avertissements. Les indices sous revue produisent volontairement un avertissement, pas une série arbitrairement corrigée.
5. Ouvrir [la carte locale](http://localhost:3102/en/explore), choisir la zone et cliquer **Market**.

`migrate` crée ou modifie les tables ; il ne télécharge rien. Recompiler le site ne collecte rien non plus. C’est l’exécution du flow qui acquiert et enregistre les nouvelles observations. Sur une autre installation, reconstruire API/ingestion puis appliquer `migrate --noinput` avant de démarrer le nouveau runner, suivant [INGESTION.md](INGESTION.md).

Pour consulter les données dans l’outil SQL connecté à la base `property_platform` :

```sql
SELECT territory, dataset, period_start, period_end, source_row_count, created_at
FROM evidence.adrec_market_snapshot
ORDER BY created_at DESC;

SELECT project_name, registration_date, price_aed, sold_area_sqm, sold_share
FROM evidence.adrec_sale_observation
WHERE snapshot_id = '<UUID du snapshot choisi>'
ORDER BY registration_date DESC, source_position;
```

Ne pas additionner toutes les lignes historiques pour annoncer un nombre de transactions uniques. Pour l’interface actuelle, l’API `GET /api/v1/preview/adrec-market?territory=saadiyat-island` choisit le snapshot exploitable et limite la réponse à 40 ventes par page, avec recherche par projet.


## Résultats vérifiés sur ce poste — 13 octobre 2026

La migration `evidence.0014` est appliquée à la vraie base locale. Les trois nouvelles tables sont bien dans `evidence` ; les tables Onwani/OSM et les volumes existants sont conservés. Les derniers snapshots contiennent **1 422 ventes Reem et 526 ventes Saadiyat**, du **15 juillet au 12 octobre 2026**, ainsi que **560 observations d’indices de vente exploitables et 1 440 observations locatives sous revue**. Ce sont les effectifs des snapshots, pas un registre dédupliqué de transactions uniques.

Les trois déploiements ADREC ont terminé leurs premiers imports. Les calendriers sont activés aux heures indiquées plus haut ; Prefect affiche maintenant **20 déploiements et 17 calendriers actifs**. La prévisualisation Docker sur **3102** montre les prix et permet la recherche par projet : The Arthouse retourne dix lignes de ventes dans la fenêtre importée, dont une à **3 900 000 AED**, **93,27 m²**, datée du **12 octobre**. Le rapprochement physique avec un bâtiment reste à valider séparément.

Contrôles : **213 tests backend sur PostGIS**, **80 tests ingestion Windows** (un contrôle de lien symbolique réservé à Linux est ignoré), **21 tests web**, compilation Linux Node 26 et TypeScript, routes HTTP des quinze langues, interface anglaise et arabe/RTL, deux contrats de dépendance, contrat OpenAPI/types générés et liens de documentation. Le contrôle TypeScript natif Windows est bloqué par la vérification du cache SWC ; la compilation Linux effectue ce contrôle avec succès, sans désactiver les protections du cache natif. Ces résultats sont locaux ; ils ne constituent pas une exécution CI GitHub déjà réussie.

Une capture locale de la vérification est conservée sous `C:\Users\Karim\Repositories\property-platform\.cache\validation\adrec-market-saadiyat.png`, hors Git. Les réponses sources exactes sont dans la base et ne sont pas commitées dans le dépôt.
