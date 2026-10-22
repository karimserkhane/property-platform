# Données, pipelines et historique

Extension du 20 octobre 2026. Le site conserve ses observations métier typées et ses captures originales. Une source disparue ou une collecte partielle ne supprime pas automatiquement les données connues.

## Audit PostgreSQL

`evidence.row_revision` journalise chaque INSERT, UPDATE et DELETE des tables de `real_estate` et `evidence`, y compris SQL direct et opérations en lot. Il garde table, clé primaire réelle, avant/après, transaction, opérateur et clé d’exécution Prefect lorsqu’elle est connue. `recorded_at` vient de `clock_timestamp()` PostgreSQL, en UTC à la microseconde. Le journal est dans la même transaction que la mutation ; un rollback annule les deux.

La migration crée un inventaire `BASELINE` des lignes préexistantes. `known_ingested_at` reprend leur date d’ingestion/création si elle existe, sinon NULL. L’heure de l’inventaire n’est pas une ancienne ingestion. Les mutations antérieures à l’installation ne sont pas inventées.

Les octets ne sont pas dupliqués dans le JSON du journal : les originaux restent dans `Capture.payload` ou le stockage privé immuable, avec SHA-256 et liens `StoredObject`/`CaptureObject`. Le JSON avant/après est exclusivement technique ; il ne remplace pas les modèles métier.

Le journal refuse UPDATE/DELETE. Les opérations administrateur telles que TRUNCATE, restauration ou désactivation des triggers demandent une procédure de maintenance et une sauvegarde externe de PostgreSQL et du stockage privé. Les credentials/sessions Django et la base interne distincte de Prefect sont hors du journal immobilier.

Les colonnes binaires apparaissent dans le journal sous forme de SHA-256 calculé par PostgreSQL. Les captures originales refusent la suppression et le remplacement de leurs octets/empreintes ; déplacer des octets SQL vers le stockage privé exige une copie vérifiée de même empreinte et même taille.

## Reprise dans les lectures

| Données | Reprise |
| --- | --- |
| Projets | Dernière valeur non vide par page pour résumé, livraison, programme, typologies et équipements, même après de nombreuses collectes incomplètes de cette URL. Chaque valeur garde ses propres preuves et dates. |
| Contexte officiel | Dernière observation réussie par identifiant fournisseur et dataset ; enregistrement absent du dernier snapshot marqué historique. Les champs textuels vides peuvent reprendre leur valeur antérieure avec `field_history`. Les contrôles de chute de couverture restent actifs. |
| Carte/parcelles | Identités manquantes conservées ; reprise des champs de présentation vides depuis les observations/audits acceptés de la même identité fournisseur. Les géométries courantes et les valeurs nulles originales restent conservées. Aucun rétablissement d’identité inactive/remplacée. |
| Ventes ADREC | Snapshots consultables séparément par `snapshot_id`, avec fenêtres et effectifs exacts, depuis le sélecteur du Marché. Aucun cumul des fenêtres ni identité de transaction devinée. |
| Indices | Dernière valeur par série typée, avec période et provenance propres. Une série mise en quarantaine ne retrouve pas artificiellement un statut utilisable. |
| Médias | Originaux privés et droits/publication séparés ; la sélection historique ne rétablit pas un média bloqué dans une version plus récente. |

Une donnée historique garde son heure de récupération et d’ingestion d’origine ; elle n’est pas requalifiée comme fraîche. Les contrats exposent ces dates et marqueurs. Les libellés d’historique existent dans les seize langues.

`HistoryExclusion` enregistre un retrait confirmé avec capture, auteur, motif et révocation réversible. Un HTTP 404 ou une absence ne crée pas automatiquement un retrait. La commande `data_history exclude` accepte `context:<dataset>` + identifiant source, ou `project:<slug>` + URL. Une affirmation projet précise utilise `URL#handover`, `#total_units`, `#summary`, `#typologies` ou `#amenities`. `restore` conserve la décision initiale et documente sa révocation. Les options `--dataset`, `--key`, `--actor`, `--reason` sont obligatoires ; `exclude` exige aussi `--capture`.

## Fonds de carte

`BasemapRequest` conserve la file durable ; `BasemapTile` conserve chaque version avec licence, attribution, version fournisseur et capture des octets. Le TileJSON OpenFreeMap est capturé lui aussi. L’API enregistre les demandes manquantes sans contacter les fournisseurs. Prefect acquiert les tuiles ; la carte lit ensuite l’archive et attend au plus trois minutes une première acquisition. Le déplacement annule l’attente. Une collecte échouée conserve la dernière version utilisable du même fournisseur.

Reem et Saadiyat sont amorcées jusqu’au zoom natif 14 ; ailleurs, les tuiles sont demandées à la consultation. Les vérifications de nouvelles versions sont hebdomadaires. Aucun fond Esri n’est substitué à Sentinel absent.

Les composites ESA WorldCover 2020/2021 sont gratuits sous CC BY 4.0 ([licence](https://esa-worldcover.org/en/data-access)). Les [conditions OpenFreeMap](https://openfreemap.org/tos/) autorisent des zones de 3 000 tuiles ou 50 Mo maximum avec quatre requêtes simultanées et un User-Agent propre. Le collecteur est séquentiel et applique une borne cumulative conservatrice de 3 000 versions / 50 Mo. Au-delà, un accord fournisseur ou un hébergement propre est requis.

**Exception : Esri reste diffusé depuis son fournisseur ; ses droits de conservation permanente ne sont pas établis.** Cette exception figure dans le rapport d’inventaire. Les images d’ambiance, polices, traductions et styles restent des assets versionnés du logiciel. Les photos et documents immobiliers acquis utilisent déjà PostgreSQL et le stockage privé.

## Pipelines et installation

`evidence/pipeline_inventory.py` rattache chaque table à ses flows producteurs. Les tables partagées/jonctions appartiennent aux flows qui les alimentent ; les décisions humaines ont une vérification, sans décision de revue fabriquée par une collecte.

Le déploiement **data-history** contrôle tables, triggers actifs et couverture des pipelines, puis capture son rapport. Une table inconnue/non auditée fait échouer le contrôle. Les trois déploiements **basemap-openfreemap**, **basemap-sentinel-worldcover-2020**, **basemap-sentinel-worldcover-2021** traitent la file chaque minute. Les nouveaux calendriers démarrent désactivés ; ceux déjà configurés sont conservés au redémarrage.

Une nouvelle table doit ajouter son rattachement et appeler `evidence.install_row_journals(false)` dans sa migration explicite. Aucun DDL de démarrage.

Reconstruire API/ingestion, appliquer `python /workspace/apps/api/manage.py migrate --noinput`, redémarrer le runner, lancer **data-history** et les trois archives dans Prefect avant d’activer leurs calendriers, puis reconstruire le web. Aucun volume ne doit être supprimé. `python /workspace/apps/api/manage.py data_history report` affiche la couverture sans collecter de données.

**Installation locale vérifiée le 20 octobre :** 45 tables couvertes, 71 157 lignes inventoriées en `BASELINE`, quatre nouveaux calendriers activés. Les archives Reem/Saadiyat et une demande extérieure aux îles ont été acquises pour les trois fournisseurs ouverts puis relues par HTTP avec leurs dates d’ingestion. Le planificateur local nécessitait aussi la correction SQLAlchemy décrite dans [TOOLCHAIN.md](TOOLCHAIN.md) : les lancements manuels seuls ne validaient pas son fonctionnement. Les 35 déploiements préexistants et leurs réglages de calendrier ont été conservés.
