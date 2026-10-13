# Couverture nationale et activation des territoires

Décision du 12 octobre 2026 : **Property Platform vise les sept émirats. Al Reem est le premier jeu de données, pas une limite du produit.** L'accueil et la navigation sont nationaux ; les données actuellement collectées restent celles du pilote.

## Couverture actuelle

L'accueil propose Abu Dhabi, Dubai, Sharjah, Ajman, Umm Al Quwain, Ras Al Khaimah et Fujairah. Choisir Abu Dhabi ouvre actuellement Al Reem. Les autres émirats affichent une couverture en préparation : aucune parcelle, référence ou image satellite de Reem ne leur est attribuée. Un identifiant inconnu ne déclenche pas de remplacement silencieux.

La liste s'appuie sur [le portail du gouvernement des Émirats](https://u.ae/about-the-uae/the-seven-emirates). Les fenêtres de navigation sont **nos rectangles approximatifs**, pas des limites administratives officielles, cadastrales ou des preuves de couverture. Elles peuvent se chevaucher et inclure des territoires voisins. Les émirats ne se résument pas à leur ville principale : Ajman comprend aussi Masfout et Manama ([Department of Digital Ajman](https://media.ajman.ae/en/happiness-bundle/emirate-ajman/emirates-ajman)). Une collecte utilise les géométries et identités de ses sources validées.

La couverture détaillée de Reem reste décrite dans [REEM_MAP.md](REEM_MAP.md). Les photos d'accueil de Dubai et Abu Dhabi sont éditoriales ; elles ne prouvent pas l'existence de dossiers immobiliers dans ces villes.

## Où configurer la géographie

| Responsabilité | Fichier sur ton poste |
|---|---|
| Registre typé pays → émirat → zone, noms anglais/arabe et fenêtres de navigation | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\catalog\territories.py` |
| Profils activés : namespaces des sources, cadrage, références et identifiants satellite | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\modules\publication\coverage.py` |
| API locale `/api/v1/preview/territories` et paramètre `territory` des lectures | `C:\Users\Karim\Repositories\property-platform\apps\api\src\property_platform\api\parcels.py` |
| Snapshot public généré pour l'accueil statique et le futur mobile | `C:\Users\Karim\Repositories\property-platform\packages\contracts\territories.json` |
| Sélecteurs émirat/zone, historique et remise à zéro des données | `C:\Users\Karim\Repositories\property-platform\apps\web\src\features\atlas\territory-explorer.tsx` |
| Textes traduits et états de couverture | `C:\Users\Karim\Repositories\property-platform\apps\web\messages\<langue>.json`, namespace `Coverage` |

Le snapshot se régénère avec la commande d'export OpenAPI existante ; ne pas l'éditer à la main. Il contient la navigation et les profils configurés, **aucun nombre de parcelles figé**. L'accueil reste compilable sans base. L'API calcule les nombres actuels des namespaces activés ; ces comptes concernent les zones configurées, sans total national implicite. Un profil configuré peut avoir zéro parcelle avant import.

Une URL comme `/en/explore?territory=dubai` conserve la sélection au rechargement, au changement de langue et dans l'historique. Les zones non activées renvoient `409 territory_not_configured` aux lectures ; l'interface évite ces lectures et montre leur état de préparation. Les lectures sans paramètre restent génériques et bornées, utiles pour contrôler un autre fournisseur localement.

## Base et calculs géographiques

Les tables `real_estate.parcel`, `street`, `building`, `place` et `administrative_area` acceptent déjà des géométries WGS84, sans contrainte Reem. Les identités sont séparées par `source_namespace` et `source_record_id`. **Aucune nouvelle migration SQL ni réimport n'est nécessaire pour cette modification de navigation.** Les UUID, preuves, sources et audits sont conservés.

Le registre ne crée pas de lignes fictives dans `administrative_area`, qui conserve les objets géographiques des fournisseurs et leur provenance. Un rattachement administratif canonique demandera des territoires validés et datés, une migration additive et des rapprochements réversibles : un nom ou un rectangle qui se chevauche ne suffit pas.

Le catalogue ne filtre plus toutes les parcelles sur Onwani. Le profil sélectionné fournit les namespaces autorisés ; la fiche retrouve la provenance de sa propre identité. CSV et crédits de carte utilisent les vrais noms et URL des preuves.

Les surfaces utilisent `ST_Area(geometry::geography)` et les distances routières le sphéroïde WGS84, sans imposer UTM 40 à l'ouest du pays. Une présélection spatiale indexable précède le filtre exact de 120 m. Les contrôles PostGIS couvrent des points synthétiques à l'ouest, au centre et à l'est, dans une base isolée.

## Ajouter une deuxième zone, étape par étape

1. **Définir périmètre et sources.** Vérifier identifiants, géométries, couverture, dates, accès et droits. Un service d'Abu Dhabi n'est pas réputé couvrir Dubai ; une source publique n'accorde pas automatiquement un droit de redistribution.
2. **Créer son collecteur dans `evidence`.** Conserver captures, observations, mappings versionnés, quarantaine et audit. Les commandes `import_onwani` et `import_reem_*` gardent leur vrai périmètre ; changer leur nom ne les rendrait pas nationales.
3. **Documenter ses identités.** Choisir des namespaces stables par fournisseur/collection. Ne pas renommer les clés anciennes. Si plusieurs zones partagent un namespace, ajouter un filtre de couverture validé et des comptes spatiaux : le profil actuel ne doit pas compter toute la collection comme une seule zone.
4. **Adapter la projection.** Les attributs de permis Onwani sont spécifiques ; un autre fournisseur requiert un mapping explicite. Vérifier unités, devise, frais, autorités et règles locales. Déclarer et vérifier la catégorie de fiabilité du nouveau fournisseur plutôt que la déduire d'un nom commercial.
5. **Ajouter la zone au registre**, avec son émirat parent, puis son profil : sources autorisées, cadrage, références et scènes réellement acquises. L'inscription prépare la navigation ; l'activation requiert les contrôles précédents.
6. **Importer, contrôler et régénérer les contrats.** Suivre [le pipeline du guide](DEVELOPMENT.md#data-engineering). Vérifier doublons, géométries, provenance, filtres, dates et état vide. Reconstruire API et site pour actualiser la navigation compilée.
7. **Vérifier les parcours.** Carte/liste, lien direct, retour à Reem, historique, langues, mobile et RTL. Aucun résultat ou média d'une autre zone ne doit survivre au changement.

## Limites à traiter avant une couverture massive

Le prototype charge une petite zone en GeoJSON, avec un rectangle de requête maximal de 0,2° et 3 000 objets par couche. **Ce plafond protège le prototype ; envoyer toutes les parcelles du pays au navigateur serait inadapté.** Une nouvelle zone ne doit pas contourner cette limite.

À la montée en charge, prévoir des lectures par fenêtre visible, des tuiles vectorielles ou agrégats à faible zoom, une pagination stable de liste et une recherche nationale séparée. Conserver les index spatiaux et mesurer volumes, réseau, SQL et fraîcheur avant d'ajouter caches ou services. Secrets, droits et calendriers de collecte restent distincts par fournisseur.

Prix/unités, règles de frais par juridiction, scoring de fiabilité et traitements IA/media restent à développer. L'[orchestration Prefect](INGESTION.md) existe pour les sources du pilote Al Reem ; une autre zone demande ses connecteurs et contrôles avant activation. La provenance, l'identité durable, le coût et le contrôle suivent [REPOSITORY.md](REPOSITORY.md), [DATA_PROVENANCE.md](DATA_PROVENANCE.md) et la revue d'architecture. La couverture nationale ne justifie pas à elle seule un remplacement de stack ou des microservices.

## Validation de cette modification

123 tests backend ont réussi sur une base PostGIS isolée, dont la provenance d'un deuxième fournisseur synthétique, les mesures géodésiques et le refus de replier une zone inactive sur le pilote. 78 tests sans GIS ont ensuite réussi sur Windows ; ils ne remplacent pas PostGIS. Cinq tests web, types, Biome, Ruff, frontières de modules, contrats générés et liens documentaires ont été contrôlés.

La compilation du code actuel a réussi hors réseau dans l'environnement Linux déjà validé, avec les mêmes dépendances verrouillées. L'artefact autonome passe les contrôles des quinze langues. Le navigateur a validé le parcours Reem → Sharjah → retour, l'état de préparation de Dubai, l'historique, la conservation du territoire au changement de langue et le RTL sur mobile de 390 pixels, sans débordement. Le nettoyage des contrôles MapLibre au changement de zone a été corrigé pendant cette vérification.

La prévisualisation locale fonctionne sur `http://localhost:3102/en`. Le disque plein a nécessité un redémarrage normal de Docker, puis une reprise des images applicatives locales depuis les environnements sains ; les volumes, captures et sauvegardes ont été conservés. La base retrouve 2 431 parcelles, 665 rues et 188 bâtiments. **Une reconstruction depuis zéro reste bloquée sur ce poste par `UnknownIssuer` vers PyPI et npm**, et le build Windows par les permissions du cache natif SWC. Aucun contrôle de certificat ou de cache n'a été désactivé. Ces incidents locaux ne sont pas une validation du déploiement ni de la chaîne de certificats pour un nouvel environnement.

Pour reprendre la prévisualisation sur ce poste avec ses images actuelles, depuis `C:\Users\Karim\Repositories\property-platform` :

```powershell
docker compose -f infra/local/compose.yaml --profile web-preview up -d --no-build
```

Cette commande démarre les images déjà présentes ; elle ne compile pas les modifications suivantes. Pour reconstruire normalement après correction des certificats de l'environnement, utiliser les commandes de [DEVELOPMENT.md](DEVELOPMENT.md). Ne pas ajouter de désactivation TLS pour contourner `UnknownIssuer`.
