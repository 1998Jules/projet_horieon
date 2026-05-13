// ==============================
// --- Carte Leaflet ---
// ==============================
// Ancien
// const map = L.map('map').setView([8.08,1.12], 14);

// Nouveau
const map = L.map('map', { zoomControl: false }).setView([8.08, 1.12], 14);
// Ajouter les boutons de zoom en bas à droite
L.control.zoom({
    position: 'bottomright'
}).addTo(map);

let hoverLayer = null;
let clickLayer = null;
let allQuartiers = [];
let allCantons = [];
let allRoute = [];

// ==============================
// --- Basemaps --- 
// ==============================
const baseLayers = {
    "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:22, attribution:'© OpenStreetMap'}).addTo(map),
    "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:22, attribution:'© Esri'}),
    "Hybride": L.tileLayer('http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',{maxZoom:22, attribution:'© Google'})
};

// ==============================
// --- Fonction pour styliser les couches ---
// ==============================
function styleQuartier(feature) {
    return {
        fillColor: '#007bff',
        weight: 2,
        opacity: 1,
        color: '#0056b3',
        dashArray: '',
        fillOpacity: 0.2
    };
}

function styleCanton(feature) {
    return {
        fillColor: '#ff6600',
        weight: 2,
        opacity: 1,
        color: '#cc5200',
        dashArray: '',
        fillOpacity: 0.01
    };
}

function styleCommune(feature) {
    return {
        fillColor: '#28a745',
        weight: 2,
        opacity: 1,
        
        dashArray: '-',
        fillOpacity: 0

    };
}

function normalize(str) {
    return str
        ?.toLowerCase()
        .normalize("NFD")
        .replace(/[\u0300-\u036f]/g, "")
        .trim();
}

function styleRoute(feature) {
    const type = normalize(feature.properties?.route_type);

    if (type === 'piste rurale') {
        return {
            color: '#201c18',
            weight: 1.5,
            dashArray: '4,6',
            opacity: 1
        };
    }

    

    if (type === 'route nationale revetue') {
        return {
            color: '#DC143C',
            weight: 4,
            dashArray: '',
            opacity: 1
        };
    }

    // ❌ Pas de style par défaut → invisible
    return {
        opacity: 0,
        weight: 0
    };
}


// ==============================
// --- Fonction pour afficher les infos au clic ---
// ==============================
let activePopup = null;

function onEachFeature(feature, layer, layerType) {
    if (feature.properties) {
        // Style au survol
        layer.on({
    click: function(e) {

    // 🔴 FERMER le popup précédent
    if (activePopup) {
        map.closePopup(activePopup);
        activePopup = null;
    }

    // Supprimer ancien highlight
    if (clickLayer) {
        map.removeLayer(clickLayer);
    }

    clickLayer = L.geoJSON(feature, {
        style: {
            weight: 4,
            color: '#5c74ee',
            fillColor: '#ff0000',
            fillOpacity: 0.05,
            dashArray: '', 
            opacity: 1
        }
    }).addTo(map);

    const bounds = layer.getBounds();
    const center = bounds.getCenter();

    let popupContent = `<div class="feature-popup"><h3>${layerType}</h3>`;
    for (const [key, value] of Object.entries(feature.properties)) {
        popupContent += `<p><strong>${key}:</strong> ${value}</p>`;
    }
    popupContent += `<hr><p><strong>Coordonnées centre:</strong><br>
        Lat: ${center.lat.toFixed(6)}<br>
        Lng: ${center.lng.toFixed(6)}</p></div>`;

    // 🟢 créer le popup
    activePopup = L.popup({
        maxWidth: 300,
        closeButton: true,
        autoClose: false,
        closeOnClick: false,
        className: 'custom-popup'
    })
    .setLatLng(center)
    .setContent(popupContent)
    .openOn(map);

    map.fitBounds(bounds, { padding: [50,50], maxZoom: 16 });
    clickLayer.bringToFront();
}

});
;
    }
}



// ==============================
// --- Couches GeoJSON métier --- 
// ==============================
const geoLayers = {
   
    "Commune": L.geoJSON(null, {
        style: styleCommune,
        onEachFeature: (feature, layer) => onEachFeature(feature, layer, 'Commune')
    }).addTo(map),
    
    "Cantons": L.geoJSON(null, {
        style: styleCanton,
        onEachFeature: (feature, layer) => onEachFeature(feature, layer, 'Canton')
    }).addTo(map),
    "Route": L.geoJSON(null, {
        style:  styleRoute,
         interactive: false

    }).addTo(map),
}


// COUCHES DE INFRASTRUCTURE

function onEachInfra(feature, layer, typeName) {
    layer.on('click', () => {

        if (activePopup) map.closePopup(activePopup);
        if (clickLayer) map.removeLayer(clickLayer);

        const center = layer.getLatLng();

        let content = `<div class="feature-popup"><h3>${typeName}</h3>`;
        for (const [k, v] of Object.entries(feature.properties)) {
            if (v) content += `<p><strong>${k}:</strong> ${v}</p>`;
        }
        content += '</div>';

        activePopup = L.popup({ maxWidth: 300 })
            .setLatLng(center)
            .setContent(content)
            .openOn(map);
    });
}

// couche eau 
function onEachEau(feature, layer, typeName) {
    layer.on('click', () => {

        if (activePopup) map.closePopup(activePopup);
        if (clickLayer) map.removeLayer(clickLayer);

        const center = layer.getLatLng();

        let content = `<div class="feature-popup"><h3>${typeName}</h3>`;
        for (const [k, v] of Object.entries(feature.properties)) {
            if (v) content += `<p><strong>${k}:</strong> ${v}</p>`;
        }
        content += '</div>';

        activePopup = L.popup({ maxWidth: 300 })
            .setLatLng(center)
            .setContent(content)
            .openOn(map);
    });
}




const infraIcons = {
    lycee: L.icon({
        iconUrl: '/static/icone/lycee.png',
        iconSize: [28, 28],
        iconAnchor: [14, 28],
        popupAnchor: [0, -28]
    }),

    college: L.icon({
        iconUrl: '/static/icone/college.png',
        iconSize: [26, 26],
        iconAnchor: [13, 26],
        popupAnchor: [0, -26]
    }),

    jardin: L.icon({
        iconUrl: '/static/icone/jardin.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    }),
     marche: L.icon({
        iconUrl: '/static/icone/marche.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    }),
   
};

const HydroIcons={
     Point_eau: L.icon({
        iconUrl: '/static/icone/pea.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    }),
     bornefontaine: L.icon({
        iconUrl: '/static/icone/bornefontaine.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    }),

     chateau: L.icon({
        iconUrl: '/static/icone/chateau.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    })
}

const santeIcons={
     hopitale: L.icon({
        iconUrl: '/static/icone/hopital.png',
        iconSize: [24, 24],
        iconAnchor: [12, 24],
        popupAnchor: [0, -24]
    }),
     
}

geoLayers["Lycées"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: infraIcons.lycee }),
    onEachFeature: (f, l) => onEachInfra(f, l, 'Lycée')
});

geoLayers["Collèges"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: infraIcons.college }),
    onEachFeature: (f, l) => onEachInfra(f, l, 'Collège')
});


geoLayers["Jardins"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: infraIcons.jardin }),
    onEachFeature: (f, l) => onEachInfra(f, l, 'Jardin')
});

geoLayers["marches"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: infraIcons.marche }),
    onEachFeature: (f, l) => onEachInfra(f, l, 'marche')
});


geoLayers["borne_fontaine"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: HydroIcons.bornefontaine }),
    onEachFeature: (f, l) => onEachInfra(f, l, 'borne_fontaine')
});




geoLayers["Points d'eau autonome"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: HydroIcons.Point_eau }),
    onEachFeature: (f, l) => onEachEau(f, l, "Point d'eau autonome")
});


geoLayers["chateau"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: HydroIcons.chateau }),
    onEachFeature: (f, l) => onEachEau(f, l, "chateau")
});



geoLayers["Formation sanitaire"] = L.geoJSON(null, {
    pointToLayer: (f, latlng) =>
        L.marker(latlng, { icon: santeIcons.hopitale }),
    onEachFeature: (f, l) => onEachEau(f, l, "Formation sanitaire")
});

// ==============================
// --- Charger GeoJSON --- 
// ==============================
async function loadGeoJSON(url, layer, storeArray=null) {
    try{
        const res = await fetch(url);
        const data = await res.json();
        layer.clearLayers();
        layer.addData(data);
        
        if(storeArray !== null) {
            storeArray.splice(0, storeArray.length, ...data.features);
            
            // Pour les cantons, peupler le select
            if (url.includes('cantons')) {
                populateCantonSelect(data.features);
            }
        }
        
        console.log(`${url} chargé, ${data.features.length} entités`);
    }catch(err){ 
        console.error("Erreur chargement GeoJSON:", err); 
    }
}

// ==============================
// --- Peupler le select des cantons ---
// ==============================
function populateCantonSelect(features) {
    const cantonSelect = document.getElementById("Canton-select");
    
    // Vider les options existantes sauf la première
    while (cantonSelect.options.length > 1) {
        cantonSelect.remove(1);
    }
    
    // Ajouter chaque canton
    features.forEach(feature => {
        if (feature.properties && feature.properties.cant) {
            const option = document.createElement("option");
            option.value = feature.properties.cant;
            option.textContent = feature.properties.cant;
            option.dataset.geom = JSON.stringify(feature.geometry);
            cantonSelect.appendChild(option);
        }
    });
    
    console.log(`${features.length} cantons ajoutés au select`);
   console.log(features.map(f => f.properties.route_type));



}

// ==============================
// --- Charger toutes les couches ---
// ==============================


async function initMap() {
    // Charger les couches légères en parallèle
    await Promise.all([
        loadGeoJSON("/geoportail/geojson/commune/", geoLayers.Commune),
        loadGeoJSON("/geoportail/geojson/cantons/", geoLayers.Cantons, allCantons),
        loadGeoJSON("/geoportail/geojson/routes/", geoLayers.Route, allRoute),
        loadGeoJSON("/geoportail/geojson/lycee/", geoLayers["Lycées"]),
        loadGeoJSON("/geoportail/geojson/college/", geoLayers["Collèges"]),
        loadGeoJSON("/geoportail/geojson/jardin/", geoLayers["Jardins"]),
        loadGeoJSON("/geoportail/geojson/Point_eau/", geoLayers["Points d'eau autonome"]),
        loadGeoJSON("/geoportail/geojson/Marches/", geoLayers["marches"]),
        loadGeoJSON("/geoportail/geojson/bornefontaine/", geoLayers["borne_fontaine"]),
        loadGeoJSON("/geoportail/geojson/chateau/", geoLayers["chateau"]),
        loadGeoJSON("/geoportail/geojson/hopitale/", geoLayers["Formation sanitaire"])
    ]);

    // Peupler le filtre canton et mettre à jour les stats
    populateFilterCanton(allCantons);
    updateFilteredStats();
}

// Lancer l'initialisation
initMap();


// ==============================
// --- Filtrer quartiers par canton --- 
// ==============================
document.getElementById("Canton-select").addEventListener("change", function(){
    const sel = this.options[this.selectedIndex];
    if(!sel?.dataset.geom) return;

    const cantonFeature = turf.feature(JSON.parse(sel.dataset.geom));
    const quartierSelect = document.getElementById("quartier-select");
    quartierSelect.innerHTML='<option value="">-- Choisir un quartier --</option>';

    let quartiersCount = 0;
    allQuartiers.forEach(q=>{
        if(turf.booleanIntersects(cantonFeature, turf.feature(q.geometry))){
            const opt = document.createElement("option");
            opt.value = JSON.stringify(q.geometry);
            opt.textContent = q.properties.quartiers || "Nom inconnu";
            opt.dataset.properties = JSON.stringify(q.properties); // Stocker toutes les propriétés
            quartierSelect.appendChild(opt);
            quartiersCount++;
        }
    });
    
    console.log(`${quartiersCount} quartiers trouvés pour ce canton`);
});

// ==============================
// --- Sélection quartier --- 
// ==============================
document.getElementById("quartier-select").addEventListener("change", function(){
    const sel = this.options[this.selectedIndex];
    if(!sel.value) return;
    
    const geom = JSON.parse(sel.value);
    const properties = sel.dataset.properties ? JSON.parse(sel.dataset.properties) : {};
    
    // Supprimer les anciennes couches
    if(hoverLayer) map.removeLayer(hoverLayer);
    if(clickLayer) map.removeLayer(clickLayer);
    
    // Créer la couche highlight
    hoverLayer = L.geoJSON(geom,{
        style: {
            color: '#007bff', 
            weight: 3, 
            fillOpacity: 0.2,
            fillColor: '#007bff'
        }
    }).addTo(map);
    
    // Zoom sur le quartier
    map.fitBounds(hoverLayer.getBounds(),{padding:[50,50]});
    
    // Créer et ouvrir le popup
    const bounds = hoverLayer.getBounds();
    const center = bounds.getCenter();
    
    let popupContent = `<div class="quartier-popup">`;
    popupContent += `<h3>Quartier: ${sel.text}</h3>`;
    
    // Afficher toutes les propriétés
    for (const [key, value] of Object.entries(properties)) {
        if (value) {
            popupContent += `<p><strong>${key}:</strong> ${value}</p>`;
        }
    }
    
    // Ajouter les coordonnées
    popupContent += `<hr>`;
    popupContent += `<p><strong>Coordonnées centre:</strong><br>`;
    popupContent += `Lat: ${center.lat.toFixed(6)}<br>`;
    popupContent += `Lng: ${center.lng.toFixed(6)}</p>`;
    
    popupContent += `</div>`;
    
    L.popup()
        .setLatLng(center)
        .setContent(popupContent)
        .openOn(map);
});

// ==============================
// --- Gestionnaire de couches personnalisé --- 
// ==============================
const layerBtn = document.getElementById("layerBtn");
const layerManager = document.getElementById("layer-manager");
layerBtn.addEventListener("click", ()=>layerManager.classList.toggle("hidden"));

// Basemap
document.querySelectorAll('input[name="basemap"]').forEach(r=>{
    r.addEventListener("change", e=>{
        Object.values(baseLayers).forEach(l=>map.removeLayer(l));
        if(e.target.value==='osm') baseLayers.OpenStreetMap.addTo(map);
        else if(e.target.value==='satellite') baseLayers.Satellite.addTo(map);
        else if(e.target.value==='hybrid') baseLayers.Hybride.addTo(map);
    });
});

// Thèmes
const themeBtns = document.querySelectorAll(".theme-btn");
themeBtns.forEach(btn=>{
    btn.addEventListener("click", ()=>{
        themeBtns.forEach(b=>b.classList.remove("active"));
        btn.classList.add("active");
        updateLayerList(btn.dataset.theme);
    });
});

function updateLayerList(theme){
    const layerList = document.getElementById("layer-list");
    layerList.innerHTML="";
    const themeLayers = {
        "admin":["Quartiers","Cantons","Commune"],
        "hydro":["Points d'eau autonome",'borne_fontaine','chateau'],
        "transport":["Route"],
        "infrastructure": ["Lycées", "Collèges", "Jardins","marches"],
        "sante": ["Formation sanitaire"],
        "agriculture": [""],
        "sport": [""],
    

    };
    if(!themeLayers[theme]) return;

    themeLayers[theme].forEach(name=>{
        const layer = geoLayers[name] || null;
        if(!layer) return;
        const div = document.createElement("div");
        div.innerHTML = `<label><input type="checkbox" data-layer="${name}" ${map.hasLayer(layer)?'checked':''}> ${name}</label>`;
        layerList.appendChild(div);
    });

    layerList.querySelectorAll("input[type=checkbox]").forEach(cb=>{
        cb.addEventListener("change", e=>{
            const name = e.target.dataset.layer;
            const layer = geoLayers[name];
            if(e.target.checked) map.addLayer(layer);
            else map.removeLayer(layer);
        });
    });
}

// ==============================
// --- Affichage coordonnées --- 
// ==============================
var projUTM = '+proj=utm +zone=31 +datum=WGS84 +units=m +no_defs';
map.on('mousemove', function(e){
    const utm = proj4('EPSG:4326', projUTM, [e.latlng.lng,e.latlng.lat]);
    document.getElementById('coords').innerHTML = `X : ${utm[0].toFixed(2)} | Y : ${utm[1].toFixed(2)}`;
});

// ==============================
// --- Fonctions utilitaires ---
// ==============================

// Fonction pour désélectionner toutes les couches
function clearSelection() {
    if (hoverLayer) {
        map.removeLayer(hoverLayer);
        hoverLayer = null;
    }
    if (clickLayer) {
        map.removeLayer(clickLayer);
        clickLayer = null;
    }
    map.closePopup();
}

//pour les infrastructure


// ==============================
// --- Peupler le filtre canton ---
// ==============================
function populateFilterCanton(features) {
    const filterCanton = document.getElementById("filter-canton");

    // Vider sauf la première option
    while(filterCanton.options.length > 1) filterCanton.remove(1);

    features.forEach(f => {
        const opt = document.createElement("option");
        opt.value = JSON.stringify(f.geometry);
        opt.textContent = f.properties.canton || "Nom inconnu";
        filterCanton.appendChild(opt);
    });
}

// ==============================
// --- Mettre à jour les stats selon filtres ---
// ==============================
function updateFilteredStats() {
    // Récupérer les filtres
    const cantonGeom = document.getElementById("filter-canton").value;
    const theme = document.getElementById("filter-theme").value;

    const selectedLayers = Array.from(document.querySelectorAll("#filter-layers input[type=checkbox]:checked"))
        .map(cb => cb.dataset.layer);

    let cantonFeature = cantonGeom ? turf.feature(JSON.parse(cantonGeom)) : null;

    function countLayer(name) {
        if(!selectedLayers.includes(name)) return 0;
        let layer = geoLayers[name];
        if(!layer) return 0;
        let count = 0;
        layer.eachLayer(l => {
            let geom = l.feature?.geometry;
            if(geom && (!cantonFeature || turf.booleanIntersects(cantonFeature, turf.feature(geom)))) {
                count++;
            }
        });
        return count;
    }

    document.getElementById('stat-lycees').textContent = countLayer("Lycées");
    document.getElementById('stat-colleges').textContent = countLayer("Collèges");
    document.getElementById('stat-jardins').textContent = countLayer("Jardins");
    document.getElementById('stat-marches').textContent = countLayer("marches");
    document.getElementById('stat-points-eau').textContent = countLayer("Points d'eau autonome");
    document.getElementById('stat-borne').textContent = countLayer("borne_fontaine");
    document.getElementById('stat-chateau').textContent = countLayer("chateau");
}

// Quand on change le canton, thème ou couches
document.getElementById("filter-canton").addEventListener("change", updateFilteredStats);
document.getElementById("filter-theme").addEventListener("change", updateFilteredStats);
document.querySelectorAll("#filter-layers input[type=checkbox]").forEach(cb => {
    cb.addEventListener("change", updateFilteredStats);
});

//await loadGeoJSON("/geoportail/geojson/cantons/", geoLayers.Cantons, allCantons);
populateFilterCanton(allCantons);
updateFilteredStats();

document.getElementById('toggle-left-panel').addEventListener('click', () => {
    document.getElementById('left-panel').classList.toggle('collapsed');
});
