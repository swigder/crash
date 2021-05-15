const loaded = new Set()

let metadata = {}
$.ajax({
    url: "geojson/file-metadata.json",
    async: false,
    dataType: "json",
    success: data => {
        metadata = data;
        window.dispatchEvent(new CustomEvent("metadata-load", {
            detail: metadata
        }))
    }
})

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
    },

    filter: function (feature, layer) {
        return showFeature(feature);
    },
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

document.getElementById('location-input').onkeydown = function (event) {
    let e = event || window.event;
    if (e.key === "Enter") {
        // https://api.mapbox.com/geocoding/v5/mapbox.places/Los%20Angeles.json?access_token=YOUR_MAPBOX_ACCESS_TOKEN
        $.getJSON(`https://api.mapbox.com/geocoding/v5/mapbox.places/${e.target.value}.json`, {
            access_token: 'pk.eyJ1Ijoic3dpZ2RlciIsImEiOiJja29hbnI2bmQwMm0zMm91aHhlNHlhOHF2In0.FaLm4CYTTue7x4-NWm8p5g',
            // query: e.target.value,
            limit: 1
        }, function (data) {
            let result = data.features[0]
            let longLat = result.center
            map.setView([longLat[1], longLat[0]], 13);
            e.target.value = result.place_name
        })
    }
}

let fullGeojsonData = []

function roundLatLongDown(latlong) {
    let interval = metadata.latlong_interval
    return Math.floor(latlong / interval) * interval;
}

function roundLatLongUp(latlong) {
    let interval = metadata.latlong_interval
    return Math.ceil(latlong / interval) * interval + interval;
}

function getNewData() {
    let bounds = map.getBounds()
    let south = roundLatLongDown(bounds.getSouth())
    let north = roundLatLongUp(bounds.getNorth())
    let west = roundLatLongDown(bounds.getWest())
    let east = roundLatLongUp(bounds.getEast())
    let tasks = []
    for (let lat = south; lat < north; lat += metadata.latlong_interval) {
        for (let long = west; long < east; long += metadata.latlong_interval) {
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
                fullGeojsonData = fullGeojsonData.concat(data[0])
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
        if (l instanceof L.Marker && map.getBounds().contains(l.getLatLng()) && showFeature(l.feature)) {
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

const filters = {
    "harm": new Set(["ped", "car", "bike", "other"])
}

function showFeature(feature) {
    return filters["harm"].has(feature.properties.harm)
}

$("button").on('click', (event) => {
    let button = $(event.currentTarget)
    button.toggleClass('is-dark is-light is-selected');
    let filter = button.attr("data-filter-type")
    let value = button.attr("data-filter-value")
    if (button.hasClass('is-selected')) {
        filters[filter].add(value);
    } else {
        filters[filter].delete(value);
    }
    geojsonLayer.clearLayers()
    geojsonLayer.addData(fullGeojsonData)
    clusterLayer.clearLayers()
    clusterLayer.addLayer(geojsonLayer)
    updateCount()
});
