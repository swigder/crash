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
});
map.addLayer(clusterLayer)

map.setView([39.00, -76.88], 13)
map.setView([39.0005, -76.88], 13)  // Hack to get markers to show on first load

function getNewData() {
    let bounds = map.getBounds()
    let south = Math.floor(bounds.getSouth())
    let north = Math.ceil(bounds.getNorth())
    let west = Math.floor(bounds.getWest())
    let east = Math.ceil(bounds.getEast())
    for (let lat = south; lat < north + 1; lat++) {
        for (let long = west; long < east + 1; long++) {
            for (let year = 2015; year < 2020; year++) {
                let file = `geojson/geojson-${year}-${lat}_${long}.json`
                if (!loaded.has(file)) {
                    $.getJSON(file, function (data) {
                        geojsonLayer.addData(data)
                    });
                    loaded.add(file)
                }
            }
        }
    }
    clusterLayer.clearLayers()
    clusterLayer.addLayer(geojsonLayer)
    updateCount();
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
