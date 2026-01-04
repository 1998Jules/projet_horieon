// ==============================
// --- Carte Leaflet ---
// ==============================
const map = L.map('map').setView([6.23461,1.59096], 14);
let hoverLayer = null;
let clickLayer = null;
let allQuartiers = [];

// ==============================
// --- Basemaps --- 
// ==============================
const baseLayers = {
    "OpenStreetMap": L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:22, attribution:'© OpenStreetMap'}).addTo(map),
    "Satellite": L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:22, attribution:'© Esri'}),
    "Hybride": L.tileLayer('http://mt0.google.com/vt/lyrs=y&hl=en&x={x}&y={y}&z={z}',{maxZoom:22, attribution:'© Google'})
};

// ==============================
// --- Couches WMS métier --- 
// ==============================
const wmsLayers = {
    "Quartiers": L.tileLayer.wms("http://localhost:8089/geoserver/horicommune/wms",{layers:"qartier_aneho", format:"image/png", transparent:true, attribution:"GeoServer", maxZoom:22}).addTo(map),
    "Commune": L.tileLayer.wms("http://localhost:8089/geoserver/horicommune/wms",{layers:"commune_lac1", format:"image/png", transparent:true, attribution:"GeoServer", maxZoom:22}).addTo(map),
    "Routes": L.tileLayer.wms("http://localhost:8089/geoserver/horicommune/wms",{layers:"route", format:"image/png", transparent:true, attribution:"GeoServer", maxZoom:22}),
    "Lagune": L.tileLayer.wms("http://localhost:8089/geoserver/horicommune/wms",{layers:"lagune", format:"image/png", transparent:true, attribution:"GeoServer", maxZoom:22})
};

// ==============================
// --- Visibilité selon zoom --- 
// ==============================
const ROUTE_ZOOM_MIN = 16;
const LAGUNE_ZOOM_MIN = 14;

function updateRoutesVisibility() {
    map.getZoom()>=ROUTE_ZOOM_MIN ? map.addLayer(wmsLayers["Routes"]) : map.removeLayer(wmsLayers["Routes"]);
}
function updateLaguneVisibility() {
    map.getZoom()>=LAGUNE_ZOOM_MIN ? map.addLayer(wmsLayers["Lagune"]) : map.removeLayer(wmsLayers["Lagune"]);
}

updateRoutesVisibility();
updateLaguneVisibility();

map.on('zoomend', ()=>{
    updateRoutesVisibility();
    updateLaguneVisibility();
});

// ==============================
// --- Coordonnées projetées--- 
// ==============================
var projUTM = '+proj=utm +zone=31 +datum=WGS84 +units=m +no_defs';
map.on('mousemove', function(e){
    const utm = proj4('EPSG:4326', projUTM, [e.latlng.lng,e.latlng.lat]);
    document.getElementById('coords').innerHTML = `X : ${utm[0].toFixed(2)} | Y : ${utm[1].toFixed(2)}`;
});

// ==============================
// --- Survol & clic quartiers --- 
// ==============================
function getFeatureInfoUrl(map, layer, latlng, params={}) {
    const point = map.latLngToContainerPoint(latlng,map.getZoom());
    const size = map.getSize();
    const defaultParams = {
        request:'GetFeatureInfo', service:'WMS', srs:'EPSG:4326',
        styles:'', version:'1.1.1',
        bbox: map.getBounds().toBBoxString(),
        height: size.y, width:size.x,
        layers: layer.wmsParams.layers,
        query_layers: layer.wmsParams.layers
    };
    return `${layer._url}?${new URLSearchParams({...defaultParams,...params,x:Math.round(point.x),y:Math.round(point.y)})}`;
}

map.on('click', async function(e){



    
    const url = getFeatureInfoUrl(
        map,
        wmsLayers["Quartiers"],
        e.latlng,
        { info_format:'application/json', feature_count:1 }
    );





    try{
        const res = await fetch(url).then(r=>r.json());
        if(!res.features?.length) return;

        const f = res.features[0];

        if(clickLayer) map.removeLayer(clickLayer);

        clickLayer = L.geoJSON(f.geometry,{
            style:{ color:'#28a745', weight:3, fillOpacity:0.2 }
        }).addTo(map);

        map.fitBounds(clickLayer.getBounds(),{
            padding:[40,40], maxZoom:18, animate:true
        });

        // =========================
        // CALCUL SUPERFICIE 
        // =========================
        let surface = 0;

        clickLayer.eachLayer(layer => {
            const latlngs = layer.getLatLngs();

            // MultiPolygon
            if (Array.isArray(latlngs[0][0])) {
                latlngs.forEach(polygon => {
                    surface += L.GeometryUtil.geodesicArea(polygon[0]);
                });
            }
            // Polygon simple
            else {
                surface += L.GeometryUtil.geodesicArea(latlngs[0]);
            }
        });

        const surfaceHa = (surface / 10000).toFixed(2);
        const surfaceKm2 = (surface / 1e6).toFixed(3);

        L.popup()
            .setLatLng(clickLayer.getBounds().getCenter())
            .setContent(`
                <b>Quartier :</b> ${f.properties.quartiers || 'Nom inconnu'}<br>
                <b>Superficie :</b>  ${surfaceKm2} km²
            `)
            .openOn(map);

    }catch(err){
        console.error(err);
    }
});


//pour systeme lagunalaire 

 







// ==============================
// --- Charger cantons & quartiers --- 
// ==============================
async function loadQuartiers(){
    const url = "http://localhost:8089/geoserver/horicommune/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=horicommune:qartier_aneho&outputFormat=application/json&srsName=EPSG:4326";
    try{
        const res = await fetch(url);
        const data = await res.json();
        allQuartiers = data.features;
        console.log("Quartiers chargés:", allQuartiers.length);
    }catch(err){console.error(err);}
}
loadQuartiers();

async function loadCantons(){
    const url = "http://localhost:8089/geoserver/horicommune/ows?service=WFS&version=1.0.0&request=GetFeature&typeName=horicommune:canton_lac1&outputFormat=application/json&srsName=EPSG:4326";
    const select = document.getElementById("Canton-select");
    try{
        const res = await fetch(url);
        const data = await res.json();
        data.features.forEach(f=>{
            const opt = document.createElement("option");
            opt.textContent = f.properties.cant || "Nom inconnu";
            opt.dataset.geom = JSON.stringify(f.geometry);
            select.appendChild(opt);
        });
    }catch(err){console.error(err);}
}
loadCantons();

// --- Filtrer quartiers par canton ---
document.getElementById("Canton-select").addEventListener("change", function(){
    const sel = this.options[this.selectedIndex];
    if(!sel?.dataset.geom) return;

    const cantonFeature = turf.feature(JSON.parse(sel.dataset.geom));
    const quartierSelect = document.getElementById("quartier-select");
    quartierSelect.innerHTML='<option value="">-- Choisir un quartier --</option>';

    allQuartiers.forEach(q=>{
        if(turf.booleanIntersects(cantonFeature, turf.feature(q.geometry))){
            const opt = document.createElement("option");
            opt.value = JSON.stringify(q.geometry);
            opt.textContent = q.properties.quartiers||"Nom inconnu";
            quartierSelect.appendChild(opt);
        }
    });
});

// --- Sélection quartier ---
document.getElementById("quartier-select").addEventListener("change", function(){
    const val = this.value;
    if(!val) return;
    const geom = JSON.parse(val);
    if(hoverLayer) map.removeLayer(hoverLayer);
    hoverLayer = L.geoJSON(geom,{style:{color:'#007bff', weight:3, fillOpacity:0.2}}).addTo(map);
    map.fitBounds(hoverLayer.getBounds(),{padding:[50,50]});
    L.popup().setLatLng(hoverLayer.getBounds().getCenter())
             .setContent(`<b>Quartier :</b> ${this.options[this.selectedIndex].text}`)
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
        const val=e.target.value;
        Object.values(baseLayers).forEach(l=>map.removeLayer(l));
        if(val==='osm') baseLayers.OpenStreetMap.addTo(map);
        else if(val==='satellite') baseLayers.Satellite.addTo(map);
        else if(val==='hybrid') baseLayers.Hybride.addTo(map);
    });
});

// Thèmes
const themeBtns = document.querySelectorAll(".theme-btn");
themeBtns.forEach(btn=>{
    btn.addEventListener("click", e=>{
        themeBtns.forEach(b=>b.classList.remove("active"));
        btn.classList.add("active");
        updateLayerList(btn.dataset.theme);
    });
});

function updateLayerList(theme){
    const layerList = document.getElementById("layer-list");
    layerList.innerHTML="";
    const themeLayers = {
        "admin":["Quartiers","Commune"],
        "hydro":["Lagune"],
        "transport":["Routes"]
    };
    if(!themeLayers[theme]) return;

    themeLayers[theme].forEach(name=>{
        const layer = wmsLayers[name];
        if(!layer) return;
        const div = document.createElement("div");
        div.innerHTML = `<label><input type="checkbox" data-layer="${name}" ${map.hasLayer(layer)?'checked':''}> ${name}</label>`;
        layerList.appendChild(div);
    });

    layerList.querySelectorAll("input[type=checkbox]").forEach(cb=>{
        cb.addEventListener("change", e=>{
            const name = e.target.dataset.layer;
            if(e.target.checked) map.addLayer(wmsLayers[name]);
            else map.removeLayer(wmsLayers[name]);
        });
    });
}

// Initialisation
updateLayerList("admin");
