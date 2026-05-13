from django.db import models
from django.contrib.gis.db import models


class Cantons(models.Model):
    gid = models.IntegerField(primary_key=True)
    canton = models.CharField(max_length=100)
    code_canto = models.IntegerField()
    prefecture = models.CharField(max_length=100)
    code_prefe = models.IntegerField()
    region = models.CharField(max_length=100)
    code_regio = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table = "cant_bli2"
        managed = False

class Commune(models.Model):
    commune = models.CharField(max_length=100)
    code_commu = models.IntegerField()
    region = models.CharField(max_length=100)
    code_regio = models.IntegerField()
    prefecture = models.CharField(max_length=100)
    code_prefe = models.IntegerField()
    geom = models.MultiPolygonField(srid=4326)

    class Meta:
        db_table = "bl2"
        managed = False


class routes(models.Model):
    id = models.AutoField(primary_key=True)  
    route_type = models.CharField(max_length=100)
    route_clas = models.CharField(max_length=100)
    route_reco = models.CharField(max_length=100)
    route_nom = models.CharField(max_length=100)
    geom = models.MultiLineStringField(srid= 4326)

    class Meta:
        db_table = "routeb2"
        managed = False






class marche(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    marche_nom = models.CharField(max_length=100)
    jour = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='marches/', null=True, blank=True)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "marches"
        managed = False

class jardin(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    etablissem = models.CharField(max_length=100)
    etab_adr = models.CharField(max_length=100)
    ouverture= models.CharField(max_length=100)
    etabliss_1 = models.CharField(max_length=100)
    terrain = models.CharField(max_length=100)
    inspection = models.CharField(max_length=100)
    ministere = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "jardb2"
        managed = False

class college(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    etablissem = models.CharField(max_length=100)
    etab_adr = models.CharField(max_length=100)
    ouverture = models.CharField(max_length=100)
    etabliss_1 = models.CharField(max_length=100)
    terrain = models.CharField(max_length=100)
    inspection = models.CharField(max_length=100)
    ministere = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "collegeb2"
        managed = False


class lycee(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    etablissem = models.CharField(max_length=100)
    etab_adr = models.CharField(max_length=100)
    ouverture = models.CharField(max_length=100)
    etabliss_1 = models.CharField(max_length=100)
    terrain = models.CharField(max_length=100)
    inspection = models.CharField(max_length=100)
    ministere = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "lyc2"
        managed = False

class pea(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    forage_nom = models.CharField(max_length=100)
    forage_typ = models.CharField(max_length=100)
    batiment_n = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "pea"
        managed = False


class bornefontaine(models.Model):
    canton_nom = models.CharField(max_length=100)
    borne_font = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "bornefontaines"
        managed = False

class chateau(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    chateau_no = models.CharField(max_length=100)
    organisme = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "chatea"
        managed = False


class hopitale(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    nom_fs = models.CharField(max_length=100)
    ouverture = models.CharField(max_length=100)
    secteur = models.CharField(max_length=100)
    services_p = models.CharField(max_length=100)
    geom = models.PointField(srid=4326)

    class Meta:
        db_table = "formation_s"
        managed = False



class terrain(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    terrain = models.CharField(max_length=100)
    terrain_sp = models.CharField(max_length=100)
    geom = models.MultiPolygonField(srid=4326)


    class Meta:
        db_table = "stade_terrainbl2"
        managed = False

class coperative(models.Model):
    canton_nom = models.CharField(max_length=100)
    nom_locali = models.CharField(max_length=100)
    cooperativ = models.CharField(max_length=100)
    cooperat_1 = models.CharField(max_length=100)
    geom =  models.PointField(srid=4326)


    class Meta:
        db_table = "cooperativebl2"
        managed = False

class magazinbl2(models.Model):
    canton_nom = models.CharField(max_length=100)
    etab_nom = models.CharField(max_length=100)
    ouverture = models.CharField(max_length=100)
    organisme = models.CharField(max_length=100)
    geom =  models.PointField(srid=4326)


    class Meta:
        db_table = "magazin_intrantbl2"
        managed = False