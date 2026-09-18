// ==============================
// --- Carte Leaflet ---
// ==============================
// Centrée sur la commune de Blitta 2 (préfecture de Blitta)
const map = L.map('map').setView([8.15, 1.12], 11);

// ==============================
// --- Basemaps ---
// ==============================
const osm = L.tileLayer(
    'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    // OSM refuse les tuiles demandées sans Referer (Django envoie "same-origin" par défaut)
    { maxZoom: 22, maxNativeZoom: 19, referrerPolicy: 'strict-origin-when-cross-origin', attribution: '© OpenStreetMap' }
).addTo(map);

const satellite = L.tileLayer(
    'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    { maxZoom: 22, attribution: '© Esri' }
);

const hybride = L.tileLayer(
    'http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',
    { maxZoom: 22, attribution: '© Google' }
);

// Échappe le texte avant de l'insérer dans une bulle (valeurs issues de la base)
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// ==============================
// --- Couches Django ---
// ==============================

// Préfecture
const prefectureLayer = L.geoJSON(null, {
    style: { color: "green", weight: 2 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup("Préfecture : " + escapeHtml(feature.properties.prefecture));
    }
});

// Région
const regionLayer = L.geoJSON(null, {
    style: { color: "blue", weight: 2 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup("Région : " + escapeHtml(feature.properties.region));
    }
});

// Commune
const communeLayer = L.geoJSON(null, {
    style: { color: "orange", weight: 1 },
    onEachFeature: function (feature, layer) {
        layer.bindPopup(
            "Commune : " + escapeHtml(feature.properties.commune) +
            "<br>Préfecture : " + escapeHtml(feature.properties.prefecture)
        );
    }
});

// ==============================
// --- Fetch Django ---
// ==============================

function loadLayer(url, layer) {
    return fetch(url)
        .then(res => {
            if (!res.ok) throw new Error(`${url} : HTTP ${res.status}`);
            return res.json();
        })
        .then(data => layer.addData(data))
        .catch(err => console.error("Erreur chargement couche :", err));
}

loadLayer('/agriculture/api/prefectures/', prefectureLayer);
loadLayer('/agriculture/api/regions/', regionLayer);
loadLayer('/agriculture/api/communes/', communeLayer).then(() => {
    // Zoom sur les communes chargées (Blitta 2), si la couche n'est pas vide
    if (communeLayer.getLayers().length) {
        communeLayer.addTo(map);
        map.fitBounds(communeLayer.getBounds(), { padding: [20, 20] });
    }
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
