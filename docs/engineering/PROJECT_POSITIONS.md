# Qualité des positions de projet (A02, 23 octobre 2026)

Un point publié par une agence n'est pas une emprise cadastrale. Chaque position renvoyée dans `map_locations` (fiche projet et résumé de carte) dit désormais **comment** elle a été obtenue et **quelle précision** elle a. Rien n'est stocké en plus : la méthode se déduit du lien d'identité relu et de l'observation qui a créé le point. Elle se reconstruit donc depuis les pipelines Prefect, comme le reste.

## Méthodes

| `method` | Origine | `precision` | Affichage |
| --- | --- | --- | --- |
| `cadastral_parcel` | Lien relu vers une parcelle cadastrale | `boundary` | « Position : limite de la parcelle cadastrale. » |
| `building_footprint` | Lien relu vers une emprise de bâtiment | `footprint` | « Position : emprise du bâtiment vérifiée. » |
| `authority_point` | Coordonnées enregistrées auprès de l'autorité (ADREC) | `point` | approximative, pas la limite de la parcelle |
| `publisher_point` | Point de la carte du promoteur ou de l'éditeur | `point` | approximative, non vérifiée |
| `broker_point` | Coordonnées publiées par une agence (PSI, Property Finder) | `point` | approximative, non vérifiée |
| `declared_point` | Point d'une autre source déclarée (méthode inconnue) | `point` | approximative, non vérifiée |

La fiche, la carte de quartier et le résumé de l'explorateur affichent la meilleure méthode disponible, dans l'ordre du tableau. Un point ne se présente jamais comme une parcelle. Sans position documentée, le message existant (« position exacte en attente de vérification ») reste affiché ; aucune position n'est inventée (ni centre d'île, ni rapprochement par le nom).

Code : `location_method` et `LOCATION_PRECISION` dans `apps/api/src/property_platform/modules/evidence/project_queries.py` ; `projectPositionQuality` dans `apps/web/src/features/projects/presentation.ts`.

## Fiches sans position, par priorité

```bash
docker compose -f infra/local/compose.yaml exec api python manage.py project_location_gaps [--territory al-reem-island]
```

La commande liste les fiches publiées sans position visible, une ligne JSON par fiche :

1. **Priorité 1** : un parent ou un composant (voir [la hiérarchie des projets](PROJECT_HIERARCHY.md)) est déjà localisé ; une relecture peut suffire.
2. **Priorité 2** : une page du promoteur ou de l'autorité est publiée ; c'est la source habituelle d'un plan de masse ou d'un numéro de parcelle.
3. **Priorité 3** : seulement des pages d'agence ou de presse ; il faut une nouvelle preuve.

État au 23 octobre 2026 : 140 fiches localisées sur 183, 43 sans position.

- **Priorité 1 (6)** : Gate, Gate ARC, Maysan, Radisson Residences Tower 3, Tara Park 2, The Row Saadiyat Phase 2.
- **Priorité 2 (24)** : Al Maryah Vista 1, One&Only Private Residences, Rosewood Residences, Ritz-Carlton Residences, St. Regis Residences (Al Maryah) ; Bab Al Qasr Residence 77, Canal Residence, Leaf Tower, Marafid, Marlin 1, Radiant Atrium, Radiant Elite, Radiant Square, Radiant Terrace, Reem Eleven, Reem Five, Rixos Al Reem, Seamont, The Artery (Reem) ; Baccarat Residences, Faya Al Saadiyat I et II, Four Seasons Private Residences, Talay Marsa (Saadiyat).
- **Priorité 3 (13)** : JOUD Residence, Marlin Icon, Missoni Residences, One Residence, Parkside Residence B, Reem Diamond, Rotana Residences (programme, tours nord et sud), Sea View Tower, Seamont Phase 2, Global Gate, Talay Beach.

Une position s'ajoute toujours par une source collectée (pipeline) ou un lien relu dans `project_registry.json`, jamais par une saisie directe en base.
