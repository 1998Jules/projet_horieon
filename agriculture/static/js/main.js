// ==============================
// --- Carte Leaflet ---
// ==============================
const map = L.map('map').setView([6.23461, 1.59096], 14);

// ==============================
// --- Basemaps --- 
// ==============================
const osm = L.tileLayer(
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { maxZoom: 22, attribution: '© OpenStreetMap' }
).addTo(map);

const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 22, attribution: '© Esri' }
);

const hybride = L.tileLayer(
    'http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
    { maxZoom: 22, attribution: '© Google' }
);
const url = "http://localhost:8089/geoserver/horicommune/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=horicommune:canton_lac1&outputFormat=application/json&srsName=EPSG:4326";
// Contrôle des couches



// ==============================
// --- Couches Django ---
// ==============================

// Préfecture
const prefectureLayer = L.geoJSON(null, {
    style: { color: "green", weight: 2 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup("Préfecture: " + feature.properties.prefecture);
    }
});

// Région
const regionLayer = L.geoJSON(null, {
    style: { color: "blue", weight: 2 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup("Région: " + feature.properties.region);
    }
});

// Commune
const communeLayer = L.geoJSON(null, {
    style: { color: "orange", weight: 1 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup(
            "Commune: " + feature.properties.commune +
            "<br>Préfecture: " + feature.properties.prefecture
        );
    }
});

// ==============================
// --- Fetch Django ---
// ==============================

fetch('/agriculture/geojson/prefecture/')
    .then(res => res.json())
    .then(data => prefectureLayer.addData(data));

fetch('/agriculture/geojson/region/')
    .then(res => res.json())
    .then(data => {
        regionLayer.addData(data);
        map.fitBounds(regionLayer.getBounds()); // zoom auto
    });

fetch('/agriculture/geojson/commune/')
    .then(res => res.json())
    .then(data => {
        console.log("COMMUNE DATA:", data); // 👈 AJOUTE ÇA
        communeLayer.addData(data);
    });
    


L.control.layers(
    {
        "OpenStreetMap": osm,
        "Satellite": satellite,
        "Hybride": hybride
    },
    {
        "Région": regionLayer,
        "Préfecture": prefectureLayer,
        "Commune": communeLayer
    }
).addTo(map);
L.tileLayer('https://earthengine.googleapis.com/v1/projects/ee-koutoumbogajules/maps/4283efe60ae4e59ecba2fb0ba980f209-067211dcf325c448e16ee8a4b601575c/tiles/{z}/{x}/{y}', {
  attribution: 'Google Earth Engine',
  opacity: 0.7
}).addTo(map);
