const loaded = new Set()

let map = L.map('map')
map.on('moveend zoomend load', getNewData);

L.tileLayer('https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}', {
    attribution: 'Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>',
    maxZoom: 18,
    id: 'mapbox/streets-v11',
    tileSize: 512,
    zoomOffset: -1,
    accessToken: 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g'
}).addTo(map);

const emojis = {
    'car': '🚙',
    'bike': '🚴',
    'ped': '🚶',
    'other': ''
}

let geojsonLayer = L.geoJSON({"type": "FeatureCollection", "features": []}, {
    style: function (feature) {
        return feature.properties && feature.properties.style;
    },

    onEachFeature: function (feature, layer) {
        // layer.bindPopup(feature.properties.year);
        layer.on('click', function (e) {
            window.dispatchEvent(new CustomEvent("items-load", {
                detail: e.sourceTarget.feature.properties
            }));
        })
    },

    pointToLayer: function (feature, latlng) {
        const size = 20
        let harm = feature.properties.harm
        return L.marker(latlng, {
            icon: L.divIcon({
                iconSize: [size, size],
                // iconAnchor: [size / 2, size + 9],
                className: `circle ${harm}`,
                html: `${emojis[harm]}️`,
            })
        });
    }
})

let clusterLayer = L.markerClusterGroup({
    spiderfyOnMaxZoom: false,
    showCoverageOnHover: false,
    zoomToBoundsOnClick: false,
    disableClusteringAtZoom: 12,
    chunkedLoading: true,
});
map.addLayer(clusterLayer)

map.setView([39.00, -76.88], 13)

function getNewData() {
    let bounds = map.getBounds()
    let south = Math.floor(bounds.getSouth() / 2) * 2
    let north = Math.ceil(bounds.getNorth() / 2) * 2
    let west = Math.floor(bounds.getWest() / 2) * 2
    let east = Math.ceil(bounds.getEast() / 2) * 2
    let tasks = []
    for (let lat = south; lat < north + 2; lat += 2) {
        for (let long = west; long < east + 2; long += 2) {
            let file = `geojson/geojson-${lat}_${long}.json`
            if (!loaded.has(file)) {
                loaded.add(file)
                tasks.push($.Deferred(function (defer) {
                    $.ajax(file).then(defer.resolve, defer.resolve);
                }).promise())
            }
        }
    }
    $.when(...tasks).then(function (...allData) {
        allData.forEach(data => {
            if (data[1] === "success") {
                geojsonLayer.addData(data[0]);
            }
        })
        if (tasks.length > 0) {
            clusterLayer.clearLayers()
            clusterLayer.addLayer(geojsonLayer)
        }
        updateCount();
    });
}

function getCounts() {
    let crash_count = 0
    let fatality_count = 0
    for (const property in geojsonLayer._layers) {
        l = geojsonLayer._layers[property]
        if (l instanceof L.Marker && map.getBounds().contains(l.getLatLng())) {
            crash_count++
            fatality_count += l.feature.properties.num_fatalities
        }
    }
    return {crash_count: crash_count, fatality_count: fatality_count};
}

function updateCount() {
    window.dispatchEvent(new CustomEvent("count-updated", {
        detail: getCounts()
    }));
}
