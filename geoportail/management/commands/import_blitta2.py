"""
Reconstruit les couches du géoportail pour la commune de Blitta 2 à partir de
données ouvertes, quand on ne dispose pas de la base d'origine.

Sources :
- limites des cantons : OCHA COD-AB Togo (HDX, niveau ADM3) ;
- composition de la commune : décret publié au JO du 08/01/2018
  (Blitta 2 = Agbandi, Langabou, Koffiti, Tcharè-Baou) ;
- infrastructures : OpenStreetMap via Overpass (© contributeurs OSM, ODbL) ;
- formations sanitaires publiques : inventaire OMS/KEMRI (HDX, Maina et al. 2019).

Usage :
    python manage.py import_blitta2
    python manage.py import_blitta2 --cache-dir data_cache --refresh

Les tables des couches (modèles non gérés) sont créées si elles n'existent
pas, puis vidées et rechargées : la commande peut être relancée sans risque.
ATTENTION : elle écrase le contenu actuel des couches du géoportail.
"""
import io
import json
import os
import re
import tempfile
import time
import zipfile

import requests
from django.apps import apps
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

NR = "Non renseigné"
USER_AGENT = "projet-horieon-import/1.0"
HDX_API = "https://data.humdata.org/api/3/action/package_show?id={}"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
CANTONS = {  # P-code COD-AB -> nom officiel (décret)
    "TG010101": "Agbandi",
    "TG010110": "Langabou",
    "TG010109": "Koffiti",
    "TG010115": "Tcharè-Baou",
}
POINT_TABLES = ["marches", "jardb2", "collegeb2", "lyc2", "pea", "bornefontaines", "chatea", "formation_s",
                "cooperativebl2", "magazin_intrantbl2"]
LOCALI_TABLES = [t for t in POINT_TABLES + ["stade_terrainbl2"] if t not in ("bornefontaines", "magazin_intrantbl2")]
POINT_SQL = "ST_PointOnSurface(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))"


def sql(query, params=None):
    with connection.cursor() as cur:
        cur.execute(query, params or [])
        if cur.description:
            return cur.fetchall()
    return None


def name_of(tags, default):
    return (tags.get("name") or tags.get("name:fr") or tags.get("official_name") or default).strip()[:100]


def health_type(name):
    """Type de formation sanitaire déduit de la nomenclature togolaise."""
    n = name.lower()
    if re.search(r"\busp\b|unit[ée] de soins p[ée]riph", n):
        return "Unité de soins périphérique (USP)"
    if re.search(r"\bcms\b|m[ée]dico[- ]?social", n):
        return "Centre médico-social (CMS)"
    if re.search(r"\bchp\b|\bchr\b|h[ôo]pital", n):
        return "Hôpital"
    if re.search(r"centre de sant[ée]", n):
        return "Centre de santé"
    if re.search(r"dispensaire", n):
        return "Dispensaire"
    return None


def classify_school(tags):
    name = (tags.get("name") or "").lower()
    if tags.get("amenity") == "kindergarten" or re.search(r"jardin|maternelle|\bepe\b", name):
        return "jardin"
    if re.search(r"lyc[ée]e|\blt\b|\bltp\b", name) or tags.get("isced:level") in ("3", "4"):
        return "lycee"
    if re.search(r"\bceg\b|coll[èe]ge|\bces\b|\bcet\b", name) or tags.get("isced:level") == "2":
        return "college"
    return None  # école primaire : pas de couche dans le géoportail


def statut(tags, name):
    op = (tags.get("operator:type") or "").lower()
    if op in ("public", "government"):
        return "Public"
    if op in ("private", "private_non_profit"):
        return "Privé"
    if op == "religious":
        return "Confessionnel"
    if op == "community":
        return "Communautaire"
    n = name.lower()
    if re.search(r"\b(epp|ceg|lyc[ée]e|usp|cms|chp|chr)\b", n):
        return "Public"
    if re.search(r"catholique|protestant|islamique|evang|\becc\b|\bepc\b", n):
        return "Confessionnel"
    if re.search(r"priv[ée]", n):
        return "Privé"
    return NR


def osm_geometry(el):
    """Géométrie GeoJSON d'un élément Overpass (« out geom »)."""
    if el["type"] == "node":
        return {"type": "Point", "coordinates": [el["lon"], el["lat"]]}
    if el["type"] == "way" and el.get("geometry"):
        coords = [[p["lon"], p["lat"]] for p in el["geometry"]]
        if len(coords) >= 4 and coords[0] == coords[-1]:
            return {"type": "Polygon", "coordinates": [coords]}
        return {"type": "LineString", "coordinates": coords}
    if el["type"] == "relation" and el.get("members"):
        lines = [[[p["lon"], p["lat"]] for p in m["geometry"]] for m in el["members"] if m.get("geometry")]
        return {"type": "MultiLineString", "coordinates": lines} if lines else None
    return None


def insert_point(table, cols, values, geom):
    placeholders = ", ".join(["%s"] * len(values))
    sql(f"INSERT INTO {table} ({', '.join(cols)}, geom) VALUES ({placeholders}, {POINT_SQL})",
        list(values) + [json.dumps(geom)])


class Command(BaseCommand):
    help = "Reconstruit les couches du géoportail (commune de Blitta 2) à partir de données ouvertes."

    def add_arguments(self, parser):
        parser.add_argument("--cache-dir", default=os.path.join(tempfile.gettempdir(), "horieon_import"),
                            help="Dossier où garder les fichiers téléchargés.")
        parser.add_argument("--refresh", action="store_true", help="Retélécharge les données même si elles sont en cache.")
        parser.add_argument("--sans-oms", action="store_true", help="N'utilise pas l'inventaire OMS des formations sanitaires.")

    # ------------------------------------------------------------------ utils
    def cached(self, filename, fetch):
        path = os.path.join(self.cache_dir, filename)
        if self.refresh or not os.path.exists(path):
            self.stdout.write(f"  téléchargement : {filename}")
            content = fetch()
            with open(path, "wb") as fh:
                fh.write(content)
        with open(path, "rb") as fh:
            return fh.read()

    def hdx_resource(self, dataset, resource_name):
        meta = requests.get(HDX_API.format(dataset), headers={"User-Agent": USER_AGENT}, timeout=120).json()
        for res in meta["result"]["resources"]:
            if res["name"] == resource_name:
                r = requests.get(res["url"], headers={"User-Agent": USER_AGENT}, timeout=600)
                r.raise_for_status()
                return r.content
        raise CommandError(f"Ressource {resource_name} introuvable dans le jeu HDX {dataset}.")

    def overpass(self, query):
        last = None
        for url in OVERPASS_ENDPOINTS:
            for _ in range(2):
                try:
                    r = requests.post(url, data={"data": query}, timeout=300,
                                      headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
                    if r.status_code == 200:
                        return r.content
                    last = f"{url} -> HTTP {r.status_code}"
                except requests.RequestException as exc:
                    last = f"{url} -> {exc}"
                time.sleep(5)
        raise CommandError(f"Overpass indisponible : {last}")

    # ----------------------------------------------------------------- étapes
    def handle(self, *args, **options):
        self.cache_dir = options["cache_dir"]
        self.refresh = options["refresh"]
        os.makedirs(self.cache_dir, exist_ok=True)

        self.stdout.write("1/4 Limites administratives (COD-AB)")
        archive = self.cached("tgo_admin_boundaries.geojson.zip",
                              lambda: self.hdx_resource("cod-ab-tgo", "tgo_admin_boundaries.geojson.zip"))
        with zipfile.ZipFile(io.BytesIO(archive)) as zf:
            member = next(n for n in zf.namelist() if n.endswith("tgo_admin3.geojson"))
            adm3 = json.loads(zf.read(member))
        cantons = [f for f in adm3["features"] if f["properties"]["adm3_pcode"] in CANTONS]
        if len(cantons) != len(CANTONS):
            raise CommandError("Cantons de Blitta 2 introuvables dans le fichier COD-AB.")

        self.stdout.write("2/4 OpenStreetMap (Overpass)")
        osm = json.loads(self.cached("osm_blitta2.json", lambda: self.overpass(self.osm_query(cantons))))

        oms = None
        if not options["sans_oms"]:
            self.stdout.write("3/4 Inventaire OMS des formations sanitaires")
            try:
                content = self.cached("ssa_health.xlsx", lambda: self.hdx_resource(
                    "health-facilities-in-sub-saharan-africa", "Sub-Saharan_health_facilities.xlsx"))
                oms = self.read_oms(content)
            except Exception as exc:  # source complémentaire : on continue sans
                self.stderr.write(f"  inventaire OMS ignoré : {exc}")

        self.stdout.write("4/4 Chargement dans la base")
        self.create_tables()
        with transaction.atomic():
            for model in apps.get_app_config("geoportail").get_models():
                sql(f"TRUNCATE {model._meta.db_table}")
            self.load_boundaries(cantons)
            places = self.load_osm(osm)
            self.finalize(places)
            if oms is not None:
                self.enrich_health(oms)

        self.stdout.write(self.style.SUCCESS("Import terminé :"))
        for model in apps.get_app_config("geoportail").get_models():
            table = model._meta.db_table
            self.stdout.write(f"  {table:<20} {sql(f'SELECT count(*) FROM {table}')[0][0]}")

    def create_tables(self):
        existing = set(connection.introspection.table_names())
        with connection.schema_editor() as editor:
            for model in apps.get_app_config("geoportail").get_models():
                if model._meta.db_table not in existing:
                    editor.create_model(model)
                    self.stdout.write(f"  table créée : {model._meta.db_table}")

    @staticmethod
    def osm_query(cantons):
        def coords(g):
            polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
            for poly in polys:
                for ring in poly:
                    yield from ring

        pts = [c for f in cantons for c in coords(f["geometry"])]
        bbox = (f"{min(p[1] for p in pts):.4f},{min(p[0] for p in pts):.4f},"
                f"{max(p[1] for p in pts):.4f},{max(p[0] for p in pts):.4f}")
        return f"""
        [out:json][timeout:240][bbox:{bbox}];
        (
          way["highway"~"^(trunk|primary|secondary|tertiary|unclassified|track)$"];
          nwr["amenity"~"^(school|kindergarten|college|hospital|clinic|doctors|health_post|marketplace|drinking_water|water_point)$"];
          nwr["healthcare"];
          nwr["man_made"~"^(water_well|water_tower|storage_tank|water_tap|borehole)$"];
          nwr["leisure"~"^(pitch|stadium)$"];
          nwr["shop"~"^(agrarian|farm)$"];
          nwr["office"="cooperative"];
          node["place"~"^(town|village|hamlet|quarter|neighbourhood|isolated_dwelling)$"];
        );
        out tags geom;
        """

    @staticmethod
    def read_oms(content):
        import pandas as pd

        df = pd.read_excel(io.BytesIO(content))
        df = df[df["Country"].str.contains("Togo", na=False)].copy()

        def fix(s):  # le fichier contient de l'UTF-8 décodé en CP437 (« Unit├⌐ »)
            for enc in ("cp437", "cp1252"):
                try:
                    return s.encode(enc).decode("utf-8")
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue
            return s

        for col in ("Facility_n", "Facility_t", "Ownership"):
            df[col] = df[col].astype(str).map(fix)
        return df

    @staticmethod
    def load_boundaries(cantons):
        for gid, f in enumerate(sorted(cantons, key=lambda f: f["properties"]["adm3_pcode"]), start=1):
            p = f["properties"]
            sql("""INSERT INTO cant_bli2 (gid, canton, code_canto, prefecture, code_prefe, region, code_regio, geom)
                   VALUES (%s, %s, %s, %s, %s, %s, %s,
                           ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))""",
                [gid, CANTONS[p["adm3_pcode"]], int(p["adm3_pcode"][2:]), p["adm2_name"],
                 int(p["adm2_pcode"][2:]), p["adm1_name"], int(p["adm1_pcode"][2:]), json.dumps(f["geometry"])])
        sql("""INSERT INTO bl2 (commune, code_commu, region, code_regio, prefecture, code_prefe, geom)
               SELECT 'Blitta 2', 10102, 'Centrale', 1, 'Blitta', 101,
                      ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_Union(geom)), 3))
               FROM cant_bli2""")

    def load_osm(self, data):
        places = []
        for el in data["elements"]:
            t = el.get("tags", {})
            geom = osm_geometry(el)
            if geom is None:
                continue
            if "place" in t and el["type"] == "node":
                if t.get("name"):
                    places.append((t["name"], el["lon"], el["lat"]))
                continue
            self.load_feature(el, t, geom)
        return places

    @staticmethod
    def load_feature(el, t, geom):
        hw = t.get("highway")
        if hw and el["type"] == "way" and geom["type"] == "LineString":
            paved = t.get("surface") in ("asphalt", "paved", "concrete", "chipseal")
            nationale = hw in ("trunk", "primary") or (t.get("ref", "").upper().startswith("N") and paved)
            route_clas = {"trunk": "Route nationale", "primary": "Route nationale", "secondary": "Route secondaire",
                          "tertiary": "Route tertiaire", "unclassified": "Piste", "track": "Piste agricole"}[hw]
            route_reco = "Revêtue" if paved or nationale else ("Non revêtue" if t.get("surface") else NR)
            sql("""INSERT INTO routeb2 (route_type, route_clas, route_reco, route_nom, geom)
                   VALUES (%s, %s, %s, %s, ST_Multi(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)))""",
                ["Route nationale revêtue" if nationale else "Piste rurale", route_clas, route_reco,
                 (t.get("ref") or t.get("name") or NR)[:100], json.dumps(geom)])
            return

        amenity = t.get("amenity")
        if amenity in ("school", "kindergarten", "college"):
            kind = classify_school(t)
            if kind:
                name = name_of(t, {"jardin": "Jardin d'enfants", "college": "Collège", "lycee": "Lycée"}[kind])
                insert_point({"jardin": "jardb2", "college": "collegeb2", "lycee": "lyc2"}[kind],
                             ["canton_nom", "nom_locali", "etablissem", "etab_adr", "ouverture", "etabliss_1",
                              "terrain", "inspection", "ministere"],
                             ["", "", name, (t.get("addr:street") or t.get("addr:city") or "")[:100],
                              (t.get("start_date") or NR)[:100], statut(t, name), NR, NR,
                              "Ministère des Enseignements Primaire, Secondaire et Technique"], geom)
            return

        if amenity in ("hospital", "clinic", "doctors", "health_post") or "healthcare" in t:
            name = name_of(t, "Formation sanitaire")
            kind = t.get("healthcare") or amenity or ""
            services = {"hospital": "Hôpital", "clinic": "Centre de santé", "centre": "Centre de santé",
                        "doctors": "Cabinet médical", "health_post": "Unité de soins périphérique (USP)",
                        "pharmacy": "Pharmacie", "dentist": "Soins dentaires"}.get(kind, NR)
            if t.get("healthcare:speciality"):
                services = t["healthcare:speciality"].replace(";", ", ")
            services = health_type(name) or services
            insert_point("formation_s", ["canton_nom", "nom_locali", "nom_fs", "ouverture", "secteur", "services_p"],
                         ["", "", name, (t.get("opening_hours") or t.get("start_date") or NR)[:100],
                          statut(t, name), services[:100]], geom)
            return

        if amenity == "marketplace":
            insert_point("marches", ["canton_nom", "nom_locali", "marche_nom", "jour"],
                         ["", "", name_of(t, ""), (t.get("opening_hours") or NR)[:100]], geom)
            return

        mm = t.get("man_made")
        if mm in ("water_well", "borehole"):
            typ = {"manual": "Pompe manuelle", "powered": "Pompe motorisée", "no": "Puits sans pompe"}.get(
                t.get("pump"), "Forage" if mm == "borehole" else "Puits")
            insert_point("pea", ["canton_nom", "nom_locali", "forage_nom", "forage_typ", "batiment_n"],
                         ["", "", name_of(t, ""), typ, NR], geom)
            return

        if amenity in ("drinking_water", "water_point") or mm == "water_tap":
            insert_point("bornefontaines", ["canton_nom", "borne_font"], ["", name_of(t, "")], geom)
            return

        if mm == "water_tower" or (mm == "storage_tank" and t.get("content", "water") == "water"):
            insert_point("chatea", ["canton_nom", "nom_locali", "chateau_no", "organisme"],
                         ["", "", name_of(t, ""), (t.get("operator") or NR)[:100]], geom)
            return

        if t.get("leisure") in ("pitch", "stadium") and geom["type"] == "Polygon":
            sport = {"soccer": "Football", "basketball": "Basketball", "volleyball": "Volleyball",
                     "handball": "Handball", "athletics": "Athlétisme", "multi": "Multisport"}.get(
                t.get("sport", ""), t.get("sport", NR))
            sql("""INSERT INTO stade_terrainbl2 (canton_nom, nom_locali, terrain, terrain_sp, geom)
                   VALUES ('', '', %s, %s,
                           ST_Multi(ST_CollectionExtract(ST_MakeValid(ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326)), 3)))""",
                [name_of(t, "Stade" if t.get("leisure") == "stadium" else "Terrain de sport"), sport[:100],
                 json.dumps(geom)])
            return

        if t.get("office") == "cooperative":
            insert_point("cooperativebl2", ["canton_nom", "nom_locali", "cooperativ", "cooperat_1"],
                         ["", "", name_of(t, "Coopérative"), (t.get("description") or NR)[:100]], geom)
            return

        if t.get("shop") in ("agrarian", "farm"):
            insert_point("magazin_intrantbl2", ["canton_nom", "etab_nom", "ouverture", "organisme"],
                         ["", name_of(t, "Magasin d'intrants"), (t.get("opening_hours") or NR)[:100],
                          (t.get("operator") or NR)[:100]], geom)

    @staticmethod
    def finalize(places):
        sql("CREATE TEMP TABLE _places (name text, geom geometry(Point, 4326)) ON COMMIT DROP")
        for name, lon, lat in places:
            sql("INSERT INTO _places VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))", [name, lon, lat])

        # Ne garder que ce qui est dans la commune ; routes découpées au contour
        for table in POINT_TABLES + ["stade_terrainbl2"]:
            sql(f"DELETE FROM {table} t USING bl2 c WHERE NOT ST_Intersects(t.geom, c.geom)")
        sql("UPDATE routeb2 r SET geom = ST_Multi(ST_CollectionExtract(ST_Intersection(r.geom, c.geom), 2)) FROM bl2 c")
        sql("DELETE FROM routeb2 WHERE geom IS NULL OR ST_IsEmpty(geom)")

        # Canton et localité la plus proche
        for table in POINT_TABLES + ["stade_terrainbl2"]:
            sql(f"""UPDATE {table} t SET canton_nom = k.canton FROM cant_bli2 k
                    WHERE ST_Intersects(k.geom, ST_PointOnSurface(t.geom))""")
        for table in LOCALI_TABLES:
            sql(f"""UPDATE {table} t SET nom_locali = COALESCE((
                        SELECT p.name FROM _places p ORDER BY p.geom <-> ST_PointOnSurface(t.geom) LIMIT 1), %s)""",
                [NR])

        # Noms manquants : « <type> de <localité> »
        sql("UPDATE marches SET marche_nom = 'Marché de ' || nom_locali WHERE marche_nom = ''")
        sql("UPDATE pea SET forage_nom = forage_typ || ' de ' || nom_locali WHERE forage_nom = ''")
        sql("UPDATE chatea SET chateau_no = 'Château d''eau de ' || nom_locali WHERE chateau_no = ''")
        sql("""UPDATE bornefontaines b SET borne_font = COALESCE('Borne-fontaine de ' || (
                   SELECT p.name FROM _places p ORDER BY p.geom <-> b.geom LIMIT 1), 'Borne-fontaine')
               WHERE borne_font = ''""")
        for table in ("jardb2", "collegeb2", "lyc2"):
            sql(f"UPDATE {table} SET etab_adr = nom_locali WHERE etab_adr = ''")

        # Doublons OSM (nœud + bâtiment pour la même structure) : on garde le mieux nommé
        sql("""DELETE FROM formation_s a USING formation_s b
               WHERE a.id <> b.id AND ST_DWithin(a.geom::geography, b.geom::geography, 50)
                 AND (a.nom_fs = 'Formation sanitaire' AND b.nom_fs <> 'Formation sanitaire'
                      OR (a.nom_fs = 'Formation sanitaire') = (b.nom_fs = 'Formation sanitaire') AND a.id > b.id)""")

    @staticmethod
    def enrich_health(df):
        for _, row in df.iterrows():
            inside = sql("SELECT ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) FROM bl2",
                         [row["Long"], row["Lat"]])[0][0]
            if not inside:
                continue
            typ = health_type(row["Facility_t"]) or row["Facility_t"]
            lieu = row["Facility_n"].split()[0]
            nom = f"{typ.split(' (')[0]} de {lieu}"
            # Coordonnées OMS arrondies (~2 km) : rapprochement avec l'objet OSM le plus proche
            match = sql("""SELECT id FROM formation_s
                           WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 2500)
                           ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) LIMIT 1""",
                        [row["Long"], row["Lat"], row["Long"], row["Lat"]])
            if match:
                sql("""UPDATE formation_s SET
                           nom_fs = CASE WHEN nom_fs = 'Formation sanitaire' THEN %s ELSE nom_fs END,
                           services_p = %s,
                           secteur = CASE WHEN secteur = %s THEN %s ELSE secteur END
                       WHERE id = %s""", [nom, typ, NR, row["Ownership"], match[0][0]])
            else:
                insert_point("formation_s", ["canton_nom", "nom_locali", "nom_fs", "ouverture", "secteur", "services_p"],
                             ["", lieu, nom, NR, row["Ownership"], typ],
                             {"type": "Point", "coordinates": [row["Long"], row["Lat"]]})
                sql("""UPDATE formation_s t SET canton_nom = k.canton FROM cant_bli2 k
                       WHERE t.canton_nom = '' AND ST_Intersects(k.geom, t.geom)""")
