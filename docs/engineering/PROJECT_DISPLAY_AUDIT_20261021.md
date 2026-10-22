# Audit des affichages projet — 21 octobre 2026, soir

## Périmètre réel

Revue des données publiées des **174 fiches** du registre : 117 à Reem et 57 à Saadiyat, avec **527 lignes de typologies**, **214 équipements** et **31 références médias**. Les données proviennent de trente noms de sources ; les types publiés sont appartement, villa, penthouse, maison de ville et duplex. Aucun nom de projet, promoteur ou titre de média n'est vide dans cet inventaire. Aucun média n'a actuellement de publication intégrée approuvée ; les fichiers restent des références externes, avec photographie d'ambiance identifiée en repli.

La revue couvre l'annuaire paginé, le dossier détaillé et ses composants partagés, la couverture et le résumé cartographique. Les droits médias, localisations incertaines, précision des dates annoncées et champs commerciaux non renseignés restent qualifiés. L'analyse ne garantit pas l'exhaustivité des projets immobiliers ni la véracité commerciale des sources.

## Défauts confirmés et correction commune

Le filtrage précédent ne reconnaissait que le JSON. Les textes produits par certains extracteurs pouvaient prendre d'autres formes : liste Python chez Aldar, `bedrooms=…` chez Aldar et Property Finder, `Studio=8` dans un relevé ADREC, chemins `PSI public page:data[…]`. Ces notes techniques ne sont pas des citations rédigées par l'éditeur.

Les composants de source n'acceptent plus de prop contenant un extrait brut. Ils affichent uniquement le lien de source, sa date localisée et son éventuel caractère historique. Aucun volet technique ni chemin d'extraction n'appartient au parcours public des fiches. L'affichage ne dépend donc plus d'une liste de formats à reconnaître. Les extraits exacts, pointeurs, captures et horodatages restent dans PostgreSQL et dans le contrat API existant ; aucune preuve n'est supprimée ou réinterprétée.

Une source commune à plusieurs variantes d'une même typologie est affichée une seule fois par capture. Les différences de pointeur, chambre ou note n'ajoutent pas de ligne de source ; les captures, versions et sources distinctes restent séparées. Les boutons utilisent « Sources et dates » pour décrire précisément ce qu'ils ouvrent. Une date de source invalide ne peut plus provoquer une erreur de rendu du dossier.

Les codes des onze équipements actuellement publiés ont tous un libellé d'interface traduit. Les variantes de chambres affichées restent uniquement celles que les données structurées associent explicitement au type de bien ; aucune note technique n'est interprétée pour inventer une combinaison.

## Vérification reproductible

Le contrôle `scripts/smoke-projects.mjs` a été corrigé : son ancienne version supposait encore que la première page de l'annuaire contenait tous les projets et que toute fiche avait un lien cartographique. Il parcourt maintenant chaque page de 48 entrées, contrôle l'absence de doublon ou d'omission et exige une identité utilisable pour les liens de carte.

Il vérifie aussi chaque dossier compilé : identité, sections, langue/sens de lecture, quartier, médias et droits, textes d'équipements traduits, quantité de citations par capture et absence de notes/pointeurs techniques dans le document rendu, y compris les volets fermés. Les scripts de transport React sont exclus de l'analyse du texte affiché. Les requêtes sont bornées à trois lectures simultanées et trente secondes par lecture. Les tests ne déclenchent aucune collecte ni écriture métier.

Depuis la racine du dépôt, avec API et web compilé démarrés et données importées :

```powershell
$env:PROPERTY_PLATFORM_PROJECT_SMOKE_LOCALES = 'en,fr,ar'
node scripts/smoke-projects.mjs
```

Sans ce filtre facultatif, le contrôle parcourt les seize langues du registre. Les tests unitaires seuls ne valident pas le rendu réel d'une fiche.

## Propriété du code

`features/projects/evidence.tsx` possède les citations publiques et dépend uniquement de métadonnées typées et de présentation. `presentation.ts` possède le regroupement par provenance et le formatage sûr des dates ; aucun parseur de source ni interprétation de note n'y est introduit. Les appels du dossier et des médias transmettent seulement la source. `scripts/smoke-projects.mjs` possède le contrôle d'intégration opt-in de ce parcours ; il ne fait pas partie de l'acquisition Prefect. Aucun modèle, contrat, migration ou pipeline n'est modifié.

## Résultats de cette passe

- 88 tests web réussis ; Biome sur 160 fichiers, typage direct et compilation Docker réussis. Les contrôles standalone couvrent les seize langues.
- Exécution complète de la commande ci-dessus : **174 contrats projet**, **522 pages de dossiers** (174 dans chacune des trois langues), **12 pages d’annuaire** (4 dans chaque langue), erreurs 400/404 attendues. Aucun pointeur ou note technique trouvé dans le texte rendu, même pour les volets fermés ; nombre de citations et libellés d’équipements contrôlés sur chaque fiche.
- Vérification navigateur du projet des deux nouvelles captures, Grove Fountain Views : Studio/1/2 avec une citation Aldar ; salle de sport avec source PSI et date, sans texte d'extracteur. Les cinq volets de source ont été ouverts simultanément : cinq citations attendues et aucun bloc technique. Rendu mobile vérifié en français à 390 pixels et en arabe à 320 pixels, sans débordement horizontal ni erreur console observée.
- Version compilée installée dans l’aperçu privé existant. Aucun test backend/PostGIS ou ingestion relancé : cette passe n’en modifie ni les sources ni les contrats.

Ce contrôle exhaustif des réponses HTML ne remplace pas l'essai visuel de 174 cartes WebGL ou un test sur téléphone physique. Les essais navigateur visent des dossiers représentatifs, le contrôle automatisé couvre les fiches rendues de tous les projets. Les dates et chiffres affichés restent des déclarations sourcées ; aucune disponibilité commerciale ou conformité de livraison n'est déduite.
